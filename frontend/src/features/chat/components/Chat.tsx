import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import type { Role, ToolResultOutput } from "@/api/models";
import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationCarousel,
  InlineCitationCarouselContent,
  InlineCitationCarouselItem,
  InlineCitationCarouselHeader,
  InlineCitationCarouselIndex,
  InlineCitationCarouselPrev,
  InlineCitationCarouselNext,
  InlineCitationSource,
  type CitationsData,
  MessageAttachment,
  MessageAttachments,
  MessageContent,
  MessageResponse,
  PaperCard,
  type PaperRecommendationsData,
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
import { SavePaperModal } from "../../collections/components/SavePaperModal";

interface ChatProps {
  id: string;
  initialMessages: Message[];
}

function Chat({ id, initialMessages }: ChatProps) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(initialMessages);
  const { status, messageId, submitChat, startChat, stopChat, contentParts } =
    useChat();
  const [isSavePaperModalOpen, setIsSavePaperModalOpen] = useState(false);
  const [paperUrlToSave, setPaperUrlToSave] = useState<string>("");

  const bottomRef = useAutoScroll({
    deps: messages,
    shouldScroll: (latest) => latest.role === "user",
  });

  useEffect(() => {
    if (!messageId) return;

    setMessages((prev) => {
      if (prev.some((msg) => msg.id === messageId)) {
        return prev.map((msg) =>
          msg.id === messageId ? { ...msg, content: contentParts } : msg
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
    contentParts: MessageContentPart[]
  ): MessageToolResultPart | undefined => {
    return contentParts.find((part): part is MessageToolResultPart => {
      return part.type === "tool-result" && part.tool_call_id === toolCallId;
    });
  };

  const getToolState = (
    result: MessageToolResultPart | undefined,
    isStreaming: boolean
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
    output: ToolResultOutput
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
    role: Role
  ) => {
    switch (part.type) {
      case "text": {
        const key = `${message.id}-${index}`;
        return role === "user" ? (
          <div key={key} className="wrap-break-word">
            {part.text}
          </div>
        ) : (
          <MessageResponse key={key} className="wrap-break-word">
            {part.text}
          </MessageResponse>
        );
      }
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
            className="wrap-break-word"
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
      case "ui-event": {
        // Render UI event based on event_type
        if (part.event_type === "paper_recommendations") {
          try {
            const data = part.data as PaperRecommendationsData;
            return (
              <PaperCard
                key={`${message.id}-${index}-ui-event`}
                data={data}
                onAddToLibrary={(paper) => {
                  setPaperUrlToSave(paper.url);
                  setIsSavePaperModalOpen(true);
                }}
              />
            );
          } catch (error) {
            console.error("Error rendering paper recommendations:", error);
            return (
              <div
                key={`${message.id}-${index}-ui-event-error`}
                className="text-sm text-muted-foreground"
              >
                Error rendering UI event
              </div>
            );
          }
        }
        if (part.event_type === "citations") {
          try {
            const data = part.data as unknown as CitationsData;
            // Normalize to array
            const citationsArray = Array.isArray(data.citations)
              ? data.citations
              : [data.citations];

            // Filter out invalid citations
            const validCitations = citationsArray.filter(
              (citation) => citation && citation.url
            );

            if (validCitations.length === 0) return null;

            // Extract URLs for the trigger badge
            const sources = validCitations.map((c) => c.url);

            // Render citations inline using ai-elements with carousel
            return (
              <InlineCitation
                key={`${message.id}-${index}-ui-event-citations`}
                className="inline-flex items-center gap-1"
              >
                <InlineCitationCard>
                  <InlineCitationCardTrigger sources={sources} />
                  <InlineCitationCardBody>
                    <InlineCitationCarousel>
                      <InlineCitationCarouselHeader>
                        <InlineCitationCarouselPrev />
                        <InlineCitationCarouselNext />
                        <InlineCitationCarouselIndex />
                      </InlineCitationCarouselHeader>
                      <InlineCitationCarouselContent>
                        {validCitations.map((citation, idx) => (
                          <InlineCitationCarouselItem key={idx}>
                            <InlineCitationSource
                              title={citation.title}
                              url={citation.url}
                              description={citation.text}
                            />
                          </InlineCitationCarouselItem>
                        ))}
                      </InlineCitationCarouselContent>
                    </InlineCitationCarousel>
                  </InlineCitationCardBody>
                </InlineCitationCard>
              </InlineCitation>
            );
          } catch (error) {
            console.error("Error rendering citations:", error);
            return (
              <div
                key={`${message.id}-${index}-ui-event-error`}
                className="text-sm text-muted-foreground"
              >
                Error rendering citations
              </div>
            );
          }
        }
        // Unknown UI event type
        return (
          <div
            key={`${message.id}-${index}-ui-event-unknown`}
            className="text-sm text-muted-foreground"
          >
            Unknown UI event type: {part.event_type}
          </div>
        );
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
            : "grid-rows-[1fr_auto]"
        )}
      >
        {/* Messages Container */}
        {messages.length === 0 ? (
          <div className="flex justify-center items-end pb-10">
            <h1 className="text-3xl">What's on your mind today?</h1>
          </div>
        ) : (
          <div className="max-w-3xl flex flex-col gap-10 pt-[7vh] pb-[10vh] whitespace-pre-wrap">
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

                <MessageContent className="w-full">
                  {message.content.map((part, index) =>
                    renderContentPart(part, index, message, message.role)
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
        <div className="max-w-3xl sticky bottom-0">
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
      <SavePaperModal
        isOpen={isSavePaperModalOpen}
        onClose={() => {
          setIsSavePaperModalOpen(false);
          setPaperUrlToSave("");
        }}
        initialUrl={paperUrlToSave}
        initialTab="url"
      />
    </div>
  );
}

export default Chat;
