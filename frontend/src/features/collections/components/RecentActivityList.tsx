import { FileText } from "lucide-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { Paper } from "@/api/models";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui";

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return "just now";
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes !== 1 ? "s" : ""} ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours !== 1 ? "s" : ""} ago`;
  }

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) {
    return `${diffInDays} day${diffInDays !== 1 ? "s" : ""} ago`;
  }

  const diffInWeeks = Math.floor(diffInDays / 7);
  if (diffInWeeks < 4) {
    return `${diffInWeeks} week${diffInWeeks !== 1 ? "s" : ""} ago`;
  }

  const diffInMonths = Math.floor(diffInDays / 30);
  if (diffInMonths < 12) {
    return `${diffInMonths} month${diffInMonths !== 1 ? "s" : ""} ago`;
  }

  const diffInYears = Math.floor(diffInDays / 365);
  return `${diffInYears} year${diffInYears !== 1 ? "s" : ""} ago`;
}

interface RecentActivityListProps {
  papers: Paper[];
  isLoading: boolean;
}

export function RecentActivityList({
  papers,
  isLoading,
}: RecentActivityListProps) {
  const navigate = useNavigate();

  // Sort papers by created_at (newest first) and take top 3
  const recentPapers = useMemo(() => {
    return [...papers]
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      )
      .slice(0, 3);
  }, [papers]);

  const handleOpenPaper = () => {
    // Navigate to the papers view
    navigate(`/collections/papers`);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recently Added Papers</CardTitle>
        <CardDescription>Top 3 most recently added papers</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        ) : recentPapers.length > 0 ? (
          <div className="space-y-3">
            {recentPapers.map((paper) => (
              <div
                key={paper.id}
                className="flex items-start justify-between rounded-lg border border-border/90 p-3 hover:bg-secondary transition-colors"
              >
                <div className="flex gap-3 flex-1 min-w-0">
                  <FileText className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-foreground truncate">
                      {paper.title}
                    </p>
                    {paper.authors && paper.authors.length > 0 && (
                      <p className="text-sm text-muted-foreground truncate">
                        {paper.authors.slice(0, 3).join(", ")}
                        {paper.authors.length > 3 ? " et al." : ""}
                      </p>
                    )}
                    {paper.collection_names &&
                      paper.collection_names.length > 0 && (
                        <div className="flex gap-2 mt-1 flex-wrap">
                          {paper.collection_names
                            .slice(0, 2)
                            .map((collectionName: string, idx: number) => (
                              <span
                                key={idx}
                                className="inline-block rounded-full bg-primary/10 px-2 py-1 text-xs text-primary"
                              >
                                {collectionName}
                              </span>
                            ))}
                          {paper.collection_names.length > 2 && (
                            <span className="inline-block rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">
                              +{paper.collection_names.length - 2}
                            </span>
                          )}
                        </div>
                      )}
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTimeAgo(new Date(paper.created_at))}
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleOpenPaper}
                  className="ml-2 shrink-0"
                >
                  Open
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">No papers added yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
