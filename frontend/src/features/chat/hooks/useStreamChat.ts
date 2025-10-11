import { useCallback, useReducer } from "react";
import { apiClient, type ChatRequest } from "@/api";
import type { ChatError, StreamChatChunk } from "../types";

type StreamChatState = {
  isStreaming: boolean;
  streamedContent: string;
  streamingMessageId: string | null;
  error: Error | null;
};

const initialState: StreamChatState = {
  isStreaming: false,
  streamedContent: "",
  streamingMessageId: null,
  error: null,
};

type StreamChatAction =
  | { type: "START_STREAMING" }
  | { type: "ADD_CHUNK"; payload: { messageId: string; content: string } }
  | { type: "SET_ERROR"; payload: Error }
  | { type: "COMPLETE_STREAMING" }
  | { type: "RESET" };

function StreamChatReducer(
  state: StreamChatState,
  action: StreamChatAction,
): StreamChatState {
  switch (action.type) {
    case "START_STREAMING":
      return {
        ...state,
        isStreaming: true,
      };
    case "ADD_CHUNK":
      return {
        ...state,
        streamingMessageId: action.payload.messageId,
        streamedContent: state.streamedContent + action.payload.content,
      };
    case "SET_ERROR":
      return {
        ...state,
        error: action.payload,
        isStreaming: false,
      };
    case "COMPLETE_STREAMING":
      return {
        ...state,
        isStreaming: false,
      };
    case "RESET":
      return initialState;
    default:
      return state;
  }
}

interface StreamChatOptions {
  onChunk?: (chunk: StreamChatChunk) => void;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

export function useStreamChat(options: StreamChatOptions = {}) {
  const [state, dispatch] = useReducer(StreamChatReducer, initialState);

  const startStream = useCallback(
    async (chatRequest: ChatRequest) => {
      dispatch({ type: "START_STREAMING" });

      try {
        await apiClient.chat.stream_respond(
          chatRequest,
          (chunk: StreamChatChunk) => {
            dispatch({
              type: "ADD_CHUNK",
              payload: {
                content: chunk.data.chunk,
                messageId: chunk.metadata.message_id,
              },
            });
            options.onChunk?.(chunk);
          },
          (streamError: Error) => {
            const chatError: ChatError = streamError;
            chatError.conversationId = chatRequest.conversation_id;
            dispatch({ type: "SET_ERROR", payload: chatError });
          },
          () => {
            dispatch({ type: "COMPLETE_STREAMING" });
            options.onComplete?.();
          },
        );
      } catch (error) {
        const chatError: ChatError =
          error instanceof Error ? error : new Error("Unknown streaming error");
        dispatch({ type: "SET_ERROR", payload: chatError });
        options.onError?.(chatError);
      }
    },
    [options],
  );

  const resetStream = useCallback(() => {
    dispatch({ type: "RESET" });
  }, []);

  return {
    ...state,
    startStream,
    resetStream,
  };
}
