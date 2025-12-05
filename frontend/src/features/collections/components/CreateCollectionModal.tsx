import { useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Input,
  Textarea,
} from "@/components/ui";

interface CreateCollectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated?: () => void;
}

export function CreateCollectionModal({
  isOpen,
  onClose,
  onCreated,
}: CreateCollectionModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Collection name is required");
      return;
    }

    try {
      setIsCreating(true);
      await apiClient.collections.create({
        name: name.trim(),
        description: description.trim() || null,
      });
      toast.success("Collection created successfully");
      setName("");
      setDescription("");
      onClose();
      onCreated?.();
    } catch (error) {
      console.error("Failed to create collection:", error);
      toast.error("Failed to create collection");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Collection</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="collection-name"
              className="text-sm font-medium text-foreground"
            >
              Collection Name
            </label>
            <Input
              id="collection-name"
              placeholder="e.g., Natural Language Processing"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="collection-description"
              className="text-sm font-medium text-foreground"
            >
              Description (optional)
            </label>
            <Textarea
              id="collection-description"
              placeholder="Add a description for this collection..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="min-h-20 resize-none"
            />
          </div>
        </div>

        <div className="flex gap-2 pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            className="flex-1 bg-transparent"
            disabled={isCreating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            className="flex-1"
            disabled={isCreating}
          >
            {isCreating ? "Creating..." : "Create Collection"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
