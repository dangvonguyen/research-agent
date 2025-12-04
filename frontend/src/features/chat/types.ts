import type {
  MessageReasoningPart,
  MessageTextPart,
  MessageToolCallPart,
  MessageToolResultPart,
} from "@/api/models";
import type { Attachment, Conversation, Message } from "@/types";

export type { Attachment, Conversation, Message };

// Re-export API content part types
export type {
  MessageReasoningPart,
  MessageTextPart,
  MessageToolCallPart,
  MessageToolResultPart,
};

export type MessageContentPart =
  | MessageTextPart
  | MessageReasoningPart
  | MessageToolCallPart
  | MessageToolResultPart;

export type ChatStatus = "submitted" | "streaming" | "ready" | "error";

export interface ChatLoaderData {
  id: string;
  initialMessages: Message[];
}

// Streaming Event Types
export type StreamEventType =
  | "content_start"
  | "content_delta"
  | "content_end"
  | "message_end"
  | "error"
  | "abort";

export type StreamContentType =
  | "text"
  | "reasoning"
  | "tool-call"
  | "tool-result";

// Base event
export interface StreamEventBase {
  conversation_id: string;
  message_id: string;
  timestamp: string;
}

export interface StreamContentStart extends StreamEventBase {
  type: "content_start";
  content_type: StreamContentType;
  index: number;
  tool_call_id?: string | null;
  tool_name?: string | null;
}

export interface StreamContentDelta extends StreamEventBase {
  type: "content_delta";
  index: number;
  delta: string | Record<string, unknown>;
}

export interface StreamContentEnd extends StreamEventBase {
  type: "content_end";
  index: number;
}

export interface StreamMessageEnd extends StreamEventBase {
  type: "message_end";
}

export interface StreamError extends StreamEventBase {
  type: "error";
  error: string;
}

export interface StreamAbort extends StreamEventBase {
  type: "abort";
  reason: string;
}

export type StreamEvent =
  | StreamContentStart
  | StreamContentDelta
  | StreamContentEnd
  | StreamMessageEnd
  | StreamError
  | StreamAbort;

export interface StreamChatChunk {
  data: StreamEvent;
  metadata: Record<string, never>;
}

// Streaming metadata
export interface StreamingMetadata {
  index: number;
  isComplete: boolean;
  error?: string | null;
  _buffer?: string; // For accumulating JSON strings
}

export interface ChatError extends Error {
  code?: string;
  conversationId?: string;
  messageId?: string;
}
