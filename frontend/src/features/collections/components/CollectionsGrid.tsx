import { FileText, MoreVertical } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui";
import type { Collection } from "../types";

interface CollectionsGridProps {
  collections: Collection[];
  onCollectionDeleted?: () => void;
}

export function CollectionsGrid({
  collections,
  onCollectionDeleted,
}: CollectionsGridProps) {
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
        <Card
          key={collection.id}
          className="group border border-border bg-card/80 hover:bg-accent/40 hover:border-primary/70 hover:shadow-md transition-all"
        >
          <CardHeader className="space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3 flex-1">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold uppercase text-primary">
                  {collection.name.slice(0, 2)}
                </div>
                <Button
                  variant="ghost"
                  onClick={() => navigate(`/collections/${collection.id}`)}
                  className="text-left justify-start h-auto p-0 hover:bg-transparent flex flex-col items-start"
                >
                  <CardTitle className="text-foreground text-base font-semibold group-hover:text-primary transition-colors">
                    {collection.name}
                  </CardTitle>
                  {collection.description && (
                    <CardDescription className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                      {collection.description}
                    </CardDescription>
                  )}
                </Button>
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
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <div className="inline-flex items-center gap-2 rounded-full bg-secondary/70 px-2.5 py-1 text-[11px] font-medium text-foreground/90">
                <FileText className="h-3.5 w-3.5 text-primary" />
                <span>{collection.paperCount} papers</span>
              </div>
              <p className="text-[11px]">
                Updated {new Date(collection.lastUpdated).toLocaleDateString()}
              </p>
            </div>
            <Button
              onClick={() => navigate(`/collections/${collection.id}`)}
              className="w-full"
              variant="default"
            >
              Open Collection
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
