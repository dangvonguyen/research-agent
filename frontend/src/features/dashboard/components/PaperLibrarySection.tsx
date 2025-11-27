import { useState } from "react";
import {
  Grid3x3,
  List,
} from "lucide-react";
import { Button, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Card, CardContent } from "@/components/ui";
import type { Paper } from "@/api";
import { PaperCard } from "./PaperCard";

interface PaperLibrarySectionProps {
  papers: Paper[];
}

type ViewMode = "grid" | "list";
type SortOption = "newest" | "a-z";

export function PaperLibrarySection({ papers }: PaperLibrarySectionProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortOption, setSortOption] = useState<SortOption>("newest");

  const sortedPapers = [...papers].sort((a, b) => {
    if (sortOption === "newest") {
      return (
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    } else {
      return a.title.localeCompare(b.title);
    }
  });

  return (
    <Card className="py-0">
      <CardContent className="p-3 px-3">
        <div className="space-y-4">
          {/* Header with Title and Controls */}
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold">Paper Library</h2>
            
            {/* Controls */}
            <div className="flex items-center gap-3">
              {/* View Toggle */}
              <div className="flex items-center gap-2">
                <Button
                  variant={viewMode === "grid" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("grid")}
                >
                  <Grid3x3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setViewMode("list")}
                >
                  <List className="h-4 w-4" />
                </Button>
              </div>

              {/* Sort */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Sort:</span>
                <Select
                  value={sortOption}
                  onValueChange={(value) => setSortOption(value as SortOption)}
                >
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="newest">Newest</SelectItem>
                    <SelectItem value="a-z">A-Z</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

      {/* Paper Grid/List */}
      {sortedPapers.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          No papers found matching your search.
        </div>
      ) : (
        <div
          className={
            viewMode === "grid"
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
              : "space-y-3"
          }
        >
          {sortedPapers.map((paper) => (
            <PaperCard key={paper._id} paper={paper} />
          ))}
        </div>
        )}
        </div>
      </CardContent>
    </Card>
  );
}


