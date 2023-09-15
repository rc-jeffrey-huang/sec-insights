/* eslint-disable @typescript-eslint/ban-ts-comment */
import { backendUrl } from "~/config";
import type { BackendDocument } from "~/types/backend/document";
import type { Message } from "~/types/conversation";
import { type SecDocument } from "~/types/document";
import { fromBackendDocumentToFrontend } from "./utils/documents";

interface CreateConversationPayload {
  id: string;
}

interface GetConversationPayload {
  id: string;
  messages: Message[];
  documents: BackendDocument[];
}

interface GetConversationReturnType {
  messages: Message[];
  documents: SecDocument[];
}

export interface File {
  name: string
  size: number
  extension: string
  mime_type: string
}

class BackendClient {
  private async get(endpoint: string) {
    const url = backendUrl + endpoint;
    const res = await fetch(url);

    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res;
  }

  private async post(endpoint: string, body?: any) {
    const url = backendUrl + endpoint;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    return res;
  }

  public async createConversation(documentIds: string[]): Promise<string> {
    const endpoint = "api/conversation/";
    const payload = { document_ids: documentIds };
    const res = await this.post(endpoint, payload);
    const data = (await res.json()) as CreateConversationPayload;

    return data.id;
  }

  public async fetchConversation(
    id: string
  ): Promise<GetConversationReturnType> {
    const endpoint = `api/conversation/${id}`;
    const res = await this.get(endpoint);
    const data = (await res.json()) as GetConversationPayload;

    return {
      messages: data.messages,
      documents: fromBackendDocumentToFrontend(data.documents),
    };
  }

  public async fetchDocuments(): Promise<SecDocument[]> {
    const endpoint = `api/document/`;
    const res = await this.get(endpoint);
    const data = (await res.json()) as BackendDocument[];
    const docs = fromBackendDocumentToFrontend(data);
    return docs;
  }

  public upload(options: {
    data: FormData
    onprogress: (event: ProgressEvent) => void,
    headers?: {[key: string]: string},
  }): Promise<File> {
    const defaultOptions = {
      xhr: new XMLHttpRequest(),
      method: 'POST',
      url: `${backendUrl}api/upload`,
      data: {},
    }
    const inner_options = {
      ...defaultOptions,
      ...options,
    }
    return new Promise((resolve, reject) => {
      const xhr = inner_options.xhr;
      xhr.open(inner_options.method, inner_options.url);
      for (const key in inner_options.headers) {
        // @ts-ignore
        xhr.setRequestHeader(key, inner_options.headers[key]);
      }
  
      xhr.withCredentials = true;
      xhr.responseType = 'json';
      xhr.onreadystatechange = () => {
        if (xhr.readyState === 4) {
          if (xhr.status >= 200 || xhr.status < 300) {
            // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
            resolve(xhr.response);
          } else {
            reject(xhr);
          }
        }
      };
      xhr.upload.onprogress = options.onprogress;
      xhr.send(options.data);
    });
  }
}

export const backendClient = new BackendClient();
