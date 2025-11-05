import { Edit3, MoreHorizontal, Trash2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui";
import type { Conversation } from "@/types";

type RecentChatsSectionProps = {
  chatData: Conversation[];
  activeChatId?: string;
  onSelectChat: (chatId: string) => void;
  onDeleteChat: (chat: Conversation) => void | Promise<void>;
  onRenameChat: (chat: Conversation) => void | Promise<void>;
};

export const RecentChatsSection = ({
  chatData,
  activeChatId,
  onSelectChat,
  onDeleteChat,
  onRenameChat,
}: RecentChatsSectionProps) => {
  const hasChats = chatData.length > 0;

  return (
    <SidebarGroup className="flex-1 overflow-x-hidden overflow-y-auto scrollbar-thin transition-opacity duration-200 group-data-[collapsible=icon]:opacity-0 group-data-[collapsible=icon]:pointer-events-none">
      <SidebarGroupLabel className="w-56 group-data-[collapsible=icon]:m-0 group-data-[collapsible=icon]:opacity-100">
        Recent chats
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu className="gap-0">
          {!hasChats ? (
            <div className="w-60 text-sm text-muted-foreground text-center py-2">
              No chats yet
            </div>
          ) : (
            chatData.map((chat) => (
              <SidebarMenuItem key={chat.id} className="group/actions">
                <SidebarMenuButton
                  isActive={activeChatId === chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  className="hover:bg-sidebar-accent/70 data-[active=true]:hover:bg-sidebar-accent/70 data-[active=true]:font-normal"
                >
                  <span title={chat.name}>{chat.name}</span>
                </SidebarMenuButton>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <SidebarMenuAction
                      className="
                        cursor-pointer rounded-3xl hover:bg-inherit
                        focus-visible:ring-1 transition-opacity
                        opacity-0 group-hover/actions:opacity-100
                        pointer-events-none group-hover/actions:pointer-events-auto
                        data-[state=open]:opacity-100
                        data-[state=open]:pointer-events-auto
                    "
                    >
                      <MoreHorizontal className="h-4 w-4" />
                      <span className="sr-only">More actions</span>
                    </SidebarMenuAction>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent side="bottom" align="end">
                    <DropdownMenuItem onClick={() => onRenameChat(chat)}>
                      <Edit3 className="h-4 w-4 mr-1" />
                      Rename
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      variant="destructive"
                      onClick={() => onDeleteChat(chat)}
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
  );
};
