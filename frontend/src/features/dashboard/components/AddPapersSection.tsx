import { useState, useRef, useImperativeHandle, forwardRef } from "react";
import {
  FileText,
  Link as LinkIcon,
  Upload,
  FolderOpen,
  Download,
} from "lucide-react";
import { Button, Input, Label, Textarea, Card, CardContent } from "@/components/ui";
import { apiClient } from "@/api";
import { toast } from "sonner";

interface AddPapersSectionProps {
  onJobCreated?: (jobId: string) => void;
}

export interface AddPapersSectionRef {
  triggerFileUpload: () => void;
}

export const AddPapersSection = forwardRef<
  AddPapersSectionRef,
  AddPapersSectionProps
>(({ onJobCreated }, ref) => {
  const [paperUrl, setPaperUrl] = useState("");
  const [maxPapers, setMaxPapers] = useState<string>("5");
  const [uploading, setUploading] = useState(false);
  const [activeView, setActiveView] = useState<"upload" | "url">("upload");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useImperativeHandle(ref, () => ({
    triggerFileUpload: () => {
      fileInputRef.current?.click();
    },
  }));

  const handleFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setUploading(true);
    try {
      // For now, we'll just show a toast since the backend might need specific handling
      toast.info("File upload functionality is being processed...");
      // TODO: Implement actual file upload to papers endpoint
    } catch (error) {
      console.error("Failed to upload file:", error);
      toast.error("Failed to upload file. Please try again.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleUrlImport = async () => {
    if (!paperUrl.trim()) {
      toast.error("Please enter a paper URL");
      return;
    }

    setUploading(true);
    try {
      // Use the search API to import via URL
      const urls = paperUrl
        .split("\n")
        .map((url) => url.trim())
        .filter((url) => url.length > 0);

      if (urls.length === 0) {
        toast.error("Please enter a valid URL");
        return;
      }

      // Determine source from URL
      let source: "acl_anthology" | "arxiv" | "ieee" = "acl_anthology";
      if (urls[0].includes("arxiv.org")) {
        source = "arxiv";
      } else if (urls[0].includes("ieee.org") || urls[0].includes("ieeexplore")) {
        source = "ieee";
      }

      // Create a crawler job to import the paper
      const configs = await apiClient.crawlerConfigs.list();
      const matchedConfig = configs.find(
        (c) => c.source === source.toLowerCase(),
      );

      if (!matchedConfig) {
        toast.error(`No config found for source: ${source}`);
        return;
      }

      const maxPapersValue = maxPapers.trim() === "" ? 5 : parseInt(maxPapers, 10);
      
      const response = await apiClient.crawlerJobs.create({
        config_name: matchedConfig.name,
        query: null,
        urls: urls,
        max_papers: maxPapersValue > 0 ? maxPapersValue : null,
      });
      
      // Notify parent about the new job ID
      if (response.created_ids && response.created_ids.length > 0 && onJobCreated) {
        onJobCreated(response.created_ids[0]);
      }
      
      toast.success("Paper import started. Papers will appear in your library as they are processed.");
      setPaperUrl("");
      setMaxPapers("5");
    } catch (error) {
      console.error("Failed to import paper:", error);
      toast.error("Failed to import paper. Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="py-0">
      <CardContent className="p-3 px-3">
        <div className="space-y-4">
          {/* Toggle Buttons */}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              variant={activeView === "upload" ? "default" : "outline"}
              onClick={() => setActiveView("upload")}
              className="rounded-lg"
            >
              Upload PDF
            </Button>
            <Button
              type="button"
              variant={activeView === "url" ? "default" : "outline"}
              onClick={() => setActiveView("url")}
              className="rounded-lg"
            >
              Import URL
            </Button>
          </div>

          {/* Content Container - Fixed height to prevent layout shift */}
          <div className="relative min-h-[60px]">
            {/* Upload PDF Section */}
            <div className={activeView === "upload" ? "block" : "hidden"}>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1 flex items-center gap-2 px-4 py-2 border rounded-lg bg-background">
                    <FileText className="h-5 w-5 text-muted-foreground" />
                    <span className="text-sm text-muted-foreground">
                      Upload PDF from device
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1 text-xs text-muted-foreground">
                      <span className="px-2 py-1 bg-muted rounded">PDF</span>
                      <span className="px-2 py-1 bg-muted rounded">arXiv</span>
                      <span className="px-2 py-1 bg-muted rounded">ACL</span>
                      <span className="px-2 py-1 bg-muted rounded">IEEE</span>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleFileSelect}
                      disabled={uploading}
                    >
                      <FolderOpen className="h-4 w-4 mr-2" />
                      Browse
                    </Button>
                    <Button
                      type="button"
                      onClick={() => {
                        // Trigger upload when button is clicked
                        if (fileInputRef.current?.files?.[0]) {
                          const event = {
                            target: fileInputRef.current,
                          } as React.ChangeEvent<HTMLInputElement>;
                          handleFileUpload(event);
                        }
                      }}
                      disabled={uploading}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Upload
                    </Button>
                  </div>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  multiple
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </div>
            </div>

            {/* Paste URL Section */}
            <div className={activeView === "url" ? "block" : "hidden"}>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <div className="flex-1 flex items-center gap-2 px-4 py-2 border rounded-lg bg-background">
                    <LinkIcon className="h-5 w-5 text-muted-foreground" />
                    <Textarea
                      id="paper-url"
                      value={paperUrl}
                      onChange={(e) => setPaperUrl(e.target.value)}
                      placeholder="Paste paper URL (arXiv, ACL, IEEE)"
                      className="min-h-0 border-0 focus-visible:ring-0 resize-none p-0 bg-transparent"
                      rows={1}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="max-papers" className="text-sm text-muted-foreground whitespace-nowrap">
                        Max Papers:
                      </Label>
                      <Input
                        id="max-papers"
                        type="number"
                        min="1"
                        value={maxPapers}
                        onChange={(e) => {
                          setMaxPapers(e.target.value);
                        }}
                        className="w-20 h-10"
                        disabled={uploading}
                      />
                    </div>
                    <Button
                      type="button"
                      onClick={handleUrlImport}
                      disabled={uploading || !paperUrl.trim()}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Import
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
});

AddPapersSection.displayName = "AddPapersSection";

