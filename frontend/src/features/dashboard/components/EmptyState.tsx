import { FolderPlus, Upload } from "lucide-react";
import { Button } from "@/components/ui";

interface EmptyStateProps {
  onUploadClick: () => void;
}

export function EmptyState({ onUploadClick }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 space-y-6">
      <div className="flex flex-col items-center space-y-4">
        <div className="p-8 rounded-full bg-muted">
          <FolderPlus className="h-16 w-16 text-muted-foreground" />
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-xl font-semibold">No papers yet</h3>
          <p className="text-muted-foreground max-w-md">
            Get started by uploading a PDF or importing via arXiv/ACL/IEEE URL.
            We'll fetch title, authors, and citation data automatically.
          </p>
        </div>
      </div>
      <Button onClick={onUploadClick} size="lg">
        <Upload className="h-4 w-4 mr-2" />
        Upload Your First Document
      </Button>
    </div>
  );
}


