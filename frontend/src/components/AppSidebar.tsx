import { LayoutDashboard, MessagesSquare, SquarePen } from "lucide-react";
import { useCallback, useEffect, useState, useRef } from "react";
import { useLocation, useParams, useNavigate } from "react-router-dom";
import { apiClient } from "@/api";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
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
  const location = useLocation();
  const navigate = useNavigate();

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
    let isMounted = true;
    let isFetching = false;

    const fetchConversations = async () => {
      // Prevent duplicate concurrent calls
      if (isFetching) return;
      isFetching = true;

      try {
        const chats = await apiClient.conversations
          .list()
          .then((res) => res.data);
        if (isMounted) {
          setChatData(chats);
        }
      } catch (error) {
        console.error("Failed to fetch conversations:", error);
      } finally {
        isFetching = false;
      }
    };

    fetchConversations();

    return () => {
      isMounted = false;
    };
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
        {/* Navigation Section */}
        <SidebarGroup>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => navigate("/dashboard")}
                isActive={location.pathname.startsWith("/dashboard")}
                tooltip="Dashboard"
                className="group/button cursor-pointer"
              >
                <LayoutDashboard className="h-4 w-4" />
                <span className="text-sm">Dashboard</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                onClick={() => navigate("/")}
                isActive={location.pathname === "/" || location.pathname.startsWith("/chat")}
                tooltip="Chatbot"
                className="group/button cursor-pointer"
              >
                <MessagesSquare className="h-4 w-4" />
                <span className="text-sm">Chatbot</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>

        {/* Chat Actions - Only show in Chatbot view */}
        {(location.pathname === "/" || location.pathname.startsWith("/chat")) && (
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
        )}

        {/* Recent Chats - Only show in Chatbot view */}
        {(location.pathname === "/" || location.pathname.startsWith("/chat")) && (
          <RecentChatsSection
            chatData={chatData}
            activeChatId={chatId}
            onSelectChat={handleSelectChat}
            onDeleteChat={handleDeleteChat}
            onRenameChat={handleRenameChat}
          />
        )}
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
