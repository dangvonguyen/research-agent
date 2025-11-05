import { MessagesSquare, SquarePen } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiClient } from "@/api";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarTrigger,
} from "@/components/ui";
import { cn } from "@/lib/utils";
import type { Conversation } from "@/types";
import {
  RecentChatsSection,
  SearchChatsDialog,
  SidebarSettings,
  SidebarButton,
  SidebarLogo,
  useSidebarActions,
  useSidebarInteractions,
} from "./sidebar";

function AppSidebar() {
  const { chatId } = useParams();

  const [chatData, setChatData] = useState<Conversation[]>([]);

  const {
    searchDialogOpen,
    setSearchDialogOpen,
    handleNewChat,
    handleSelectChat,
    handleDeleteChat: deleteChat,
    handleRenameChat: renameChat,
    handleSearchChats,
  } = useSidebarActions();

  const { open, showLogo, showTrigger, headerHandlers, handleEmptySpaceClick } =
    useSidebarInteractions();

  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const chats = await apiClient.conversations
          .list()
          .then((res) => res.data);
        setChatData(chats);
      } catch (error) {
        console.error("Failed to fetch conversations:", error);
      }
    };

    fetchConversations();
  }, []);

  const handleDeleteChat = useCallback(
    async (conversation: Conversation) => {
      const deleted = await deleteChat(conversation.id, chatId);

      if (deleted) {
        setChatData((prev) =>
          prev.filter((chat) => chat.id !== conversation.id),
        );
      }
    },
    [chatId, deleteChat],
  );

  const handleRenameChat = useCallback(
    async (conversation: Conversation) => {
      const newName = await renameChat(conversation);

      if (newName) {
        setChatData((prev) =>
          prev.map((chat) =>
            chat.id === conversation.id ? { ...chat, name: newName } : chat,
          ),
        );
      }
    },
    [renameChat],
  );

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarGroup className="p-0">
          <SidebarGroupContent>
            <SidebarMenu
              className={cn(
                "flex flex-row items-center gap-2 transition-all duration-300",
                open && "justify-between",
              )}
              {...headerHandlers}
            >
              {showLogo && <SidebarLogo size={20} />}
              {showTrigger && (
                <SidebarTrigger className="size-8 cursor-e-resize hover:bg-sidebar-accent transition-transform" />
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarHeader>

      <SidebarContent
        className={cn("gap-0", !open && "cursor-e-resize")}
        onClick={handleEmptySpaceClick}
      >
        <SidebarGroup>
          <SidebarMenu>
            <SidebarButton
              icon={<SquarePen />}
              label="New chat"
              onClick={handleNewChat}
            />
            <SidebarButton
              icon={<MessagesSquare />}
              label="Search chats"
              onClick={handleSearchChats}
            />
          </SidebarMenu>
        </SidebarGroup>
        <RecentChatsSection
          chatData={chatData}
          activeChatId={chatId}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
          onRenameChat={handleRenameChat}
        />
      </SidebarContent>

      <SidebarFooter>
        <SidebarSettings />
      </SidebarFooter>

      <SearchChatsDialog
        open={searchDialogOpen}
        onOpenChange={setSearchDialogOpen}
      />
    </Sidebar>
  );
}

export default AppSidebar;
