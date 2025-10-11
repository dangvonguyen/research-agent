import { Edit3, MoreHorizontal, Search, SquarePen, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiClient } from "@/api";
import type { Conversation } from "@/types";
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
} from "./ui";

function AppSidebar() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);

  const { chatId: conversationId } = useParams();

  const filteredConversations = conversations.filter((conversation) =>
    conversation.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleDelete = async (conversation: Conversation) => {
    try {
      await apiClient.conversations.delete(conversation.id);

      setConversations((prev) =>
        prev.filter((conv) => conv.id !== conversation.id),
      );

      if (conversationId === conversation.id) {
        navigate("/");
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error);
    }
  };

  const onSelectConversation = (conversationId: string) => {
    navigate(`/chat/${conversationId}`);
  };

  const handleRename = async (conversation: Conversation) => {
    const newTitle = prompt("Enter new conversation title:", conversation.name);

    if (!newTitle || newTitle.trim() === "" || newTitle === conversation.name) {
      return;
    }

    try {
      await apiClient.conversations.update(conversation.id, {
        name: newTitle.trim(),
      });

      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === conversation.id
            ? { ...conv, name: newTitle.trim() }
            : conv,
        ),
      );
    } catch (error) {
      console.error("Failed to rename conversation:", error);
    }
  };

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const convs = await apiClient.conversations
          .list()
          .then((res) => res.data);
        setConversations(convs);
      } catch (error) {
        console.error("Failed to fetch conversations:", error);
      }
    };

    fetchConversations();
  }, []);

  return (
    <Sidebar collapsible="offcanvas" className="flex flex-col h-full">
      {/* Fixed header */}
      <SidebarHeader className="flex-shrink-0">
        <div className="w-full">
          <Button
            onClick={() => navigate("/")}
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
            onChange={(e) => setSearchQuery(e.target.value)}
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
                filteredConversations.map((conversation) => (
                  <SidebarMenuItem
                    key={conversation.id}
                    className={`group/actions rounded-md ${
                      conversationId === conversation.id
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "hover:bg-sidebar-accent/50"
                    }`}
                  >
                    <SidebarMenuButton
                      onClick={() => onSelectConversation(conversation.id)}
                      className="cursor-pointer font-medium text-sm truncate"
                    >
                      {conversation.name}
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
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRename(conversation);
                          }}
                        >
                          <Edit3 className="h-4 w-4 mr-1" />
                          Rename
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm("Delete chat?")) {
                              handleDelete(conversation);
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
  );
}

export default AppSidebar;
