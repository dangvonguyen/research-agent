import { useEffect, useState } from "react";
import { useLoaderData } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import { useAutoScroll } from "@/hooks/use-auto-scroll";
import { cn } from "@/lib/utils";
import { useStreamChat } from "../hooks/useStreamChat";
import type { ChatLoaderData } from "../types";
import ChatComposer from "./ChatComposer";

function Chat() {
  const { id, initialMessages } = useLoaderData() as ChatLoaderData;

  const [messages, setMessages] = useState(initialMessages);
  const {
    isStreaming,
    streamingMessageId,
    streamedContent,
    startStream,
    resetStream,
  } = useStreamChat();

  const bottomRef = useAutoScroll({
    deps: messages,
    shouldScroll: (latest) => latest.role === "user",
  });

  useEffect(() => {
    if (!streamingMessageId) return;

    setMessages((prev) => {
      if (prev.some((msg) => msg.id === streamingMessageId)) {
        return prev.map((msg) =>
          msg.id === streamingMessageId
            ? { ...msg, content: streamedContent }
            : msg,
        );
      } else {
        return [
          ...prev,
          {
            id: streamingMessageId,
            content: streamedContent,
            role: "assistant",
            conversation_id: id,
            created_at: new Date().toISOString(),
          },
        ];
      }
    });
  }, [streamingMessageId, streamedContent, id]);

  // Show toast error if any
  useEffect(() => {
    const msg = sessionStorage.getItem("toastError");
    if (msg) {
      toast.error(msg);
      sessionStorage.removeItem("toastError");
    }
  }, []);

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

    const userMessage = await apiClient.conversations
      .createMessage(id, { content, role: "user" })
      .then((res) => res.data);

    setMessages((prev) => [...prev, userMessage]);

    if (window.location.pathname !== `/chat/${id}`) {
      window.history.replaceState(null, "", `/chat/${id}`);
    }

    try {
      await startStream({
        conversation_id: id,
        message_id: userMessage.id,
      });

      resetStream();
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to send message. Please try again.");
    }
  };

  return (
    <div className="w-full h-screen overflow-y-auto scrollbar-thin">
      <div
        className={cn(
          "grid w-full h-screen mx-auto px-8 max-w-[52rem]",
          messages.length === 0
            ? "grid-rows-[40vh_auto]"
            : "grid-rows-[1fr_auto]",
        )}
      >
        {/* Messages Container */}
        {messages.length === 0 ? (
          <div className="flex justify-center items-end pb-10">
            <h1 className="text-3xl">What's on your mind today?</h1>
          </div>
        ) : (
          // TODO: implement files preview in user message
          <div className="flex flex-col gap-10 pt-[7vh] pb-[10vh] whitespace-pre-wrap">
            {messages.map((message) => (
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
            {isStreaming && (
              <div className="flex gap-1.5">
                <div className="w-1.5 h-1.5 bg-current rounded-3xl animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-1.5 h-1.5 bg-current rounded-3xl animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-current rounded-3xl animate-bounce"></div>
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={bottomRef} />
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
              disabled={isStreaming}
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
  );
}

export default Chat;
