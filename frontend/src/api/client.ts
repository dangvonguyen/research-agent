import createClient from "openapi-fetch";
import type { StreamChatChunk } from "@/features/chat/types";
import { getApiConfig } from "./config";
import type {
  ChatRequest,
  ChatResponse,
  CollectionCreate,
  CollectionResponse,
  CollectionUpdate,
  ConversationCreate,
  ConversationUpdate,
  CrawlerConfigCreate,
  CrawlerConfigResponse,
  CrawlerConfigUpdate,
  CrawlerJobCreate,
  CrawlerJobResponse,
  CrawlerJobUpdate,
  CreateResponse,
  DeleteResponse,
  JobStatus,
  MessageCreate,
  PaperCreate,
  PaperResponse,
  PaperUpdate,
  Response_ConversationDB_,
  Response_list_Attachment__,
  Response_list_ConversationDB__,
  Response_list_MessageDB__,
  Response_MessageDB_,
  Response_NoneType_,
  UpdateResponse,
} from "./models";
import type { paths } from "./openapi.gen";

const config = getApiConfig();
const client = createClient<paths>({
  baseUrl: config.baseUrl,
  headers: config.defaultHeaders,
});

async function apiCall<
  Path extends keyof paths,
  Method extends Exclude<keyof paths[Path] & string, "parameters">,
>(
  path: Path,
  method: Uppercase<Method>,
  errorMessage: string,
  options?: {
    params?: Record<string, unknown>;
    body?: Record<string, unknown>;
  },
) {
  // biome-ignore lint: false
  const { data, error } = await (client as any)[method](path, options);
  if (error) throw new Error(`${errorMessage}: ${JSON.stringify(error)}`);
  return data;
}

export const apiClient = {
  // Chats
  chat: {
    respond: (body: ChatRequest): Promise<ChatResponse> =>
      apiCall("/api/v1/chat", "POST", "Chat request failed", { body }),

    stream_respond: async (
      body: ChatRequest,
      onChunk: (chunk: StreamChatChunk) => void,
      onError?: (error: Error) => void,
      onComplete?: () => void,
      signal?: AbortSignal,
    ): Promise<void> => {
      try {
        const response = await fetch(`${config.baseUrl}/api/v1/chat/stream`, {
          method: "POST",
          headers: {
            ...config.defaultHeaders,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
          signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("Response body is not readable");
        }

        const decoder = new TextDecoder();
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            // Decode the chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages
            const lines = buffer.split("\n");
            buffer = lines.pop() || ""; // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const jsonData = line.slice(6); // Remove "data: " prefix
                if (jsonData.trim()) {
                  try {
                    const parsed = JSON.parse(jsonData) as StreamChatChunk;
                    onChunk(parsed);

                    // Check for completion on message_end event
                    if (parsed.data.type === "message_end") {
                      onComplete?.();
                      return;
                    }

                    // Handle errors
                    if (
                      parsed.data.type === "error" ||
                      parsed.data.type === "abort"
                    ) {
                      const errorMessage =
                        parsed.data.type === "error"
                          ? parsed.data.error
                          : `Stream aborted: ${parsed.data.reason}`;
                      onError?.(new Error(errorMessage));
                      return;
                    }
                  } catch (parseError) {
                    console.warn(
                      "Failed to parse SSE data:",
                      jsonData,
                      parseError,
                    );
                  }
                }
              }
            }
          }
        } finally {
          reader.releaseLock();
        }

        onComplete?.();
      } catch (error) {
        // Don't treat abort errors as failures
        if (error instanceof Error && error.name === "AbortError") {
          return;
        }
        console.error("Stream error:", error);
        onError?.(error instanceof Error ? error : new Error(String(error)));
      }
    },
  },

  conversations: {
    list: (
      skip?: number,
      limit?: number,
    ): Promise<Response_list_ConversationDB__> =>
      apiCall("/api/v1/conversations", "GET", "Failed to fetch conversations", {
        params: { query: { skip, limit } },
      }),

    create: (body: ConversationCreate): Promise<Response_ConversationDB_> =>
      apiCall(
        "/api/v1/conversations",
        "POST",
        "Failed to create conversation",
        { body },
      ),

    getById: (conversationId: string): Promise<Response_ConversationDB_> =>
      apiCall(
        "/api/v1/conversations/{conversation_id}",
        "GET",
        "Failed to fetch conversation",
        { params: { path: { conversation_id: conversationId } } },
      ),

    update: (
      conversationId: string,
      body: ConversationUpdate,
    ): Promise<Response_ConversationDB_> =>
      apiCall(
        "/api/v1/conversations/{conversation_id}",
        "PATCH",
        "Failed to update conversation",
        { params: { path: { conversation_id: conversationId } }, body },
      ),

    delete: (conversationId: string): Promise<Response_NoneType_> =>
      apiCall(
        "/api/v1/conversations/{conversation_id}",
        "DELETE",
        "Failed to delete conversation",
        { params: { path: { conversation_id: conversationId } } },
      ),

    getMessages: (
      conversationId: string,
      skip?: number,
      limit?: number,
    ): Promise<Response_list_MessageDB__> =>
      apiCall(
        "/api/v1/conversations/{conversation_id}/messages",
        "GET",
        "Failed to fetch messages",
        {
          params: {
            path: { conversation_id: conversationId },
            query: { skip, limit },
          },
        },
      ),

    getMessageById: (messageId: string): Promise<Response_MessageDB_> =>
      apiCall(
        "/api/v1/conversations/messages/{message_id}",
        "GET",
        "Failed to fetch message",
        { params: { path: { message_id: messageId } } },
      ),

    getLastMessage: (conversationId: string): Promise<Response_MessageDB_> =>
      apiCall(
        "/api/v1/conversations/messages/last",
        "GET",
        "Failed to fetch last message",
        { params: { query: { conversation_id: conversationId } } },
      ),

    createMessage: (
      conversationId: string | null,
      body: MessageCreate,
    ): Promise<Response_MessageDB_> =>
      apiCall(
        "/api/v1/conversations/messages",
        "POST",
        "Failed to create message",
        { params: { query: { conversation_id: conversationId } }, body },
      ),
  },

  // File uploads
  uploads: {
    uploadFiles: async (files: File[]): Promise<Response_list_Attachment__> => {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }

      const response = await fetch(`${config.baseUrl}/api/v1/uploads`, {
        method: "POST",
        // Don't set Content-Type header for FormData - browser will set it with boundary
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        throw new Error(`Failed to upload files: ${JSON.stringify(error)}`);
      }

      return response.json();
    },
  },

  // Crawler Configs
  crawlerConfigs: {
    list: (skip?: number, limit?: number): Promise<CrawlerConfigResponse[]> =>
      apiCall(
        "/api/v1/crawlers/configs",
        "GET",
        "Failed to fetch crawler configs",
        { params: { query: { skip, limit } } },
      ),

    create: (body: CrawlerConfigCreate): Promise<CreateResponse> =>
      apiCall(
        "/api/v1/crawlers/configs",
        "POST",
        "Failed to create crawler config",
        { body },
      ),

    getById: (configId: string): Promise<CrawlerConfigResponse> =>
      apiCall(
        "/api/v1/crawlers/configs/{config_id}",
        "GET",
        "Failed to fetch crawler config",
        { params: { path: { config_id: configId } } },
      ),

    getByName: (name: string): Promise<CrawlerConfigResponse> =>
      apiCall(
        "/api/v1/crawlers/configs/name/{name}",
        "GET",
        "Failed to fetch crawler config by name",
        { params: { path: { name } } },
      ),

    update: (
      configId: string,
      body: CrawlerConfigUpdate,
    ): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/crawlers/configs/{config_id}",
        "PATCH",
        "Failed to update crawler config",
        { params: { path: { config_id: configId } }, body },
      ),

    delete: (configId: string): Promise<DeleteResponse> =>
      apiCall(
        "/api/v1/crawlers/configs/{config_id}",
        "DELETE",
        "Failed to delete crawler config",
        { params: { path: { config_id: configId } } },
      ),
  },

  // Crawler Jobs
  crawlerJobs: {
    list: (
      skip?: number,
      limit?: number,
      status?: JobStatus,
    ): Promise<CrawlerJobResponse[]> =>
      apiCall("/api/v1/crawlers/jobs", "GET", "Failed to fetch crawler jobs", {
        params: { query: { skip, limit, status } },
      }),

    create: (body: CrawlerJobCreate): Promise<CreateResponse> =>
      apiCall("/api/v1/crawlers/jobs", "POST", "Failed to create crawler job", {
        body,
      }),

    getById: (jobId: string): Promise<CrawlerJobResponse> =>
      apiCall(
        "/api/v1/crawlers/jobs/{job_id}",
        "GET",
        "Failed to fetch crawler job",
        { params: { path: { job_id: jobId } } },
      ),

    update: (jobId: string, body: CrawlerJobUpdate): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/crawlers/jobs/{job_id}",
        "PATCH",
        "Failed to update crawler job",
        { params: { path: { job_id: jobId } }, body },
      ),

    delete: (jobId: string): Promise<DeleteResponse> =>
      apiCall(
        "/api/v1/crawlers/jobs/{job_id}",
        "DELETE",
        "Failed to delete crawler job",
        { params: { path: { job_id: jobId } } },
      ),

    upload: async (files: File[]): Promise<CreateResponse> => {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }

      const response = await fetch(`${config.baseUrl}/api/v1/crawlers/upload`, {
        method: "POST",
        // Don't set Content-Type header for FormData - browser will set it with boundary
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        throw new Error(`Failed to upload papers: ${JSON.stringify(error)}`);
      }

      return response.json();
    },
  },

  // Papers
  papers: {
    list: (
      skip?: number,
      limit?: number,
      status?: JobStatus,
    ): Promise<PaperResponse[]> =>
      apiCall("/api/v1/papers", "GET", "Failed to fetch papers", {
        params: { query: { skip, limit, status } },
      }),

    create: (body: PaperCreate): Promise<CreateResponse> =>
      apiCall("/api/v1/papers", "POST", "Failed to create paper", { body }),

    getById: (paperId: string): Promise<PaperResponse> =>
      apiCall("/api/v1/papers/{paper_id}", "GET", "Failed to fetch paper", {
        params: { path: { paper_id: paperId } },
      }),

    upload: async (
      file: File,
      metadata?: {
        title?: string;
        authors?: string;
        abstract?: string;
        doi?: string;
        year?: number;
        keywords?: string;
      },
    ): Promise<CreateResponse> => {
      const formData = new FormData();
      formData.append("file", file);

      if (metadata) {
        if (metadata.title) formData.append("title", metadata.title);
        if (metadata.authors) formData.append("authors", metadata.authors);
        if (metadata.abstract) formData.append("abstract", metadata.abstract);
        if (metadata.doi) formData.append("doi", metadata.doi);
        if (metadata.year) formData.append("year", metadata.year.toString());
        if (metadata.keywords) formData.append("keywords", metadata.keywords);
      }

      const response = await fetch(`${config.baseUrl}/api/v1/papers/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({
          detail: response.statusText,
        }));
        throw new Error(`Failed to upload paper: ${JSON.stringify(error)}`);
      }

      return response.json();
    },

    update: (paperId: string, body: PaperUpdate): Promise<UpdateResponse> =>
      apiCall("/api/v1/papers/{paper_id}", "PATCH", "Failed to update paper", {
        params: { path: { paper_id: paperId } },
        body,
      }),

    delete: (paperId: string): Promise<DeleteResponse> =>
      apiCall("/api/v1/papers/{paper_id}", "DELETE", "Failed to delete paper", {
        params: { path: { paper_id: paperId } },
      }),

    getPapersPerMonth: (
      year?: number,
    ): Promise<Array<{ month: number; papers: number }>> =>
      apiCall(
        "/api/v1/papers/analytics/papers-per-month",
        "GET",
        "Failed to fetch papers per month analytics",
        {
          params: { query: year ? { year } : {} },
        },
      ),

    getByJobId: (jobId: string): Promise<PaperResponse[]> =>
      apiCall(
        "/api/v1/papers/by-job/{job_id}",
        "GET",
        "Failed to fetch papers by job ID",
        {
          params: { path: { job_id: jobId } },
        },
      ),
  },

  // Collections
  collections: {
    list: (skip?: number, limit?: number): Promise<CollectionResponse[]> =>
      apiCall("/api/v1/collections", "GET", "Failed to fetch collections", {
        params: { query: { skip, limit } },
      }),

    create: (body: CollectionCreate): Promise<CreateResponse> =>
      apiCall("/api/v1/collections", "POST", "Failed to create collection", {
        body,
      }),

    getById: (collectionId: string): Promise<CollectionResponse> =>
      apiCall(
        "/api/v1/collections/{collection_id}",
        "GET",
        "Failed to fetch collection",
        {
          params: { path: { collection_id: collectionId } },
        },
      ),

    update: (
      collectionId: string,
      body: CollectionUpdate,
    ): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/collections/{collection_id}",
        "PATCH",
        "Failed to update collection",
        {
          params: { path: { collection_id: collectionId } },
          body,
        },
      ),

    delete: (collectionId: string): Promise<DeleteResponse> =>
      apiCall(
        "/api/v1/collections/{collection_id}",
        "DELETE",
        "Failed to delete collection",
        {
          params: { path: { collection_id: collectionId } },
        },
      ),

    getPapers: (collectionId: string): Promise<PaperResponse[]> =>
      apiCall(
        "/api/v1/collections/{collection_id}/papers",
        "GET",
        "Failed to fetch collection papers",
        {
          params: {
            path: { collection_id: collectionId },
          },
        },
      ),

    addPaper: (
      collectionId: string,
      paperId: string,
    ): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/collections/{collection_id}/papers/{paper_id}",
        "POST",
        "Failed to add paper to collection",
        {
          params: {
            path: { collection_id: collectionId, paper_id: paperId },
          },
        },
      ),

    removePaper: (
      collectionId: string,
      paperId: string,
    ): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/collections/{collection_id}/papers/{paper_id}",
        "DELETE",
        "Failed to remove paper from collection",
        {
          params: {
            path: { collection_id: collectionId, paper_id: paperId },
          },
        },
      ),

    getPapersByCollection: (): Promise<
      Array<{ name: string; value: number }>
    > =>
      apiCall(
        "/api/v1/collections/analytics/papers-by-collection",
        "GET",
        "Failed to fetch papers by collection analytics",
      ),
  },

  health: {
    check: (): Promise<{ [key: string]: string }> =>
      apiCall("/health", "GET", "Health check failed"),
  },

  root: {
    get: (): Promise<{ [key: string]: string }> =>
      apiCall("/", "GET", "Root endpoint failed"),
  },
};

export default apiClient;
