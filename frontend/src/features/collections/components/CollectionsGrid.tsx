import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { MoreVertical, FileText } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/DropdownMenu";
import type { Collection } from "../types";

interface CollectionsGridProps {
  collections: Collection[];
  onCollectionDeleted?: () => void;
}

export function CollectionsGrid({ collections, onCollectionDeleted }: CollectionsGridProps) {
  const navigate = useNavigate();

  const handleDelete = async (collectionId: string) => {
    if (!window.confirm("Are you sure you want to delete this collection?")) {
      return;
    }

    try {
      await apiClient.collections.delete(collectionId);
      toast.success("Collection deleted successfully");
      onCollectionDeleted?.();
    } catch (error) {
      console.error("Failed to delete collection:", error);
      toast.error("Failed to delete collection");
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {collections.map((collection) => (
        <Card key={collection.id} className="group hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <button
                  onClick={() => navigate(`/collections/${collection.id}`)}
                  className="text-left"
                >
                  <CardTitle className="text-foreground hover:text-primary transition-colors">
                    {collection.name}
                  </CardTitle>
                </button>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem>Rename</DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={() => handleDelete(collection.id)}
                  >
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <CardDescription className="line-clamp-2">{collection.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span>{collection.paperCount} papers</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Updated {new Date(collection.lastUpdated).toLocaleDateString()}
            </p>
            <Button
              onClick={() => navigate(`/collections/${collection.id}`)}
              className="w-full bg-transparent"
              variant="outline"
            >
              Open Collection
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

