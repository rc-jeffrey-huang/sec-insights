import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Sequence, cast

import nest_asyncio
from app.chat.constants import (
    DB_DOC_ID_KEY,
    NODE_PARSER_CHUNK_OVERLAP,
    NODE_PARSER_CHUNK_SIZE,
    SYSTEM_MESSAGE,
)
from app.chat.pg_vector import get_vector_store_singleton
from app.chat.qa_response_synth import get_custom_response_synth
from app.core.config import settings
from app.models.db import MessageRoleEnum, MessageStatusEnum
from app.schema import Conversation as ConversationSchema
from app.schema import Document as DocumentSchema
from app.schema import Message as MessageSchema
from cachetools import TTLCache, cached
from llama_index import (
    ServiceContext,
    StorageContext,
    VectorStoreIndex,
    load_indices_from_storage,
)
from llama_index.agent import OpenAIAgent
from llama_index.callbacks.base import BaseCallbackHandler, CallbackManager
from llama_index.embeddings.openai import (
    OpenAIEmbedding,
    OpenAIEmbeddingMode,
    OpenAIEmbeddingModelType,
)
from llama_index.indices.query.base import BaseQueryEngine
from llama_index.indices.query.schema import QueryBundle
from llama_index.llms import ChatMessage, OpenAI
from llama_index.llms.base import MessageRole
from llama_index.node_parser.simple import SimpleNodeParser
from llama_index.query_engine import SubQuestionQueryEngine
from llama_index.question_gen.openai_generator import OpenAIQuestionGenerator
from llama_index.question_gen.types import SubQuestion, SubQuestionList
from llama_index.readers.file.docs_reader import PDFReader
from llama_index.schema import Document as LlamaIndexDocument
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.vector_stores.types import (
    ExactMatchFilter,
    MetadataFilters,
    VectorStore,
)

logger = logging.getLogger(__name__)


logger.info("Applying nested asyncio patch")
nest_asyncio.apply()


def fetch_and_read_document(
    document: DocumentSchema,
) -> List[LlamaIndexDocument]:
    # Super hacky approach to get this to feature complete on time.
    # TODO: Come up with better abstractions for this and the other methods in this module.
    UPLOAD_FOLDER = "uploads"

    file_path = Path(UPLOAD_FOLDER) / document
    if os.path.isfile(file_path):  # 确保是文件而不是子目录
        with open(file_path, "r") as file:
            file.seek(0)
            reader = PDFReader()
            return reader.load_data(file_path, extra_info={DB_DOC_ID_KEY: document})


def build_description_for_document(document: DocumentSchema) -> str:
    parts = document.split(".")
    return f"A document({parts[0]}) containing useful information that the user pre-selected to discuss with the assistant."


def index_to_query_engine(doc_id: str, index: VectorStoreIndex) -> BaseQueryEngine:
    filters = MetadataFilters(
        filters=[ExactMatchFilter(key=DB_DOC_ID_KEY, value=doc_id)]
    )
    kwargs = {"similarity_top_k": 3, "filters": filters}
    return index.as_query_engine(**kwargs)


@cached(
    TTLCache(maxsize=10, ttl=timedelta(minutes=5).total_seconds()),
    key=lambda *args, **kwargs: "global_storage_context",
)
def get_storage_context(persist_dir: str, vector_store: VectorStore) -> StorageContext:
    logger.info("Creating new storage context.")
    return StorageContext.from_defaults(
        persist_dir=persist_dir, vector_store=vector_store
    )


async def build_doc_id_to_index_map(
    service_context: ServiceContext,
    documents: List[DocumentSchema],
) -> Dict[str, VectorStoreIndex]:
    persist_dir = "persist"

    vector_store = await get_vector_store_singleton()
    try:
        try:
            storage_context = get_storage_context(persist_dir, vector_store)
        except FileNotFoundError:
            logger.info("Could not find storage context. Creating new storage context.")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            storage_context.persist(persist_dir=persist_dir)
        index_ids = [doc for doc in documents]
        indices = load_indices_from_storage(
            storage_context,
            index_ids=index_ids,
            service_context=service_context,
        )
        doc_id_to_index = dict(zip(index_ids, indices))
        logger.debug("Loaded indices from storage.")
    except ValueError:
        logger.error(
            "Failed to load indices from storage. Creating new indices.", exc_info=True
        )
        storage_context = StorageContext.from_defaults(
            persist_dir=persist_dir, vector_store=vector_store
        )
        doc_id_to_index = {}
        for doc in documents:
            llama_index_docs = fetch_and_read_document(doc)
            storage_context.docstore.add_documents(llama_index_docs)
            index = VectorStoreIndex.from_documents(
                llama_index_docs,
                storage_context=storage_context,
                service_context=service_context,
            )
            index.set_index_id(str(doc))
            index.storage_context.persist(persist_dir=persist_dir)
            doc_id_to_index[str(doc)] = index
    return doc_id_to_index


def get_chat_history(
    chat_messages: List[MessageSchema],
) -> List[ChatMessage]:
    """
    Given a list of chat messages, return a list of ChatMessage instances.

    Failed chat messages are filtered out and then the remaining ones are
    sorted by created_at.
    """
    # pre-process chat messages
    chat_messages = [
        m
        for m in chat_messages
        if m.content.strip() and m.status == MessageStatusEnum.SUCCESS
    ]
    # TODO: could be a source of high CPU utilization
    chat_messages = sorted(chat_messages, key=lambda m: m.created_at)

    chat_history = []
    for message in chat_messages:
        role = (
            MessageRole.ASSISTANT
            if message.role == MessageRoleEnum.assistant
            else MessageRole.USER
        )
        chat_history.append(ChatMessage(content=message.content, role=role))

    return chat_history


def get_tool_service_context(
    callback_handlers: List[BaseCallbackHandler],
) -> ServiceContext:
    llm = OpenAI(
        temperature=0,
        model="gpt-3.5-turbo-0613",
        streaming=False,
        api_key=settings.OPENAI_API_KEY,
        additional_kwargs={"api_key": settings.OPENAI_API_KEY},
    )
    callback_manager = CallbackManager(callback_handlers)
    embedding_model = OpenAIEmbedding(
        mode=OpenAIEmbeddingMode.SIMILARITY_MODE,
        model_type=OpenAIEmbeddingModelType.TEXT_EMBED_ADA_002,
        api_key=settings.OPENAI_API_KEY,
    )
    # Use a smaller chunk size to retrieve more granular results
    node_parser = SimpleNodeParser.from_defaults(
        chunk_size=NODE_PARSER_CHUNK_SIZE,
        chunk_overlap=NODE_PARSER_CHUNK_OVERLAP,
        callback_manager=callback_manager,
    )
    service_context = ServiceContext.from_defaults(
        callback_manager=callback_manager,
        llm=llm,
        embed_model=embedding_model,
        node_parser=node_parser,
    )
    return service_context


def build_tools_text(tools: Sequence[ToolMetadata]) -> str:
    tools_dict = {}
    for tool in tools:
        tools_dict[tool.name] = tool.description
    tools_str = json.dumps(tools_dict, indent=4, ensure_ascii=False)
    print("tools_str", tools_str)
    return tools_str


DEFAULT_OPENAI_SUB_QUESTION_PROMPT_TMPL = """\
You are a world class state of the art agent.

You have access to multiple tools, each representing a different data source or API.
Each of the tools has a name and a description, formatted as a JSON dictionary.
The keys of the dictionary are the names of the tools and the values are the \
descriptions.
Your purpose is to help answer a complex user question by generating a list of sub \
questions that can be answered by the tools.

These are the guidelines you consider when completing your task:
* Be as specific as possible
* The sub questions should be relevant to the user question 
* The sub questions should be answerable by the tools provided
* You can only generate up to three sub questions for each tool
* Tools must be specified by their name, not their description
* You don't need to use a tool if you don't think it's relevant

Output the list of sub questions by calling the SubQuestionList function.

## Tools
```json
{tools_str}
```

## User Question
{query_str}
"""


class COpenAIQuestionGenerator(OpenAIQuestionGenerator):
    def generate(
        self, tools: Sequence[ToolMetadata], query: QueryBundle
    ) -> List[SubQuestion]:
        tools_str = build_tools_text(tools)
        query_str = query.query_str
        question_list = self._program(query_str=query_str, tools_str=tools_str)
        question_list = cast(SubQuestionList, question_list)
        return question_list.items

    async def agenerate(
        self, tools: Sequence[ToolMetadata], query: QueryBundle
    ) -> List[SubQuestion]:
        tools_str = build_tools_text(tools)
        query_str = query.query_str
        question_list = await self._program.acall(
            query_str=query_str, tools_str=tools_str
        )
        question_list = cast(SubQuestionList, question_list)
        return question_list.items


async def get_chat_engine(
    callback_handler: BaseCallbackHandler,
    conversation: ConversationSchema,
) -> OpenAIAgent:
    service_context = get_tool_service_context([callback_handler])
    doc_id_to_index = await build_doc_id_to_index_map(
        service_context, conversation.documents
    )
    id_to_doc = {str(doc): (doc.split("."))[0] for doc in conversation.documents}
    vector_query_engine_tools = [
        QueryEngineTool(
            query_engine=index_to_query_engine(doc_id, index),
            metadata=ToolMetadata(
                name=id_to_doc[doc_id],
                description=build_description_for_document(id_to_doc[doc_id]),
            ),
        )
        for doc_id, index in doc_id_to_index.items()
    ]

    response_synth = get_custom_response_synth(service_context, conversation.documents)

    question_gen = COpenAIQuestionGenerator.from_defaults(
        llm=service_context.llm,
        prompt_template_str=DEFAULT_OPENAI_SUB_QUESTION_PROMPT_TMPL,
    )
    qualitative_question_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=vector_query_engine_tools,
        question_gen=question_gen,
        service_context=service_context,
        response_synthesizer=response_synth,
        verbose=settings.VERBOSE,
        use_async=True,
    )

    # api_query_engine_tools = [
    #     get_api_query_engine_tool(doc, service_context)
    #     for doc in conversation.documents
    #     if DocumentMetadataKeysEnum.SEC_DOCUMENT in doc.metadata_map
    # ]

    # quantitative_question_engine = SubQuestionQueryEngine.from_defaults(
    #     query_engine_tools=api_query_engine_tools,
    #     service_context=service_context,
    #     response_synthesizer=response_synth,
    #     verbose=settings.VERBOSE,
    #     use_async=True,
    # )

    top_level_sub_tools = [
        QueryEngineTool(
            query_engine=qualitative_question_engine,
            metadata=ToolMetadata(
                name="qualitative_question_engine",
                description="""
A query engine that can answer qualitative questions about a set of documents that the user pre-selected for the conversation.
Any questions about company-related headwinds, tailwinds, risks, sentiments, or administrative information should be asked here.
""".strip(),
            ),
        ),
        #         QueryEngineTool(
        #             query_engine=quantitative_question_engine,
        #             metadata=ToolMetadata(
        #                 name="quantitative_question_engine",
        #                 description="""
        # A query engine that can answer quantitative questions about a set of SEC financial documents that the user pre-selected for the conversation.
        # Any questions about company-related financials or other metrics should be asked here.
        # """.strip(),
        #             ),
        #         ),
    ]

    chat_llm = OpenAI(
        temperature=0,
        model="gpt-3.5-turbo-0613",
        streaming=True,
        api_key=settings.OPENAI_API_KEY,
        additional_kwargs={"api_key": settings.OPENAI_API_KEY},
    )
    chat_messages: List[MessageSchema] = conversation.messages
    chat_history = get_chat_history(chat_messages)
    logger.debug("Chat history: %s", chat_history)

    if conversation.documents:
        doc_titles = "\n".join(
            "- " + (doc.split("."))[0] for doc in conversation.documents
        )
    else:
        doc_titles = "No documents selected."

    curr_date = datetime.utcnow().strftime("%Y-%m-%d")
    chat_engine = OpenAIAgent.from_tools(
        tools=top_level_sub_tools,
        llm=chat_llm,
        chat_history=chat_history,
        verbose=settings.VERBOSE,
        system_prompt=SYSTEM_MESSAGE.format(doc_titles=doc_titles, curr_date=curr_date),
        callback_manager=service_context.callback_manager,
        max_function_calls=3,
    )

    return chat_engine
