import { useEffect, useMemo, useRef, useState } from "react"

import { cn } from "@/lib/utils"

import ChatComposer from "./ChatComposer"

import type { Conversation, Message } from "@/types"

interface ChatProps {
  activeConversation: string | null
  setActiveConversation: React.Dispatch<React.SetStateAction<string | null>>
  conversations: Conversation[]
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>
  onUpdateConversation: (conversationId: string, messages: Message[]) => void
  onCreateNewConversation: () => Conversation
}

function Chat({
  activeConversation,
  setActiveConversation,
  conversations,
  setConversations,
  onUpdateConversation,
  onCreateNewConversation,
}: ChatProps) {
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const currentConversation = conversations.find(
    c => c.id === activeConversation
  )
  const messages = useMemo(
    () => currentConversation?.messages || [],
    [currentConversation?.messages]
  )

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

    // If there's no active conversation, create a new one
    if (conversationId == null) {
      const newConversation = onCreateNewConversation()
      conversationId = newConversation.id

      setConversations(prev => [newConversation, ...prev])
      setActiveConversation(conversationId)
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      content,
      role: "user",
      createdAt: new Date(),
    }

    const updatedMessages = [...messages, userMessage]
    onUpdateConversation(conversationId, updatedMessages)

    // Simulate AI response
    setIsLoading(true)
    try {
      // TODO: Replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 1000))

      const assistantMessage: Message = {
        id: `msg-${Date.now()}-assistant`,
        content:
          "This is a simulated AI response. You'll need to integrate with your actual AI service.",
        role: "assistant",
        createdAt: new Date(),
      }

      onUpdateConversation(conversationId, [
        ...updatedMessages,
        assistantMessage,
      ])
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
              disabled={isLoading}
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
