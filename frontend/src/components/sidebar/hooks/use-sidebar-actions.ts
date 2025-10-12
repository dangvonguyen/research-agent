import { useCallback, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiClient } from "@/api";
import type { Conversation } from "@/types";

export const useSidebarActions = () => {
  const navigate = useNavigate();
  const location = useLocation();

  // Dialog states
  const [searchDialogOpen, setSearchDialogOpen] = useState(false);

  const handleNewChat = useCallback(() => {
    if (location.pathname !== "/") {
      navigate("/");
    }
  }, [location.pathname, navigate]);

  const handleSelectChat = useCallback(
    (chatId: string) => {
      navigate(`/chat/${chatId}`);
    },
    [navigate],
  );

  const handleDeleteChat = useCallback(
    async (chatId: string, activeChatId?: string) => {
      if (!window.confirm("Delete chat?")) {
        return false;
      }

      try {
        await apiClient.conversations.delete(chatId);

        if (activeChatId === chatId) {
          navigate("/");
        }
        return true;
      } catch (error) {
        console.error("Failed to delete conversation:", error);
        return false;
      }
    },
    [navigate],
  );

  const handleRenameChat = useCallback(async (conversation: Conversation) => {
    const newTitle = prompt("Enter new conversation title:", conversation.name);

    if (!newTitle) {
      return undefined;
    }

    const trimmedTitle = newTitle.trim();

    if (!trimmedTitle || trimmedTitle === conversation.name) {
      return undefined;
    }

    try {
      await apiClient.conversations.update(conversation.id, {
        name: trimmedTitle,
      });
      return trimmedTitle;
    } catch (error) {
      console.error("Failed to rename conversation:", error);
      return undefined;
    }
  }, []);

  const handleSearchChats = useCallback(() => {
    setSearchDialogOpen(true);
  }, []);

  return {
    searchDialogOpen,
    setSearchDialogOpen,
    handleNewChat,
    handleSelectChat,
    handleDeleteChat,
    handleRenameChat,
    handleSearchChats,
  };
};
