import { ArrowUp, FileText, Paperclip, Plus, X } from "lucide-react";
import type React from "react";
import { useRef, useState } from "react";
import {
  Button,
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Label,
  Textarea,
} from "@/components/ui";

interface ChatComposerProps {
  onSend: (message: string, files?: File[]) => void;
  placeholder: string;
  disabled: boolean;
}

function ChatComposer({
  onSend,
  placeholder = "Ask anything",
  disabled,
}: ChatComposerProps) {
  const [message, setMessage] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const canSendMessage = (message.trim() || files.length) && !disabled;

  const handleSend = () => {
    if (!canSendMessage) return;

    onSend(message, files);
    setMessage("");
    setFiles([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFilesSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newFiles = e.target.files ? Array.from(e.target.files) : [];

    if (!newFiles.length) return;

    setFiles((prev) => {
      const uniqueNewFiles = newFiles.filter(
        (newFile) =>
          newFile.size > 0 &&
          !prev.some(
            (existingFile) =>
              existingFile.name === newFile.name &&
              existingFile.size === newFile.size,
          ),
      );
      return [...prev, ...uniqueNewFiles];
    });
    e.target.value = "";
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <Label htmlFor="chat-composer-input" className="w-full cursor-text">
      <Card className="w-full gap-1 rounded-3xl pt-0 pb-2 shadow-none overflow-hidden">
        {/* File Previews */}
        {files.length > 0 && (
          <CardHeader className="flex px-2 pt-2 gap-2 overflow-x-auto scrollbar-none">
            {files.map((file, index) => (
              <div
                key={`${index}-${file.name}`}
                className="min-w-60 flex items-center justify-between rounded-2xl border bg-muted p-2"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-blue-500" />
                  <div className="flex flex-col">
                    <span className="text-sm font-medium truncate max-w-42">
                      {file.name}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {file.type || "Unknown type"}
                    </span>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveFile(index)}
                  className="h-6 w-6 cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </CardHeader>
        )}

        {/* Chat Input */}
        <CardContent className="px-4">
          <Textarea
            id="chat-composer-input"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="min-h-0 max-h-[25vh] md:text-base font-normal resize-none border-0 rounded-none p-0 pt-4 shadow-none focus-visible:ring-0 scrollbar-thin dark:bg-inherit"
          />
        </CardContent>

        {/* Utilities */}
        <CardFooter className="justify-between px-2 border-0 m-0">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="cursor-pointer rounded-3xl focus-visible:ring-2"
              >
                <Plus />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-54 rounded-xl">
              <DropdownMenuItem
                onClick={handleFileUpload}
                className="cursor-pointer rounded-lg"
                disabled // TODO: not supported yet
              >
                <span>
                  <Paperclip />
                </span>
                <span>Upload photos & files</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button
            variant={canSendMessage ? "default" : "ghost"}
            size="icon"
            onClick={handleSend}
            className={`rounded-3xl focus-visible:ring-2 ${
              canSendMessage
                ? "cursor-pointer"
                : "cursor-not-allowed hover:bg-none"
            }`}
          >
            <ArrowUp strokeWidth={3} />
          </Button>
        </CardFooter>
      </Card>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFilesSelected}
      />
    </Label>
  );
}

export default ChatComposer;
