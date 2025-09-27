import { useEffect, useState } from "react"

import { apiClient } from "@/api"
import AppSidebar from "@/components/AppSidebar"
import Chat from "@/components/Chat"
import { SidebarProvider } from "@/components/ui"

import type { Conversation } from "@/types"

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversation, setActiveConversation] = useState<string | null>(
    null
  )

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const convs = await apiClient.conversations.list()

        setConversations(convs.data)
      } catch (error) {
        console.error("Failed to fetch conversations:", error)
      }
    }

    fetchConversations()
  }, [])

  return (
    <SidebarProvider>
      <AppSidebar
        conversations={conversations}
        setConversations={setConversations}
        activeConversation={activeConversation}
        setActiveConversation={setActiveConversation}
      />
      <Chat
        activeConversation={activeConversation}
        setActiveConversation={setActiveConversation}
        conversations={conversations}
        setConversations={setConversations}
      />
    </SidebarProvider>
  )
}

export default App
