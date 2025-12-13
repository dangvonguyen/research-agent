import { LayoutGrid, List, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  Button,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui";
import type { Collection } from "../types";
import { CollectionsGrid } from "./CollectionsGrid";
import { CollectionsList } from "./CollectionsList";
import { CollectionsNavBar } from "./CollectionsNavBar";
import { CreateCollectionModal } from "./CreateCollectionModal";

export function CollectionsPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [sortBy, setSortBy] = useState("recently-updated");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const fetchingRef = useRef(false);

  useEffect(() => {
    // Prevent concurrent fetches (e.g., from StrictMode double-mount)
    if (fetchingRef.current) {
      return;
    }
    fetchingRef.current = true;

    let isMounted = true;

    const fetchCollections = async () => {
      try {
        setIsLoading(true);
        const data = await apiClient.collections.list();
        if (!isMounted) return;
        const formattedCollections: Collection[] = data.map((c) => ({
          id: c.id,
          name: c.name,
          description: c.description || "",
          paperCount: c.paper_count,
          lastUpdated: c.updated_at,
          paper_count: c.paper_count,
        }));
        setCollections(formattedCollections);
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to fetch collections:", error);
        toast.error("Failed to load collections");
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
        fetchingRef.current = false;
      }
    };

    fetchCollections();

    return () => {
      isMounted = false;
      fetchingRef.current = false;
    };
  }, []);

  const handleCollectionCreated = () => {
    // Refresh collections after creation
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
      } catch (error) {
        console.error("Failed to fetch collections:", error);
      }
    };
    fetchCollections();
  };

  return (
    <div className="flex flex-col h-screen">
      <CollectionsNavBar />
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">
                Collections
              </h1>
              <p className="text-muted-foreground">
                Organize your papers into categories
              </p>
            </div>
            <Button
              onClick={() => setIsCreateModalOpen(true)}
              className="gap-2"
            >
              <Plus className="h-4 w-4" />
              Create Collection
            </Button>
          </div>

          {/* Filters & Controls Row */}
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex gap-2">
              <Button
                variant={viewMode === "grid" ? "default" : "secondary"}
                size="icon"
                onClick={() => setViewMode("grid")}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "list" ? "default" : "secondary"}
                size="icon"
                onClick={() => setViewMode("list")}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>

            <div className="w-full md:w-48">
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger>
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="a-z">A–Z</SelectItem>
                  <SelectItem value="z-a">Z–A</SelectItem>
                  <SelectItem value="most-papers">Most Papers</SelectItem>
                  <SelectItem value="recently-updated">
                    Recently Updated
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Collections View */}
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <p className="text-muted-foreground">Loading collections...</p>
            </div>
          ) : collections.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <p className="text-muted-foreground">
                No collections yet. Create your first collection!
              </p>
            </div>
          ) : viewMode === "grid" ? (
            <CollectionsGrid
              collections={collections}
              onCollectionDeleted={handleCollectionCreated}
            />
          ) : (
            <CollectionsList
              collections={collections}
              onCollectionDeleted={handleCollectionCreated}
            />
          )}

          {/* Create Collection Modal */}
          <CreateCollectionModal
            isOpen={isCreateModalOpen}
            onClose={() => setIsCreateModalOpen(false)}
            onCreated={handleCollectionCreated}
          />
        </div>
      </div>
    </div>
  );
}
