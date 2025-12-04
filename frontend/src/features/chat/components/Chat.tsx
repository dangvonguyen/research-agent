import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  MessageAttachment,
  MessageAttachments,
  MessageContent,
  MessageResponse,
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
  Message as UIMessage,
} from "@/components/ai-elements";
import { useAutoScroll } from "@/hooks/use-auto-scroll";
import { cn } from "@/lib/utils";
import { useChat } from "../hooks/useChat";
import type { Attachment, Message } from "../types";
import ChatComposer from "./ChatComposer";

interface ChatProps {
  id: string;
  initialMessages: Message[];
}

function Chat({ id, initialMessages }: ChatProps) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(initialMessages);
  const { status, messageId, submitChat, startChat, stopChat, contentParts } =
    useChat();
  const isStreaming = status === "streaming" || status === "submitted";

  const bottomRef = useAutoScroll({
    deps: messages,
    shouldScroll: (latest) => latest.role === "user",
  });

  useEffect(() => {
    if (!messageId) return;

    setMessages((prev) => {
      if (prev.some((msg) => msg.id === messageId)) {
        return prev.map((msg) =>
          msg.id === messageId ? { ...msg, content: contentParts } : msg,
        );
      } else {
        return [
          ...prev,
          {
            id: messageId,
            content: contentParts,
            role: "assistant",
            conversation_id: id,
            created_at: new Date().toISOString(),
          },
        ];
      }
    });
  }, [messageId, contentParts, id]);

  // Show toast error if any
  useEffect(() => {
    const msg = sessionStorage.getItem("toastError");
    if (msg) {
      toast.error(msg);
      sessionStorage.removeItem("toastError");
    }
  }, []);

  const handleSendMessage = async (content: string, files?: File[]) => {
    if (!content.trim() && (!files || files.length === 0)) return;

    try {
      // Upload files if any
      let attachments: Attachment[] = [];
      if (files && files.length > 0) {
        const uploadResponse = await apiClient.uploads.uploadFiles(files);
        attachments = uploadResponse.data;
      }

      // Set status to "submitted"
      submitChat();

      // Create message with content and attachments
      const userMessage = await apiClient.conversations
        .createMessage(id, {
          content: [{ type: "text", text: content }],
          role: "user",
          attachments: attachments,
        })
        .then((res) => res.data);

      setMessages((prev) => [...prev, userMessage]);

      const shouldNavigate = window.location.pathname !== `/chat/${id}`;

      await startChat({
        conversation_id: id,
        message_id: userMessage.id,
      });

      if (shouldNavigate) {
        navigate(`/chat/${id}`);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("Failed to send message. Please try again.");
    }
  };

  return (
    <div className="w-full h-screen overflow-y-auto scrollbar-thin">
      <div
        className={cn(
          "grid w-full h-screen mx-auto px-8 max-w-208",
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
          <div className="flex flex-col gap-10 pt-[7vh] pb-[10vh] whitespace-pre-wrap">
            {messages.map((message) => (
              <UIMessage from={message.role} key={message.id}>
                {message.attachments && message.attachments.length > 0 && (
                  <MessageAttachments>
                    {message.attachments.map((att) => (
                      <MessageAttachment
                        key={att.path}
                        data={{
                          type: "file",
                          url: att.path,
                          mediaType: att.content_type,
                          filename: att.name,
                        }}
                      />
                    ))}
                  </MessageAttachments>
                )}

                <MessageContent>
                  {message.content.map((part, index) => {
                    switch (part.type) {
                      case "text":
                        return (
                          <MessageResponse key={`${message.id}-${index}`}>
                            {part.text}
                          </MessageResponse>
                        );
                      case "reasoning":
                        return (
                          <Reasoning
                            key={`${message.id}-${index}`}
                            defaultOpen={
                              isStreaming && message.id === messageId
                            }
                            isStreaming={
                              isStreaming &&
                              index === message.content.length - 1 &&
                              message.id === messageId
                            }
                          >
                            <ReasoningTrigger />
                            <ReasoningContent>{part.text}</ReasoningContent>
                          </Reasoning>
                        );
                      default:
                        return null;
                    }
                  })}
                </MessageContent>
              </UIMessage>
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
              status={status}
              onSend={handleSendMessage}
              onStop={stopChat}
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
