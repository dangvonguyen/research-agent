import {
  Calendar,
  Check,
  ExternalLink,
  FileText,
  Link as LinkIcon,
  MapPin,
  Plus,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui";
import type { Collection, Paper } from "../types";

interface PaperDetailSheetProps {
  paper: Paper;
  onClose: () => void;
}

export function PaperDetailSheet({ paper, onClose }: PaperDetailSheetProps) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<string[]>(
    [],
  );
  const [isAddToCollectionOpen, setIsAddToCollectionOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Use collection_names directly from the paper object (provided by backend)
  const paperCollectionNames = paper.collection_names || [];

  // Fetch collections when modal opens
  useEffect(() => {
    if (isAddToCollectionOpen) {
      const fetchCollections = async () => {
        try {
          const data = await apiClient.collections.list();
          const formattedCollections: Collection[] = data.map((c) => ({
            id: c.id,
            name: c.name,
            description: c.description || "",
            paperCount: c.paper_count,
            lastUpdated: c.updated_at,
            paper_count: c.paper_count,
          }));
          setCollections(formattedCollections);
          // Pre-select collections that already contain this paper
          if (paper.collectionIds && paper.collectionIds.length > 0) {
            setSelectedCollectionIds(paper.collectionIds);
          } else {
            setSelectedCollectionIds([]);
          }
        } catch (error) {
          console.error("Failed to fetch collections:", error);
          toast.error("Failed to load collections");
        }
      };
      fetchCollections();
    }
  }, [isAddToCollectionOpen, paper.collectionIds]);

  const handleToggleCollection = (collectionId: string) => {
    setSelectedCollectionIds((prev) =>
      prev.includes(collectionId)
        ? prev.filter((id) => id !== collectionId)
        : [...prev, collectionId],
    );
  };

  const handleAddToCollections = async () => {
    if (selectedCollectionIds.length === 0) {
      toast.error("Please select at least one collection");
      return;
    }

    try {
      setIsLoading(true);
      let successCount = 0;
      let errorCount = 0;

      for (const collectionId of selectedCollectionIds) {
        try {
          // Check if paper is already in collection
          if (paper.collectionIds?.includes(collectionId)) {
            continue; // Skip if already in collection
          }
          await apiClient.collections.addPaper(collectionId, paper.id);
          successCount++;
        } catch (error) {
          console.error(
            `Failed to add paper to collection ${collectionId}:`,
            error,
          );
          errorCount++;
        }
      }

      if (successCount > 0) {
        toast.success(
          `Successfully added paper to ${successCount} collection(s)`,
        );
        setIsAddToCollectionOpen(false);
        // Optionally refresh the paper data or trigger a callback
      }
      if (errorCount > 0) {
        toast.error(`Failed to add paper to ${errorCount} collection(s)`);
      }
    } catch (error) {
      console.error("Failed to add paper to collections:", error);
      toast.error("Failed to add paper to collections");
    } finally {
      setIsLoading(false);
    }
  };

  // Get source display info
  const getSourceInfo = () => {
    if (paper.source_type === "url" && paper.source_url) {
      return {
        label: "URL Source",
        value: paper.source_url,
        icon: LinkIcon,
        color: "bg-muted/50 text-muted-foreground border-border",
      };
    } else if (paper.source_type === "upload" && paper.file_path) {
      return {
        label: "Uploaded File",
        value: "PDF Upload",
        icon: FileText,
        color: "bg-muted/50 text-muted-foreground border-border",
      };
    }
    return null;
  };

  const sourceInfo = getSourceInfo();

  return (
    <>
      {/* Backdrop - closes sheet when clicked, very subtle and only covers the main content area */}
      <div
        className="fixed left-0 right-128 top-0 bottom-0 bg-transparent z-20"
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        className="fixed right-0 top-0 h-screen w-lg border-l border-border bg-card shadow-xl overflow-y-auto z-30"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            onClose();
          }
        }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="paper-details-title"
      >
        {/* Header */}
        <div className="sticky top-0 flex items-center justify-between border-b border-border bg-card px-6 py-4 z-10">
          <h2
            id="paper-details-title"
            className="font-semibold text-foreground"
          >
            Paper Details
          </h2>
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={onClose}
            className="rounded-md p-1 hover:bg-accent"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="space-y-6 p-6">
          {/* Title */}
          <div className="space-y-2">
            <h3 className="font-semibold text-lg text-foreground text-balance leading-tight">
              {paper.title}
            </h3>
          </div>

          {/* Authors */}
          {paper.authors && paper.authors.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">
                Authors
              </p>
              <p className="text-sm text-foreground">
                {paper.authors.join(", ")}
              </p>
            </div>
          )}

          {/* Venue and Year */}
          <div className="flex flex-wrap gap-4">
            {paper.venue && (
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">{paper.venue}</span>
              </div>
            )}
            {paper.year && (
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">{paper.year}</span>
              </div>
            )}
          </div>

          {/* Source - Colored Component */}
          {sourceInfo && (
            <div className={`rounded-lg border p-3 ${sourceInfo.color}`}>
              <div className="flex items-center gap-2 mb-1">
                <sourceInfo.icon className="h-4 w-4" />
                <p className="text-xs font-semibold text-foreground">
                  {sourceInfo.label}
                </p>
              </div>
              {paper.source_url ? (
                <a
                  href={paper.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs hover:underline flex items-center gap-1 truncate"
                >
                  {sourceInfo.value}
                  <ExternalLink className="h-3 w-3 shrink-0" />
                </a>
              ) : (
                <p className="text-xs">{sourceInfo.value}</p>
              )}
            </div>
          )}

          {/* Abstract - Colored Component (if exists) */}
          {paper.abstract && (
            <div className="rounded-lg border bg-muted/50 text-muted-foreground border-border p-3">
              <p className="text-xs font-semibold mb-2 text-foreground">
                Abstract
              </p>
              <p className="text-sm leading-relaxed">{paper.abstract}</p>
            </div>
          )}

          {/* Divider */}
          <div className="border-t border-border" />

          {/* Collections */}
          {paperCollectionNames.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold mb-2 text-foreground">
                Collections
              </p>
              <div className="flex flex-wrap gap-2">
                {paperCollectionNames.map((name) => (
                  <div
                    key={name}
                    className="rounded-md border border-border bg-muted/50 px-3 py-1.5"
                  >
                    <span className="text-sm text-foreground">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {paperCollectionNames.length === 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">
                Collections
              </p>
              <p className="text-sm text-muted-foreground italic">
                No collections
              </p>
            </div>
          )}

          {/* Paper Metadata */}
          <div className="space-y-2">
            <p className="text-xs font-semibold mb-2 text-foreground">
              Paper Metadata
            </p>
            <div className="space-y-1 text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Added:</span>
                <span>{paper.created_at.toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Last Updated:</span>
                <span>{paper.updated_at.toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Source Type:</span>
                <span className="capitalize">{paper.source_type}</span>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="border-t border-border" />

          {/* Actions */}
          <div className="space-y-2">
            <Button
              onClick={() => setIsAddToCollectionOpen(true)}
              className="w-full justify-center gap-2"
              variant="default"
            >
              <Plus className="h-4 w-4" />
              Add to Collection
            </Button>
          </div>
        </div>
      </div>

      {/* Add to Collection Modal */}
      <Dialog
        open={isAddToCollectionOpen}
        onOpenChange={setIsAddToCollectionOpen}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Add to Collection</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Select one or more collections to add this paper to:
            </p>
            <div className="max-h-64 overflow-y-auto space-y-2">
              {collections.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No collections available
                </p>
              ) : (
                collections.map((collection) => {
                  const isSelected = selectedCollectionIds.includes(
                    collection.id,
                  );
                  return (
                    <Button
                      key={collection.id}
                      variant="ghost"
                      className="p-2 w-full"
                      onClick={() => handleToggleCollection(collection.id)}
                      aria-label={`${
                        isSelected ? "Remove from" : "Add to"
                      } collection ${collection.name}`}
                    >
                      <div
                        className={`flex h-5 w-5 items-center justify-center rounded border-2 transition-colors ${
                          isSelected
                            ? "bg-primary border-primary text-primary-foreground"
                            : "border-border bg-background"
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3" />}
                      </div>
                      <div className="flex-1 text-left">
                        <span className="text-sm font-medium block">
                          {collection.name}
                        </span>
                        {collection.description && (
                          <p className="text-xs text-muted-foreground truncate">
                            {collection.description}
                          </p>
                        )}
                      </div>
                    </Button>
                  );
                })
              )}
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button
                variant="outline"
                onClick={() => setIsAddToCollectionOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddToCollections}
                disabled={isLoading || selectedCollectionIds.length === 0}
              >
                {isLoading
                  ? "Adding..."
                  : `Add to ${selectedCollectionIds.length} Collection(s)`}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
