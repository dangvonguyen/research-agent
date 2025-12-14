import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import type { ToolResultOutput } from "@/api/models";
import {
  MessageAttachment,
  MessageAttachments,
  MessageContent,
  MessageResponse,
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
  Tool,
  ToolContent,
  ToolHeader,
  ToolInput,
  ToolOutput,
  Message as UIMessage,
} from "@/components/ai-elements";
import { useAutoScroll } from "@/hooks/use-auto-scroll";
import { cn } from "@/lib/utils";
import { useChat } from "../hooks/useChat";
import type {
  Attachment,
  Message,
  MessageContentPart,
  MessageToolResultPart,
  SubAgentOutput,
  ToolState,
} from "../types";
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

  const findToolResult = (
    toolCallId: string,
    contentParts: MessageContentPart[],
  ): MessageToolResultPart | undefined => {
    return contentParts.find((part): part is MessageToolResultPart => {
      return part.type === "tool-result" && part.tool_call_id === toolCallId;
    });
  };

  const getToolState = (
    result: MessageToolResultPart | undefined,
    isStreaming: boolean,
  ): ToolState => {
    if (!result) {
      return isStreaming ? "input-streaming" : "input-available";
    }

    // Check if result has error
    if (
      result.output.type === "error-text" ||
      result.output.type === "error-json"
    ) {
      return "output-error";
    }

    return "output-available";
  };

  const parseToolOutput = (
    output: ToolResultOutput,
  ): {
    output?: unknown;
    error?: string;
    subAgentEvents?: MessageContentPart[];
  } => {
    switch (output.type) {
      case "text":
        return { output: output.value };
      case "json":
        return { output: output.value };
      case "error-text":
        return { error: String(output.value) };
      case "error-json":
        return {
          error:
            typeof output.value === "string"
              ? output.value
              : JSON.stringify(output.value),
        };
      case "content":
      case "sub-agent": {
        const subAgentData = output.value as SubAgentOutput;
        return {
          output: subAgentData.result,
          subAgentEvents: subAgentData.events,
        };
      }
      default:
        return { output: output.value };
    }
  };

  const renderContentPart = (
    part: MessageContentPart,
    index: number,
    message: Message,
  ) => {
    switch (part.type) {
      case "text":
        return (
          <MessageResponse key={`${message.id}-${index}`} className="break-all">
            {part.text}
          </MessageResponse>
        );
      case "reasoning": {
        const isPartStreaming =
          status === "streaming" &&
          message.id === messageId &&
          index === message.content.length - 1;
        return (
          <Reasoning
            key={`${message.id}-${index}`}
            defaultOpen={isPartStreaming}
            isStreaming={isPartStreaming}
            className="break-all"
          >
            <ReasoningTrigger />
            <ReasoningContent>{part.text}</ReasoningContent>
          </Reasoning>
        );
      }
      case "tool-call": {
        const result = findToolResult(part.tool_call_id, message.content);
        const isPartStreaming =
          status === "streaming" && message.id === messageId;
        const toolState = getToolState(result, isPartStreaming);

        const { output, error } = result ? parseToolOutput(result.output) : {};

        return (
          <Tool key={`${message.id}-${part.tool_call_id}`}>
            <ToolHeader
              name={part.tool_name}
              title={part.tool_name}
              state={toolState}
            />
            <ToolContent className="break-all">
              <ToolInput input={part.input} />
              {result && <ToolOutput output={output} errorText={error} />}
            </ToolContent>
          </Tool>
        );
      }
      case "tool-result": {
        return null;
      }
      default:
        return null;
    }
  };

  return (
    <div className="w-full h-screen overflow-y-scroll scrollbar">
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

                <MessageContent className="group-[.is-assistant]:w-full max-w-3xl">
                  {message.content.map((part, index) =>
                    renderContentPart(part, index, message),
                  )}
                </MessageContent>
              </UIMessage>
            ))}

            {/* Loading indicator */}
            {status === "streaming" && (
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
              disabled={status === "submitted" || status === "streaming"}
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
