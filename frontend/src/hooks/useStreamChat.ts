import { useCallback, useState } from "react"

import { apiClient } from "@/api/client"

import type { ChatRequest } from "@/api/models"

interface StreamChatChunk {
  data: {
    chunk: string
    is_final: boolean
  }
  metadata: {
    conversation_id: string
    message_id: string
    timestamp: string
  }
}

interface UseStreamChatOptions {
  onError?: (error: Error) => void
  onComplete?: () => void
}

export function useStreamChat(options: UseStreamChatOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamedContent, setStreamedContent] = useState("")
  const [error, setError] = useState<Error | null>(null)
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null
  )

  const startStream = useCallback(
    async (chatRequest: ChatRequest) => {
      setIsStreaming(true)
      setStreamedContent("")
      setError(null)

      try {
        await apiClient.chat.stream_respond(
          chatRequest,
          (chunk: StreamChatChunk) => {
            setStreamingMessageId(chunk.metadata.message_id)
            setStreamedContent(prev => prev + chunk.data.chunk)
          },
          (streamError: Error) => {
            setError(streamError)
            setIsStreaming(false)
            options.onError?.(streamError)
          },
          () => {
            setIsStreaming(false)
            options.onComplete?.()
          }
        )
      } catch (err) {
        const error = err instanceof Error ? err : new Error("Unknown error")
        setError(error)
        setIsStreaming(false)
        options.onError?.(error)
      }
    },
    [options]
  )

  const resetStream = useCallback(() => {
    setStreamedContent("")
    setStreamingMessageId(null)
    setError(null)
    setIsStreaming(false)
  }, [])

  return {
    isStreaming,
    streamingMessageId,
    streamedContent,
    error,
    startStream,
    resetStream,
  }
}
