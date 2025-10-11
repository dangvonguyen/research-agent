import type { Attachment, Conversation, Message } from "@/types";

export type { Attachment, Conversation, Message };

export interface ChatLoaderData {
  id: string;
  initialMessages: Message[];
}

export interface StreamChatChunk {
  data: {
    chunk: string;
    is_final: boolean;
  };
  metadata: {
    conversation_id: string;
    message_id: string;
    timestamp: string;
  };
}

export interface ChatError extends Error {
  code?: string;
  conversationId?: string;
  messageId?: string;
}
