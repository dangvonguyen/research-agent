import { FileText, MoreVertical } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui";
import type { Collection } from "../types";

interface CollectionsListProps {
  collections: Collection[];
  onCollectionDeleted?: () => void;
}

export function CollectionsList({
  collections,
  onCollectionDeleted,
}: CollectionsListProps) {
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
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="text-left p-4 text-xs font-semibold tracking-wide text-muted-foreground">
                Name
              </th>
              <th className="text-left p-4 text-xs font-semibold tracking-wide text-muted-foreground">
                Description
              </th>
              <th className="text-right p-4 text-xs font-semibold tracking-wide text-muted-foreground">
                Papers
              </th>
              <th className="text-left p-4 text-xs font-semibold tracking-wide text-muted-foreground">
                Last Updated
              </th>
              <th className="text-right p-4 text-xs font-semibold tracking-wide text-muted-foreground">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {collections.map((collection) => (
              <tr
                key={collection.id}
                className="border-t border-border bg-background hover:bg-accent/40 transition-colors"
              >
                <td className="p-4 font-semibold text-foreground">
                  <button
                    onClick={() => navigate(`/collections/${collection.id}`)}
                    className="inline-flex items-center gap-2 text-left hover:text-primary hover:underline"
                  >
                    <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold uppercase text-primary">
                      {collection.name.slice(0, 2)}
                    </span>
                    {collection.name}
                  </button>
                </td>
                <td className="p-4 text-muted-foreground text-xs md:text-sm">
                  <span className="line-clamp-2">{collection.description}</span>
                </td>
                <td className="p-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="inline-flex items-center gap-1 rounded-full bg-secondary/70 px-2.5 py-1 text-[11px] font-medium text-foreground/90">
                      <FileText className="h-3.5 w-3.5 text-primary" />
                      <span>{collection.paperCount} papers</span>
                    </div>
                  </div>
                </td>
                <td className="p-4 text-xs md:text-sm text-muted-foreground">
                  {new Date(collection.lastUpdated).toLocaleDateString()}
                </td>
                <td className="p-4 text-right">
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
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
