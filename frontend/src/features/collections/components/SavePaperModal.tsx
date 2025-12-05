import { LinkIcon, Search, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import apiClient from "@/api/client";
import type { Collection } from "@/api/models";
import {
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  Textarea,
} from "@/components/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";

interface SavePaperModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SavePaperModal({ isOpen, onClose }: SavePaperModalProps) {
  const { collectionId } = useParams<{ collectionId?: string }>();
  const [activeTab, setActiveTab] = useState("query");
  const [url, setUrl] = useState("");
  const [query, setQuery] = useState("");
  const [maxResult, setMaxResult] = useState(5);
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<string[]>(
    collectionId ? [collectionId] : [],
  );
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [metadata, setMetadata] = useState({
    title: "",
    authors: "",
    abstract: "",
    doi: "",
    year: "",
    keywords: "",
  });

  // Fetch collections when modal opens
  useEffect(() => {
    if (isOpen) {
      const fetchCollections = async () => {
        try {
          const data = await apiClient.collections.list();
          setCollections(data);
          // Set default collection to current collection if available
          if (collectionId && selectedCollectionIds.length === 0) {
            setSelectedCollectionIds([collectionId]);
          }
        } catch (error) {
          console.error("Failed to fetch collections:", error);
          toast.error("Failed to load collections");
        }
      };
      fetchCollections();
    }
  }, [isOpen, collectionId, selectedCollectionIds]);

  const handleGetPapers = async () => {
    // Check if we're in query mode or URL mode
    const isQueryMode = activeTab === "query";

    if (isQueryMode && !query.trim()) {
      toast.error("Please enter a search query");
      return;
    }

    if (!isQueryMode && !url.trim()) {
      toast.error("Please enter a URL");
      return;
    }

    // Collections are optional - allow search without selecting collections
    if (maxResult < 1) {
      toast.error("Max result must be at least 1");
      return;
    }

    try {
      setIsLoading(true);
      // Create crawler job
      const jobResponse = await apiClient.crawlerJobs.create({
        config_name: "default_acl_anthology",
        urls: isQueryMode ? undefined : [url.trim()],
        query: isQueryMode ? query.trim() : undefined,
        max_papers: maxResult,
      });

      toast.success(
        "Crawler job created successfully. Papers will be added to the collection when ready.",
      );

      // Poll for job completion and add papers to collections
      const jobId = jobResponse.created_ids[0];
      const pollJob = async () => {
        try {
          const job = await apiClient.crawlerJobs.getById(jobId);
          if (job.status === "completed") {
            // Get papers created by this specific job
            const jobPapers = await apiClient.papers.getByJobId(jobId);

            if (jobPapers.length === 0) {
              toast.warning("No papers were created by this job");
              setIsLoading(false);
              return;
            }

            // Add papers to selected collections (if any selected)
            if (selectedCollectionIds.length > 0) {
              let totalAdded = 0;
              const errors: string[] = [];

              for (const paper of jobPapers) {
                for (const collectionId of selectedCollectionIds) {
                  try {
                    await apiClient.collections.addPaper(
                      collectionId,
                      paper.id,
                    );
                    totalAdded++;
                  } catch (error) {
                    // Paper might already be in collection, continue
                    const errorMsg =
                      error instanceof Error ? error.message : String(error);
                    if (!errorMsg.includes("already")) {
                      errors.push(
                        `Failed to add paper "${paper.title}" to collection`,
                      );
                    }
                  }
                }
              }

              if (totalAdded > 0) {
                toast.success(
                  `Successfully added ${jobPapers.length} paper(s) to ${selectedCollectionIds.length} collection(s)`,
                );
              } else if (errors.length > 0) {
                toast.warning(
                  "Some papers may already be in the selected collections",
                );
              } else {
                toast.info(
                  "Papers were created but may already be in the collections",
                );
              }
            } else {
              toast.success(
                `Successfully found ${jobPapers.length} paper(s). Papers are available in your library.`,
              );
            }

            onClose();
            // Reset form
            setUrl("");
            setQuery("");
            setMaxResult(5);
            setSelectedCollectionIds(collectionId ? [collectionId] : []);
          } else if (job.status === "failed") {
            toast.error(
              `Crawler job failed: ${job.error_message || "Unknown error"}`,
            );
            setIsLoading(false);
          } else {
            // Job still running, poll again after 2 seconds
            setTimeout(pollJob, 2000);
          }
        } catch (error) {
          console.error("Error polling job:", error);
          toast.error("Failed to check job status");
          setIsLoading(false);
        }
      };

      // Start polling after a short delay
      setTimeout(pollJob, 2000);
    } catch (error) {
      console.error("Failed to create crawler job:", error);
      toast.error("Failed to create crawler job");
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Save Paper</DialogTitle>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="query" className="flex items-center gap-2">
              <Search className="h-4 w-4" />
              Write Query
            </TabsTrigger>
            <TabsTrigger value="url" className="flex items-center gap-2">
              <LinkIcon className="h-4 w-4" />
              Insert URL
            </TabsTrigger>
            <TabsTrigger value="upload" className="flex items-center gap-2">
              <Upload className="h-4 w-4" />
              Upload PDF
            </TabsTrigger>
          </TabsList>

          <TabsContent value="query" className="space-y-4">
            <Textarea
              placeholder="Enter title, keywords, or question to search for papers..."
              className="min-h-24"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground whitespace-nowrap">
                Max Result:
              </label>
              <Input
                type="number"
                min="1"
                value={maxResult}
                onChange={(e) => setMaxResult(parseInt(e.target.value) || 1)}
                className="w-20"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Select Collections (optional, multiple allowed)
              </label>
              <div className="border border-border rounded-md p-3 max-h-48 overflow-y-auto space-y-2">
                {collections.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No collections available
                  </p>
                ) : (
                  collections.map((collection) => (
                    <label
                      key={collection.id}
                      className="flex items-center space-x-2 cursor-pointer hover:bg-secondary p-2 rounded transition-colors"
                    >
                      <input
                        type="checkbox"
                        checked={selectedCollectionIds.includes(collection.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedCollectionIds([
                              ...selectedCollectionIds,
                              collection.id,
                            ]);
                          } else {
                            setSelectedCollectionIds(
                              selectedCollectionIds.filter(
                                (id) => id !== collection.id,
                              ),
                            );
                          }
                        }}
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                      />
                      <span className="text-sm">{collection.name}</span>
                      {collection.description && (
                        <span className="text-xs text-muted-foreground">
                          - {collection.description}
                        </span>
                      )}
                    </label>
                  ))
                )}
              </div>
              {selectedCollectionIds.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {selectedCollectionIds.length} collection
                  {selectedCollectionIds.length !== 1 ? "s" : ""} selected
                </p>
              )}
            </div>
            <Button
              className="w-full"
              onClick={handleGetPapers}
              disabled={isLoading || !query.trim()}
            >
              {isLoading ? "Searching..." : "Search Papers"}
            </Button>
          </TabsContent>

          <TabsContent value="url" className="space-y-4">
            <div className="space-y-3">
              <div className="flex gap-2">
                <Input
                  placeholder="Paste paper URL (arXiv, DOI, etc.)"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="flex-1"
                />
                <div className="flex items-center gap-2">
                  <label className="text-sm text-muted-foreground whitespace-nowrap">
                    Max Result:
                  </label>
                  <Input
                    type="number"
                    min="1"
                    value={maxResult}
                    onChange={(e) =>
                      setMaxResult(parseInt(e.target.value) || 5)
                    }
                    className="w-20"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Select Collections (optional, multiple allowed)
                </label>
                <div className="border border-border rounded-md p-3 max-h-48 overflow-y-auto space-y-2">
                  {collections.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No collections available
                    </p>
                  ) : (
                    collections.map((collection) => (
                      <label
                        key={collection.id}
                        className="flex items-center space-x-2 cursor-pointer hover:bg-secondary p-2 rounded transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCollectionIds.includes(
                            collection.id,
                          )}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedCollectionIds([
                                ...selectedCollectionIds,
                                collection.id,
                              ]);
                            } else {
                              setSelectedCollectionIds(
                                selectedCollectionIds.filter(
                                  (id) => id !== collection.id,
                                ),
                              );
                            }
                          }}
                          className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                        />
                        <span className="text-sm">{collection.name}</span>
                        {collection.description && (
                          <span className="text-xs text-muted-foreground">
                            - {collection.description}
                          </span>
                        )}
                      </label>
                    ))
                  )}
                </div>
                {selectedCollectionIds.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {selectedCollectionIds.length} collection
                    {selectedCollectionIds.length !== 1 ? "s" : ""} selected
                  </p>
                )}
              </div>
              <Button
                onClick={handleGetPapers}
                disabled={isLoading || !url.trim()}
                className="w-full"
              >
                {isLoading ? "Processing..." : "Get Papers"}
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="upload" className="space-y-4">
            <div
              className="rounded-lg border-2 border-dashed border-border p-8 text-center cursor-pointer hover:border-primary/60 hover:bg-accent/40 transition-colors"
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
              <p className="font-medium text-foreground">
                Drag and drop your PDF here
              </p>
              <Input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    setSelectedFile(file);
                  }
                }}
              />
              {selectedFile && (
                <p className="text-sm text-muted-foreground mt-2">
                  {selectedFile.name}
                </p>
              )}
            </div>

            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold">Metadata</h3>
              <div className="grid gap-3">
                <Input
                  placeholder="Title"
                  value={metadata.title}
                  onChange={(e) =>
                    setMetadata({ ...metadata, title: e.target.value })
                  }
                />
                <Input
                  placeholder="Authors"
                  value={metadata.authors}
                  onChange={(e) =>
                    setMetadata({ ...metadata, authors: e.target.value })
                  }
                />
                <Textarea
                  placeholder="Abstract"
                  value={metadata.abstract}
                  onChange={(e) =>
                    setMetadata({ ...metadata, abstract: e.target.value })
                  }
                />
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    placeholder="DOI"
                    value={metadata.doi}
                    onChange={(e) =>
                      setMetadata({ ...metadata, doi: e.target.value })
                    }
                  />
                  <Input
                    placeholder="Year"
                    type="number"
                    value={metadata.year}
                    onChange={(e) =>
                      setMetadata({ ...metadata, year: e.target.value })
                    }
                  />
                </div>
                <Input
                  placeholder="Keywords (comma-separated)"
                  value={metadata.keywords}
                  onChange={(e) =>
                    setMetadata({ ...metadata, keywords: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Select Collections (multiple allowed)
                </label>
                <div className="border border-border rounded-md p-3 max-h-48 overflow-y-auto space-y-2">
                  {collections.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No collections available
                    </p>
                  ) : (
                    collections.map((collection) => (
                      <label
                        key={collection.id}
                        className="flex items-center space-x-2 cursor-pointer hover:bg-secondary p-2 rounded transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={selectedCollectionIds.includes(
                            collection.id,
                          )}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedCollectionIds([
                                ...selectedCollectionIds,
                                collection.id,
                              ]);
                            } else {
                              setSelectedCollectionIds(
                                selectedCollectionIds.filter(
                                  (id) => id !== collection.id,
                                ),
                              );
                            }
                          }}
                          className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
                        />
                        <span className="text-sm">{collection.name}</span>
                        {collection.description && (
                          <span className="text-xs text-muted-foreground">
                            - {collection.description}
                          </span>
                        )}
                      </label>
                    ))
                  )}
                </div>
                {selectedCollectionIds.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {selectedCollectionIds.length} collection
                    {selectedCollectionIds.length !== 1 ? "s" : ""} selected
                  </p>
                )}
              </div>
              <Button
                onClick={async () => {
                  if (!selectedFile) {
                    toast.error("Please select a PDF file");
                    return;
                  }

                  if (selectedCollectionIds.length === 0) {
                    toast.error("Please select at least one collection");
                    return;
                  }

                  try {
                    setIsLoading(true);
                    const response = await apiClient.papers.upload(
                      selectedFile,
                      {
                        title: metadata.title || undefined,
                        authors: metadata.authors || undefined,
                        abstract: metadata.abstract || undefined,
                        doi: metadata.doi || undefined,
                        year: metadata.year
                          ? parseInt(metadata.year)
                          : undefined,
                        keywords: metadata.keywords || undefined,
                      },
                    );

                    // Add paper to selected collections
                    const paperId = response.created_ids[0];
                    let totalAdded = 0;
                    for (const collectionId of selectedCollectionIds) {
                      try {
                        await apiClient.collections.addPaper(
                          collectionId,
                          paperId,
                        );
                        totalAdded++;
                      } catch (error) {
                        console.error(
                          `Failed to add paper to collection ${collectionId}:`,
                          error,
                        );
                      }
                    }

                    if (totalAdded > 0) {
                      toast.success(
                        `Successfully uploaded paper and added to ${totalAdded} collection(s)`,
                      );
                    } else {
                      toast.success("Paper uploaded successfully");
                    }

                    onClose();
                    // Reset form
                    setSelectedFile(null);
                    setMetadata({
                      title: "",
                      authors: "",
                      abstract: "",
                      doi: "",
                      year: "",
                      keywords: "",
                    });
                    setSelectedCollectionIds(
                      collectionId ? [collectionId] : [],
                    );
                    if (fileInputRef.current) {
                      fileInputRef.current.value = "";
                    }
                  } catch (error) {
                    console.error("Failed to upload paper:", error);
                    toast.error("Failed to upload paper");
                  } finally {
                    setIsLoading(false);
                  }
                }}
                disabled={
                  isLoading ||
                  !selectedFile ||
                  selectedCollectionIds.length === 0
                }
                className="w-full"
              >
                {isLoading ? "Uploading..." : "Upload Paper"}
              </Button>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex gap-2 pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            className="flex-1 bg-transparent"
          >
            Cancel
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
