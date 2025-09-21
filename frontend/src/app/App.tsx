import { useState } from "react"

import AppSidebar from "@/components/AppSidebar"
import Chat from "@/components/Chat"
import { SidebarProvider } from "@/components/ui"

import type { Conversation, Message } from "@/types"

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversation, setActiveConversation] = useState<string | null>(
    null
  )
  const [searchQuery, setSearchQuery] = useState("")

  const createNewChat = (): Conversation => {
    const newConversation: Conversation = {
      id: `conv-${Date.now()}`,
      title: "New Chat",
      messages: [],
      lastMessageAt: new Date(),
    }
    return newConversation
  }

  const updateConversation = (conversationId: string, messages: Message[]) => {
    setConversations(prev =>
      prev.map(conv => {
        if (conv.id === conversationId) {
          // Auto-generate title from first user message if it's still "New Chat"
          let title = conv.title
          if (title === "New Chat" && messages.length > 0) {
            const firstUserMessage = messages.find(m => m.role === "user")
            if (firstUserMessage) {
              title =
                firstUserMessage.content.slice(0, 50) +
                (firstUserMessage.content.length > 50 ? "..." : "")
            }
          }

          return {
            ...conv,
            title,
            messages,
            lastMessageAt: new Date(),
          }
        }
        return conv
      })
    )
  }

  const deleteConversation = (conversationId: string) => {
    setConversations(prev => prev.filter(conv => conv.id !== conversationId))
    if (activeConversation === conversationId) {
      setActiveConversation(null)
    }
  }

  const renameConversation = (conversationId: string, newTitle: string) => {
    setConversations(prev =>
      prev.map(conv =>
        conv.id === conversationId ? { ...conv, title: newTitle } : conv
      )
    )
  }

  return (
    <SidebarProvider>
      <AppSidebar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        conversations={conversations}
        activeConversation={activeConversation}
        setActiveConversation={setActiveConversation}
        onSelectConversation={setActiveConversation}
        onDeleteConversation={deleteConversation}
        onRenameConversation={renameConversation}
      />
      <Chat
        activeConversation={activeConversation}
        setActiveConversation={setActiveConversation}
        conversations={conversations}
        setConversations={setConversations}
        onUpdateConversation={updateConversation}
        onCreateNewConversation={createNewChat}
      />
    </SidebarProvider>
  )
}

export default App
