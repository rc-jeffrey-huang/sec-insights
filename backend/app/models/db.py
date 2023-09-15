from enum import Enum

from app.models.base import Base
from llama_index.callbacks.schema import CBEventType
from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship


class MessageRoleEnum(str, Enum):
    user = "user"
    assistant = "assistant"


class MessageStatusEnum(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class MessageSubProcessStatusEnum(str, Enum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"


# python doesn't allow enums to be extended, so we have to do this
additional_message_subprocess_fields = {
    "CONSTRUCTED_QUERY_ENGINE": "constructed_query_engine",
    "SUB_QUESTIONS": "sub_questions",
}
MessageSubProcessSourceEnum = Enum(
    "MessageSubProcessSourceEnum",
    [(event_type.name, event_type.value) for event_type in CBEventType]
    + list(additional_message_subprocess_fields.items()),
)


def to_pg_enum(enum_class) -> ENUM:
    return ENUM(enum_class, name=enum_class.__name__)


class Conversation(Base):
    """
    A conversation with messages and linked documents
    """

    messages = relationship("Message", back_populates="conversation")
    conversation_documents = relationship(
        "ConversationDocument", back_populates="conversation"
    )


class ConversationDocument(Base):
    """
    A many-to-many relationship between a conversation and a document
    """

    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversation.id"), index=True
    )
    document_id = Column(String)
    conversation = relationship("Conversation", back_populates="conversation_documents")


class Message(Base):
    """
    A message in a conversation
    """

    conversation_id = Column(
        UUID(as_uuid=True), ForeignKey("conversation.id"), index=True
    )
    content = Column(String)
    role = Column(to_pg_enum(MessageRoleEnum))
    status = Column(to_pg_enum(MessageStatusEnum), default=MessageStatusEnum.PENDING)
    conversation = relationship("Conversation", back_populates="messages")
    sub_processes = relationship("MessageSubProcess", back_populates="message")


class MessageSubProcess(Base):
    """
    A record of a sub-process that occurred as part of the generation of a message from an AI assistant
    """

    message_id = Column(UUID(as_uuid=True), ForeignKey("message.id"), index=True)
    source = Column(to_pg_enum(MessageSubProcessSourceEnum))
    message = relationship("Message", back_populates="sub_processes")
    status = Column(
        to_pg_enum(MessageSubProcessStatusEnum),
        default=MessageSubProcessStatusEnum.FINISHED,
        nullable=False,
    )
    metadata_map = Column(JSONB, nullable=True)
