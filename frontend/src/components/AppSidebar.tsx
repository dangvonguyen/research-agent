import { Edit3, MoreHorizontal, Search, SquarePen, Trash2 } from "lucide-react"

import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Input,
  Label,
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "./ui"

import type { Conversation } from "@/types"

interface AppSidebarProps {
  searchQuery?: string
  setSearchQuery: (q: string) => void
  conversations: Conversation[]
  activeConversation: string | null
  setActiveConversation: React.Dispatch<React.SetStateAction<string | null>>
  onSelectConversation: (conversationId: string) => void
  onDeleteConversation: (conversationId: string) => void
  onRenameConversation: (conversationId: string, newTitle: string) => void
}

function AppSidebar({
  searchQuery = "",
  setSearchQuery,
  conversations = [],
  activeConversation,
  setActiveConversation,
  onSelectConversation,
  onDeleteConversation,
  onRenameConversation,
}: AppSidebarProps) {
  const filteredConversations = conversations.filter(conversation =>
    conversation.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleRename = (conversationId: string) => {
    const conversation = conversations.find(c => c.id === conversationId)
    if (!conversation) return

    console.log("hi")

    const newTitle = prompt("Enter new conversation title:", conversation.title)
    if (newTitle && newTitle.trim() && newTitle !== conversation.title) {
      onRenameConversation(conversationId, newTitle.trim())
    }
  }

  return (
    <Sidebar collapsible="offcanvas" className="flex flex-col h-full">
      {/* Fixed header */}
      <SidebarHeader className="flex-shrink-0">
        <div className="w-full">
          <Button
            onClick={() => setActiveConversation(null)}
            size="lg"
            className="w-full justify-start cursor-pointer"
          >
            <SquarePen />
            New chat
          </Button>
        </div>
        <div className="relative w-full">
          <Label
            htmlFor="chat-search"
            className="absolute left-3 top-1/4 cursor-text text-muted-foreground"
          >
            <Search className="h-5 w-5" />
          </Label>
          <Input
            id="chat-search"
            placeholder="Search chats"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="h-10 pl-10 rounded-md focus-visible:ring-0"
          />
        </div>
      </SidebarHeader>

      {/* Chat list */}
      <SidebarContent className="scrollbar-thin">
        <SidebarGroup>
          <SidebarGroupLabel>Recent chats</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {filteredConversations.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-2">
                  {searchQuery
                    ? "No matching conversations"
                    : "No conversations yet"}
                </div>
              ) : (
                filteredConversations.map(conversation => (
                  <SidebarMenuItem
                    key={conversation.id}
                    className={`group/actions rounded-md ${
                      activeConversation === conversation.id
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "hover:bg-sidebar-accent/50"
                    }`}
                  >
                    <SidebarMenuButton
                      onClick={() => onSelectConversation(conversation.id)}
                      className="cursor-pointer font-medium text-sm truncate"
                    >
                      {conversation.title}
                    </SidebarMenuButton>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuAction
                          className="
                            cursor-pointer rounded-3xl
                            focus-visible:ring-1 transition-opacity
                            opacity-0 group-hover/actions:opacity-100
                            pointer-events-none group-hover/actions:pointer-events-auto
                            data-[state=open]:opacity-100
                            data-[state=open]:pointer-events-auto
                          "
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </SidebarMenuAction>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent side="bottom" align="end">
                        <DropdownMenuItem
                          onClick={e => {
                            console.log(conversation.id)
                            e.stopPropagation()
                            console.log("foo")
                            handleRename(conversation.id)
                            console.log("hmm")
                          }}
                        >
                          <Edit3 className="h-4 w-4 mr-1" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={e => {
                            e.stopPropagation()
                            if (confirm("Delete chat?")) {
                              onDeleteConversation(conversation.id)
                            }
                          }}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}

export default AppSidebar
