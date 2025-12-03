import { Button } from "@/components/ui/Button";
import { MoreVertical, FileText } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/DropdownMenu";
import type { Collection } from "../types";

interface CollectionsListProps {
  collections: Collection[];
  onCollectionDeleted?: () => void;
}

export function CollectionsList({ collections, onCollectionDeleted }: CollectionsListProps) {
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
        <table className="w-full">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium">Name</th>
              <th className="text-left p-4 font-medium">Description</th>
              <th className="text-right p-4 font-medium">Papers</th>
              <th className="text-left p-4 font-medium">Last Updated</th>
              <th className="text-right p-4 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {collections.map((collection) => (
              <tr
                key={collection.id}
                className="border-t border-border hover:bg-secondary transition-colors"
              >
                <td className="p-4 font-medium">
                  <button
                    onClick={() => navigate(`/collections/${collection.id}`)}
                    className="text-primary hover:underline"
                  >
                    {collection.name}
                  </button>
                </td>
                <td className="p-4 text-muted-foreground text-sm">{collection.description}</td>
                <td className="p-4 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    {collection.paperCount}
                  </div>
                </td>
                <td className="p-4 text-sm text-muted-foreground">
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

