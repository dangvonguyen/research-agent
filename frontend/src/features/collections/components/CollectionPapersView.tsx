import { ArrowUpDown, Filter, Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { apiClient } from "@/api";
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  Input,
} from "@/components/ui";
import type { Paper } from "../types";
import { PaperCard } from "./PaperCard";
import { PaperDetailSheet } from "./PaperDetailSheet";
import { TopSearchBar } from "./TopSearchBar";

interface CollectionPapersViewProps {
  collectionId: string | null;
}

export function CollectionPapersView({
  collectionId,
}: CollectionPapersViewProps) {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "a-z">("newest");
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [filterYear, setFilterYear] = useState<number | null>(null);
  const [papers, setPapers] = useState<Paper[]>([]);
  const [collectionName, setCollectionName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetchingRef = useRef(false);
  // Use a sentinel value to distinguish "never fetched" from "fetched with null"
  const currentCollectionIdRef = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    // Only fetch if collectionId actually changed
    if (currentCollectionIdRef.current === collectionId) {
      console.log("Skipping fetch - collectionId unchanged:", collectionId);
      return;
    }

    // Prevent concurrent fetches
    if (fetchingRef.current) {
      console.log("Skipping fetch - already fetching");
      return;
    }

    console.log("Starting fetch for collectionId:", collectionId);
    fetchingRef.current = true;

    let isMounted = true;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        if (collectionId && collectionId !== "") {
          // Fetch collection details
          console.log("Step 1: Fetching collection details for:", collectionId);
          const collection = await apiClient.collections.getById(collectionId);
          console.log("Step 1: Collection received:", collection);
          if (!isMounted) {
            console.log("Component unmounted after getById");
            return;
          }
          setCollectionName(collection.name);

          // Fetch papers in collection
          console.log("Step 2: Fetching papers for collection:", collectionId);
          const papersData = await apiClient.collections.getPapers(
            collectionId
          );
          console.log(
            "Step 2: Papers received:",
            papersData?.length || 0,
            "papers"
          );
          if (!isMounted) {
            console.log("Component unmounted after getPapers");
            return;
          }
          const formattedPapers: Paper[] = papersData.map((p) => ({
            id: p.id,
            title: p.title,
            authors: p.authors || [],
            year: p.year ?? null,
            venue: p.venue || undefined,
            abstract: p.abstract || "",
            source_type: p.source_type as "upload" | "url",
            source_url: p.source_url || null,
            file_path: p.file_path || null,
            parsed: p.parsed,
            created_at: new Date(p.created_at),
            updated_at: new Date(p.updated_at),
            keywords: [],
            tags: [],
            collectionIds: p.collection_ids || [collectionId],
            collection_names: p.collection_names || [],
          }));
          setPapers(formattedPapers);
        } else {
          // Fetch all papers
          console.log("Step 1: Fetching all papers (no collection filter)");
          const papersData = await apiClient.papers.list();
          console.log(
            "Step 1: All papers received:",
            papersData?.length || 0,
            "papers"
          );
          if (!isMounted) return;
          const formattedPapers: Paper[] = papersData.map((p) => ({
            id: p.id,
            title: p.title,
            authors: p.authors || [],
            year: p.year ?? null,
            venue: p.venue || undefined,
            abstract: p.abstract || "",
            source_type: p.source_type as "upload" | "url",
            source_url: p.source_url || null,
            file_path: p.file_path || null,
            parsed: p.parsed,
            created_at: new Date(p.created_at),
            updated_at: new Date(p.updated_at),
            keywords: [],
            tags: [],
            collectionIds: p.collection_ids || [],
            collection_names: p.collection_names || [],
          }));
          setPapers(formattedPapers);
        }
        // Mark this collectionId as fetched only after successful completion
        currentCollectionIdRef.current = collectionId;
        console.log(
          "Successfully fetched papers for collectionId:",
          collectionId
        );
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to fetch papers:", error);
        toast.error("Failed to load papers");
        // Reset ref on error to allow retry
        currentCollectionIdRef.current = undefined;
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
        fetchingRef.current = false;
      }
    };

    fetchData();

    // Cleanup function
    return () => {
      isMounted = false;
      fetchingRef.current = false;
    };
  }, [collectionId]);

  // Filter papers
  const filteredPapers = papers.filter((paper) => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return (
        paper.title.toLowerCase().includes(term) ||
        paper.authors.some((a) => a.toLowerCase().includes(term)) ||
        paper.keywords?.some((k) => k.toLowerCase().includes(term)) ||
        false
      );
    }
    if (filterYear && paper.year !== filterYear) {
      return false;
    }
    return true;
  });

  // Sort papers
  const sortedPapers = [...filteredPapers].sort((a, b) => {
    if (sortBy === "newest") {
      // Sort by created_at (newest first - time paper was added)
      return b.created_at.getTime() - a.created_at.getTime();
    }
    if (sortBy === "oldest") {
      // Sort by created_at (oldest first)
      return a.created_at.getTime() - b.created_at.getTime();
    }
    // Sort alphabetically by title
    return a.title.localeCompare(b.title);
  });

  const selectedPaper = papers.find((p) => p.id === selectedPaperId);

  return (
    <div className="flex flex-col h-screen gap-0 bg-background">
      <TopSearchBar />
      <div className="flex flex-1 overflow-hidden">
        {/* Main Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Header */}
          <div className="border-b border-border bg-card px-6 py-4">
            <div className="mb-4">
              <h1 className="text-2xl font-bold text-foreground">Papers</h1>
              {collectionName && (
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-sm text-muted-foreground">
                    Filtered by collection:
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1">
                    <span className="text-sm font-medium text-primary">
                      {collectionName}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => navigate("/collections")}
                      className="ml-1 hover:bg-primary/20 rounded p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </span>
                </div>
              )}
            </div>

            {/* Search and Filters */}
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search papers within this collection..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 pr-10"
                />
                {searchTerm && (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setSearchTerm("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 hover:bg-muted rounded p-1"
                    aria-label="Clear search"
                  >
                    <X className="h-4 w-4 text-muted-foreground" />
                  </Button>
                )}
              </div>

              <div className="flex gap-2">
                {/* Filter Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      <Filter className="h-4 w-4" />
                      Filter
                      {filterYear && (
                        <span className="ml-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">
                          1
                        </span>
                      )}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <div className="px-2 py-1.5 text-sm font-semibold">
                      Filter by Year
                    </div>
                    {[2024, 2023, 2022, 2021, 2020].map((year) => (
                      <DropdownMenuItem
                        key={year}
                        onClick={() =>
                          setFilterYear(filterYear === year ? null : year)
                        }
                        className={filterYear === year ? "bg-accent" : ""}
                      >
                        {year}
                      </DropdownMenuItem>
                    ))}
                    {filterYear && (
                      <>
                        <div className="border-t border-border my-1" />
                        <DropdownMenuItem
                          onClick={() => setFilterYear(null)}
                          className="text-muted-foreground"
                        >
                          Clear Year Filter
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>

                {/* Sort Dropdown */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-2 bg-transparent"
                    >
                      <ArrowUpDown className="h-4 w-4" />
                      Sort
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-40">
                    <DropdownMenuItem
                      onClick={() => setSortBy("newest")}
                      className={sortBy === "newest" ? "bg-accent" : ""}
                    >
                      Newest
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setSortBy("oldest")}
                      className={sortBy === "oldest" ? "bg-accent" : ""}
                    >
                      Oldest
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => setSortBy("a-z")}
                      className={sortBy === "a-z" ? "bg-accent" : ""}
                    >
                      A–Z
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                {sortedPapers.length} paper
                {sortedPapers.length !== 1 ? "s" : ""} found
              </div>
              {(searchTerm || filterYear) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearchTerm("");
                    setFilterYear(null);
                  }}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
                >
                  <X className="h-4 w-4" />
                  Clear all filters
                </Button>
              )}
            </div>
          </div>

          {/* Papers List */}
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-3 p-6">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <p className="text-muted-foreground">Loading papers...</p>
                </div>
              ) : sortedPapers.length > 0 ? (
                sortedPapers.map((paper) => (
                  <PaperCard
                    key={paper.id}
                    paper={paper}
                    isSelected={selectedPaperId === paper.id}
                    onSelect={() => setSelectedPaperId(paper.id)}
                  />
                ))
              ) : (
                <div className="flex items-center justify-center rounded-lg border border-dashed border-border bg-muted/50 py-12">
                  <div className="text-center">
                    <p className="text-muted-foreground">No papers found</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Paper Detail Sheet */}
        {selectedPaper && (
          <PaperDetailSheet
            paper={selectedPaper}
            onClose={() => setSelectedPaperId(null)}
          />
        )}
      </div>
    </div>
  );
}
