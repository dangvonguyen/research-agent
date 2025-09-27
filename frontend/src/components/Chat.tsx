import { useEffect, useRef, useState } from "react"

import { apiClient } from "@/api"
import { useStreamChat } from "@/hooks/useStreamChat"
import { cn } from "@/lib/utils"

import ChatComposer from "./ChatComposer"

import type { Conversation, Message } from "@/types"

interface ChatProps {
  activeConversation: string | null
  setActiveConversation: React.Dispatch<React.SetStateAction<string | null>>
  conversations: Conversation[]
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>
}

function Chat({
  activeConversation,
  setActiveConversation,
  setConversations,
}: ChatProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const {
    isStreaming,
    streamingMessageId,
    streamedContent,
    startStream,
    resetStream,
  } = useStreamChat()

  useEffect(() => {
    const fetchMessages = async () => {
      if (activeConversation) {
        try {
          const currentMessages = await apiClient.conversations
            .getMessages(activeConversation)
            .then(res => res.data)
          setMessages(currentMessages)
        } catch (error) {
          console.error("Failed to fetch messages:", error)
        }
      } else {
        setMessages([])
      }
    }

    fetchMessages()
  }, [activeConversation, messages.length])

  useEffect(() => {
    if (streamingMessageId) {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === streamingMessageId
            ? { ...msg, content: streamedContent }
            : msg
        )
      )
    }
  }, [streamingMessageId, streamedContent])

  // Scroll on conversation change (instant jump)
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "auto" })
  }, [activeConversation])

  // Scroll only when the last message is from the user
  useEffect(() => {
    if (!messagesEndRef.current || messages.length === 0) return

    const lastMessage = messages[messages.length - 1]

    if (lastMessage.role === "user") {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return

    let conversationId = activeConversation

    // Create user message and also create new conversation if none is active
    const userMessage = await apiClient.conversations
      .createMessage(conversationId, { content, role: "user" })
      .then(res => res.data)

    setMessages(prev => [...prev, userMessage])

    if (conversationId == null) {
      conversationId = userMessage.conversation_id

      const newConversation = await apiClient.conversations
        .getById(userMessage.conversation_id)
        .then(res => res.data)

      setConversations(prev => [newConversation, ...prev])
      setActiveConversation(conversationId)
    }

    setIsLoading(true)
    try {
      await startStream({
        conversation_id: conversationId,
        message_id: userMessage.id,
      })

      resetStream()
    } catch (error) {
      console.error("Error sending message:", error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full h-screen overflow-y-auto scrollbar-thin">
      <div
        className={cn(
          "grid w-full h-screen mx-auto px-8 max-w-[52rem]",
          messages.length === 0
            ? "grid-rows-[40vh_auto]"
            : "grid-rows-[1fr_auto]"
        )}
      >
        {/* Messages Container */}
        {messages.length === 0 ? (
          <div className="flex justify-center items-end pb-10">
            <h1 className="text-3xl">What's on your mind today?</h1>
          </div>
        ) : (
          // TODO: implement files preview in user message
          <div className="flex flex-col gap-10 pt-[7vh] pb-[10vh]">
            {messages.map(message => (
              <div
                key={message.id}
                className={
                  message.role === "user"
                    ? "self-end bg-secondary text-secondary-foreground rounded-3xl px-4 py-2 max-w-[70%] shadow"
                    : "self-stretch bg-background text-foreground"
                }
              >
                {message.content}
              </div>
            ))}

            {/* Loading indicator */}
            {isLoading && (
              <div className="flex gap-1.5">
                <div className="w-1.5 h-1.5 bg-current rounded-3xl animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-1.5 h-1.5 bg-current rounded-3xl animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-current rounded-3xl animate-bounce"></div>
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Chat Composer */}
        <div className="sticky bottom-0">
          {/* Backdrop */}
          <div className="absolute top-10 bottom-0 inset-x-0 bg-background z-0" />

          {/* Foreground content */}
          <div className="relative z-10">
            <ChatComposer
              onSend={handleSendMessage}
              placeholder="Ask anything"
              disabled={isLoading || isStreaming}
            />
            {messages.length > 0 && (
              <div className="flex justify-center">
                <span className="text-xs p-1.5">
                  Verify AI-generated content. Don't share sensitive info.
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chat
