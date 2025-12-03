import { useState, useEffect } from "react";
import { X, Download, Plus, Bookmark, ExternalLink, Share2, Calendar, MapPin, FileText } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/api";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { Input } from "@/components/ui/Input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import type { Paper } from "../types";

interface PaperDetailSheetProps {
  paper: Paper;
  onClose: () => void;
}

export function PaperDetailSheet({ paper, onClose }: PaperDetailSheetProps) {
  const [notes, setNotes] = useState("");
  const [newTag, setNewTag] = useState("");
  const [tags, setTags] = useState<string[]>(paper.tags);
  const [isSaving, setIsSaving] = useState(false);

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag)) {
      setTags([...tags, newTag]);
      setNewTag("");
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const [collectionNames, setCollectionNames] = useState<string[]>([]);

  useEffect(() => {
    const fetchCollectionNames = async () => {
      if (paper.collectionIds && paper.collectionIds.length > 0) {
        try {
          const names = await Promise.all(
            paper.collectionIds.map(async (id) => {
              try {
                const collection = await apiClient.collections.getById(id);
                return collection.name;
              } catch {
                return null;
              }
            })
          );
          setCollectionNames(names.filter((n): n is string => n !== null));
        } catch (error) {
          console.error("Failed to fetch collection names:", error);
        }
      } else {
        setCollectionNames([]);
      }
    };

    fetchCollectionNames();
  }, [paper.collectionIds]);

  return (
    <div className="fixed right-0 top-0 h-screen w-96 border-l border-border bg-card shadow-lg overflow-y-auto z-30">
      {/* Header */}
      <div className="sticky top-0 flex items-center justify-between border-b border-border bg-card px-6 py-4 z-10">
        <h2 className="font-semibold text-foreground">Paper Details</h2>
        <button onClick={onClose} className="rounded-md p-1 hover:bg-accent transition-colors">
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="space-y-6 p-6">
          {/* Title and Basic Info */}
          <div className="space-y-3">
            <h3 className="font-semibold text-base text-foreground text-balance leading-tight">{paper.title}</h3>
            <p className="text-xs text-muted-foreground">{paper.authors.join(", ")}</p>

            <div className="space-y-2 pt-2">
              {paper.venue && (
                <div className="flex items-start gap-2">
                  <MapPin className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-muted-foreground">{paper.venue}</p>
                </div>
              )}
              <div className="flex items-start gap-2">
                <Calendar className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                <p className="text-xs text-muted-foreground">{paper.year}</p>
              </div>
              {paper.source_type === "upload" && paper.file_path && (
                <div className="flex items-start gap-2">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-muted-foreground">Uploaded PDF</p>
                </div>
              )}
            </div>
          </div>

          {/* Source Info */}
          <div className="rounded-lg bg-muted/50 p-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">Source</p>
            <div className="space-y-2">
              {paper.source_url && (
                <a
                  href={paper.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline flex items-center gap-1 truncate"
                >
                  {paper.source_type === "url" ? "arxiv.org" : "External Link"}
                  <ExternalLink className="h-3 w-3 flex-shrink-0" />
                </a>
              )}
              {paper.file_path && <p className="text-xs text-muted-foreground">{paper.file_path}</p>}
              <p className="text-xs text-muted-foreground">{paper.parsed ? "Status: Parsed" : "Status: Not Parsed"}</p>
            </div>
          </div>

        {/* Abstract - Always Visible */}
        {paper.abstract && (
          <>
            <div className="border-t border-border" />
            <div className="space-y-2">
              <p className="text-xs font-semibold text-foreground uppercase">Abstract</p>
              <p className="text-sm text-muted-foreground leading-relaxed">{paper.abstract}</p>
            </div>
          </>
        )}

        {/* Divider */}
        <div className="border-t border-border" />

        {/* Tabs */}
        <Tabs defaultValue="metadata" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="metadata">Info</TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
            <TabsTrigger value="tags">Tags</TabsTrigger>
          </TabsList>

          {/* Metadata Tab */}
          <TabsContent value="metadata" className="space-y-4">
            {/* Abstract */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Abstract</p>
              <p className="text-sm text-muted-foreground leading-relaxed">{paper.abstract}</p>
            </div>

            {/* Keywords */}
            {paper.keywords && paper.keywords.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2">Keywords</p>
                <div className="flex flex-wrap gap-2">
                  {paper.keywords.map((keyword) => (
                    <span
                      key={keyword}
                      className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-xs font-medium text-muted-foreground"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Collections */}
            {collectionNames.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2">Collections</p>
                <div className="space-y-1">
                  {collectionNames.map((name) => (
                    <p key={name} className="text-xs text-foreground">
                      • {name}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata Info */}
            <div className="bg-muted/30 rounded p-3 space-y-2">
              <p className="text-xs font-medium text-muted-foreground mb-2">Paper Metadata</p>
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
          </TabsContent>

          {/* Notes Tab */}
          <TabsContent value="notes" className="space-y-3">
            <Textarea
              placeholder="Add your notes here..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="min-h-32 resize-none"
            />
            <p className="text-xs text-muted-foreground">Auto-saves as you type</p>
          </TabsContent>

          {/* Tags Tab */}
          <TabsContent value="tags" className="space-y-3">
            <div className="flex gap-2">
              <Input
                placeholder="Add new tag..."
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => e.key === "Enter" && handleAddTag()}
                className="text-sm"
              />
              <Button size="sm" onClick={handleAddTag} className="gap-1">
                <Plus className="h-3 w-3" />
                Add
              </Button>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Current Tags</p>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <div key={tag} className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1">
                    <span className="text-sm font-medium text-primary">{tag}</span>
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="ml-1 rounded-full hover:bg-primary/20 p-0.5 transition-colors"
                    >
                      <X className="h-3 w-3 text-primary" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>

        {/* Divider */}
        <div className="border-t border-border" />

        {/* Actions */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase">Actions</p>
          <div className="space-y-2">
            {paper.source_url && (
              <a href={paper.source_url} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" className="w-full justify-start gap-2 bg-transparent">
                  <Download className="h-4 w-4" />
                  {paper.source_type === "url" ? "Open Source" : "Download"}
                </Button>
              </a>
            )}
            {paper.file_path && (
              <Button variant="outline" className="w-full justify-start gap-2 bg-transparent">
                <FileText className="h-4 w-4" />
                View PDF
              </Button>
            )}
            <Button variant="outline" className="w-full justify-start gap-2 bg-transparent">
              <Share2 className="h-4 w-4" />
              Share
            </Button>
            <Button variant="outline" className="w-full justify-start gap-2 bg-transparent">
              <Bookmark className="h-4 w-4" />
              Add to Collections
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

