import { useState } from "react";
import { Upload, LinkIcon, Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/Dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";

interface SavePaperModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SavePaperModal({ isOpen, onClose }: SavePaperModalProps) {
  const [activeTab, setActiveTab] = useState("query");
  const [metadata, setMetadata] = useState({
    title: "",
    authors: "",
    abstract: "",
    doi: "",
    year: "",
    keywords: "",
  });

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
            <Textarea placeholder="Enter title, keywords, or question to search for papers..." className="min-h-24" />
            <Button className="w-full">Search Papers</Button>
          </TabsContent>

          <TabsContent value="url" className="space-y-4">
            <div className="space-y-3">
              <Input placeholder="Paste paper URL (arXiv, DOI, etc.)" />
              <Button variant="outline" className="w-full bg-transparent">
                Fetch Metadata
              </Button>
            </div>
          </TabsContent>

          <TabsContent value="upload" className="space-y-4">
            <div className="rounded-lg border-2 border-dashed border-border p-8 text-center">
              <Upload className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
              <p className="font-medium text-foreground">Drag and drop your PDF here</p>
              <p className="text-sm text-muted-foreground">or click to browse</p>
              <Input type="file" accept=".pdf" className="mt-4" />
            </div>

            <div className="space-y-4 border-t pt-4">
              <h3 className="font-semibold">Metadata</h3>
              <div className="grid gap-3">
                <Input
                  placeholder="Title"
                  value={metadata.title}
                  onChange={(e) => setMetadata({ ...metadata, title: e.target.value })}
                />
                <Input
                  placeholder="Authors"
                  value={metadata.authors}
                  onChange={(e) => setMetadata({ ...metadata, authors: e.target.value })}
                />
                <Textarea
                  placeholder="Abstract"
                  value={metadata.abstract}
                  onChange={(e) => setMetadata({ ...metadata, abstract: e.target.value })}
                />
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    placeholder="DOI"
                    value={metadata.doi}
                    onChange={(e) => setMetadata({ ...metadata, doi: e.target.value })}
                  />
                  <Input
                    placeholder="Year"
                    type="number"
                    value={metadata.year}
                    onChange={(e) => setMetadata({ ...metadata, year: e.target.value })}
                  />
                </div>
                <Input
                  placeholder="Keywords (comma-separated)"
                  value={metadata.keywords}
                  onChange={(e) => setMetadata({ ...metadata, keywords: e.target.value })}
                />
              </div>
            </div>
          </TabsContent>
        </Tabs>

        <div className="flex gap-2 pt-4">
          <Button variant="outline" onClick={onClose} className="flex-1 bg-transparent">
            Cancel
          </Button>
          <Button onClick={onClose} className="flex-1">
            Save to Collections
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

