import { MessageSquareQuote } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "@/api";
import {
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  Input,
} from "@/components/ui";
import type { Conversation } from "@/types";

const getRelativeTime = (dateString: string): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

  if (diffInHours < 24) {
    return "Today";
  } else if (diffInHours < 48) {
    return "Yesterday";
  } else if (diffInHours < 24 * 7) {
    return "This week";
  } else if (diffInHours < 24 * 30) {
    return "This month";
  } else {
    return "Older";
  }
};

const fetchConversations = async (): Promise<Conversation[]> => {
  try {
    return await apiClient.conversations.list().then((res) => res.data);
  } catch (error) {
    console.error("Error fetching conversations:", error);
    return [];
  }
};

interface SearchChatsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const SearchChatsDialog = ({
  open,
  onOpenChange,
}: SearchChatsDialogProps) => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [chats, setChats] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch chats when dialog opens
  useEffect(() => {
    if (open) {
      setIsLoading(true);

      fetchConversations()
        .then(setChats)
        .finally(() => setIsLoading(false));
    }
  }, [open]);

  const filteredChats = useMemo(
    () =>
      chats.filter((chat) =>
        chat.name.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    [chats, searchQuery],
  );

  const groupedChats = useMemo(() => {
    const grouped = filteredChats.reduce(
      (groups, chat) => {
        const group = getRelativeTime(chat.updated_at);
        if (!groups[group]) {
          groups[group] = [];
        }
        groups[group].push(chat);
        return groups;
      },
      {} as Record<string, Conversation[]>,
    );

    return Object.entries(grouped);
  }, [filteredChats]);

  const handleChatSelect = (chatId: string) => {
    navigate(`/chat/${chatId}`);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex flex-col min-w-2xl pt-4 rounded-3xl"
        showCloseButton={false}
      >
        <DialogHeader className="border-b pb-2">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="border-0 shadow-none focus-visible:ring-0 px-0 text-sm"
          />
        </DialogHeader>

        <div className="h-96 overflow-y-auto scrollbar-thin">
          {isLoading ? (
            <div className="text-center py-8 text-gray-500 text-sm">
              Loading chats...
            </div>
          ) : groupedChats.length > 0 ? (
            groupedChats.map(([group, chats]) => (
              <div key={group} className="mb-4">
                <h3 className="text-xs font-medium text-gray-500 mb-2">
                  {group}
                </h3>
                <div className="space-y-1">
                  {chats.map((chat) => (
                    <Button
                      key={chat.id}
                      variant="ghost"
                      className="w-full flex items-center text-left"
                      onClick={() => handleChatSelect(chat.id)}
                    >
                      <MessageSquareQuote className="size-4" />
                      <span className="flex-1 truncate">{chat.name}</span>
                    </Button>
                  ))}
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-gray-500 text-sm">
              {searchQuery
                ? "No chats found matching your search"
                : "No chats found"}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
