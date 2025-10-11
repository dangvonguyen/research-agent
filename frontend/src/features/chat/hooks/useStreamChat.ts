import { useCallback, useReducer, useRef } from "react";
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
  chunkDelay?: number;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function useStreamChat(options: StreamChatOptions = {}) {
  const [state, dispatch] = useReducer(StreamChatReducer, initialState);
  const processingPromiseRef = useRef<Promise<void>>(Promise.resolve());

  const startStream = useCallback(
    async (chatRequest: ChatRequest) => {
      dispatch({ type: "START_STREAMING" });
      processingPromiseRef.current = Promise.resolve();

      const delay = options.chunkDelay ?? 0;

      try {
        await apiClient.chat.stream_respond(
          chatRequest,
          (chunk: StreamChatChunk) => {
            processingPromiseRef.current = processingPromiseRef.current.then(
              async () => {
                dispatch({
                  type: "ADD_CHUNK",
                  payload: {
                    content: chunk.data.chunk,
                    messageId: chunk.metadata.message_id,
                  },
                });
                options.onChunk?.(chunk);

                if (delay > 0) {
                  await sleep(delay);
                }
              },
            );
          },
          (streamError: Error) => {
            const chatError: ChatError = streamError;
            chatError.conversationId = chatRequest.conversation_id;
            dispatch({ type: "SET_ERROR", payload: chatError });
          },
          async () => {
            // Wait for all chunks to finish processing
            await processingPromiseRef.current;
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
    processingPromiseRef.current = Promise.resolve();
    dispatch({ type: "RESET" });
  }, []);

  return {
    ...state,
    startStream,
    resetStream,
  };
}
