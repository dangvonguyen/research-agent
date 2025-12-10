import { useCallback, useMemo, useReducer, useRef } from "react";
import { apiClient } from "@/api/client";
import type { ChatRequest } from "@/api/models";
import type {
  ChatStatus,
  MessageContentPart,
  StreamAbort,
  StreamChatChunk,
  StreamContentDelta,
  StreamContentEnd,
  StreamContentStart,
  StreamError,
  StreamEvent,
  StreamingMetadata,
} from "../types";

interface ChatState {
  // Streaming status
  status: ChatStatus;
  messageId: string | null;
  conversationId: string | null;

  // Content parts (index-based map)
  contentParts: Map<number, MessageContentPart>;

  // Streaming metadata (index-based map)
  streamingMeta: Map<number, StreamingMetadata>;

  // Error handling
  error: string | null;
}

type ChatAction =
  | { type: "SUBMIT" }
  | { type: "STREAM_START"; payload: { conversationId: string } }
  | { type: "CONTENT_START"; payload: StreamContentStart }
  | { type: "CONTENT_DELTA"; payload: StreamContentDelta }
  | { type: "CONTENT_END"; payload: StreamContentEnd }
  | { type: "MESSAGE_END" }
  | { type: "STREAM_ERROR"; payload: StreamError }
  | { type: "STREAM_ABORT"; payload: StreamAbort }
  | { type: "RESET" };

const initialState: ChatState = {
  status: "ready",
  messageId: null,
  conversationId: null,
  contentParts: new Map(),
  streamingMeta: new Map(),
  error: null,
};

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "SUBMIT": {
      return {
        ...state,
        status: "submitted",
        error: null,
      };
    }

    case "STREAM_START": {
      return {
        ...initialState,
        status: "streaming",
        conversationId: action.payload.conversationId,
      };
    }

    case "CONTENT_START": {
      const {
        index,
        content_type,
        tool_call_id,
        tool_name,
        message_id,
        agent_type,
      } = action.payload;

      // Create MessageContentPart using API types
      const newPart: MessageContentPart = (() => {
        switch (content_type) {
          case "text":
            return {
              type: "text",
              text: "",
            };
          case "reasoning":
            return {
              type: "reasoning",
              text: "",
            };
          case "tool-call":
            return {
              type: "tool-call",
              tool_call_id: tool_call_id || "",
              tool_name: tool_name || "",
              input: {},
            };
          case "tool-result":
            return {
              type: "tool-result",
              tool_call_id: tool_call_id || "",
              tool_name: tool_name || "",
              output: { type: "text", value: "" },
            };
        }
      })();

      // Create streaming metadata
      const newMeta: StreamingMetadata = {
        index,
        isComplete: false,
        agent_type,
        _buffer:
          content_type === "tool-call" || content_type === "tool-result"
            ? ""
            : undefined,
      };

      const newParts = new Map(state.contentParts);
      const newStreamingMeta = new Map(state.streamingMeta);
      newParts.set(index, newPart);
      newStreamingMeta.set(index, newMeta);

      return {
        ...state,
        messageId: message_id,
        contentParts: newParts,
        streamingMeta: newStreamingMeta,
      };
    }

    case "CONTENT_DELTA": {
      const { index, delta } = action.payload;
      const part = state.contentParts.get(index);
      const meta = state.streamingMeta.get(index);

      if (!part || !meta) {
        console.warn(`Received delta for non-existent part ${index}`);
        return state;
      }

      let updatedPart: MessageContentPart;
      const updatedMeta = { ...meta };

      if (part.type === "text" || part.type === "reasoning") {
        updatedPart = {
          ...part,
          text: part.text + (delta as string),
        };
      } else if (part.type === "tool-call" || part.type === "tool-result") {
        // Accumulate JSON string in metadata buffer (don't modify content part yet)
        updatedPart = part;
        updatedMeta._buffer =
          (meta._buffer || "") +
          (typeof delta === "string" ? delta : JSON.stringify(delta));
      } else {
        updatedPart = part;
      }

      const newParts = new Map(state.contentParts);
      const newStreamingMeta = new Map(state.streamingMeta);
      newParts.set(index, updatedPart);
      newStreamingMeta.set(index, updatedMeta);

      return {
        ...state,
        contentParts: newParts,
        streamingMeta: newStreamingMeta,
      };
    }

    case "CONTENT_END": {
      const { index } = action.payload;
      const part = state.contentParts.get(index);
      const meta = state.streamingMeta.get(index);

      if (!part || !meta) {
        console.warn(`Received end for non-existent part ${index}`);
        return state;
      }

      let updatedPart: MessageContentPart = part;
      const updatedMeta = { ...meta, isComplete: true };

      // Parse JSON for tool-call and tool-result
      if (part.type === "tool-call") {
        const buffer = meta._buffer || "";
        try {
          updatedPart = {
            ...part,
            input: buffer ? JSON.parse(buffer) : {},
          };
          delete updatedMeta._buffer;
        } catch (_) {
          updatedMeta.error = "Failed to parse tool input JSON";
        }
      } else if (part.type === "tool-result") {
        const buffer = meta._buffer || "";
        try {
          const parsed = buffer ? JSON.parse(buffer) : {};
          updatedPart = {
            ...part,
            output: {
              type: parsed.type || "text",
              value: parsed.value !== undefined ? parsed.value : parsed,
            },
          };
          delete updatedMeta._buffer;
        } catch (_) {
          updatedMeta.error = "Failed to parse tool result JSON";
        }
      }

      const newParts = new Map(state.contentParts);
      const newStreamingMeta = new Map(state.streamingMeta);
      newParts.set(index, updatedPart);
      newStreamingMeta.set(index, updatedMeta);

      return {
        ...state,
        contentParts: newParts,
        streamingMeta: newStreamingMeta,
      };
    }

    case "MESSAGE_END": {
      return {
        ...state,
        status: "ready",
      };
    }

    case "STREAM_ERROR": {
      return {
        ...state,
        status: "error",
        error: action.payload.error,
      };
    }

    case "STREAM_ABORT": {
      return {
        ...state,
        status: "error",
        error: `Stream aborted: ${action.payload.reason}`,
      };
    }

    case "RESET": {
      return initialState;
    }

    default:
      return state;
  }
}

export interface UseChatOptions {
  onEvent?: (event: StreamEvent) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

export interface UseChatReturn {
  // Status
  status: ChatStatus;
  messageId: string | null;
  conversationId: string | null;

  // Content parts
  contentParts: MessageContentPart[];

  // Errors
  error: string | null;

  // Actions
  submitChat: () => void;
  startChat: (request: ChatRequest) => Promise<void>;
  stopChat: () => void;
  reset: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const abortControllerRef = useRef<AbortController | null>(null);

  const startChat = useCallback(
    async (request: ChatRequest) => {
      // Reset state and start streaming
      dispatch({ type: "RESET" });
      dispatch({
        type: "STREAM_START",
        payload: { conversationId: request.conversation_id || "" },
      });

      // Create new AbortController for this stream
      abortControllerRef.current = new AbortController();

      await apiClient.chat.stream_respond(
        request,
        (chunk: StreamChatChunk) => {
          const event = chunk.data;

          // Call optional raw event callback
          options.onEvent?.(event);

          // Dispatch actions based on event type
          switch (event.type) {
            case "content_start":
              dispatch({ type: "CONTENT_START", payload: event });
              break;
            case "content_delta":
              dispatch({ type: "CONTENT_DELTA", payload: event });
              break;
            case "content_end":
              dispatch({ type: "CONTENT_END", payload: event });
              break;
            case "message_end":
              dispatch({ type: "MESSAGE_END" });
              break;
            case "error":
              dispatch({ type: "STREAM_ERROR", payload: event });
              break;
            case "abort":
              dispatch({ type: "STREAM_ABORT", payload: event });
              break;
          }
        },
        (error: Error) => {
          dispatch({
            type: "STREAM_ERROR",
            payload: {
              type: "error",
              error: error.message,
              conversation_id: request.conversation_id || "",
              message_id: state.messageId || "",
              timestamp: new Date().toISOString(),
            },
          });
          options.onError?.(error);
        },
        () => {
          options.onComplete?.();
          abortControllerRef.current = null;
        },
        abortControllerRef.current.signal,
      );
    },
    [options, state.messageId],
  );

  const submitChat = useCallback(() => {
    dispatch({ type: "SUBMIT" });
  }, []);

  const stopChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;

      dispatch({
        type: "STREAM_ABORT",
        payload: {
          type: "abort",
          reason: "User stopped the chat",
          conversation_id: state.conversationId || "",
          message_id: state.messageId || "",
          timestamp: new Date().toISOString(),
        },
      });
    }
  }, [state.conversationId, state.messageId]);

  const reset = useCallback(() => {
    dispatch({ type: "RESET" });
  }, []);

  // Convert Maps to Arrays for easier rendering
  const contentParts = useMemo(
    () =>
      Array.from(state.contentParts.entries())
        .filter(([index]) => {
          const meta = state.streamingMeta.get(index);
          return meta && meta.agent_type !== "sub-agent";
        })
        .sort(([a], [b]) => a - b)
        .map(([, part]) => part),
    [state],
  );

  return {
    // Status
    status: state.status,
    messageId: state.messageId,
    conversationId: state.conversationId,

    // Content parts
    contentParts,

    // Errors
    error: state.error,

    // Actions
    submitChat,
    startChat,
    stopChat,
    reset,
  };
}
