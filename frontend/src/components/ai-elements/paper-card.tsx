import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface Paper {
  title: string;
  url: string;
  reason?: string;
  authors?: string[];
  year?: number;
}

export interface PaperRecommendationsData {
  title?: string;
  message?: string;
  papers: Paper[];
}

interface PaperCardProps {
  data: PaperRecommendationsData;
  onAddToLibrary?: (paper: Paper) => void;
  className?: string;
}

export function PaperCard({ data, onAddToLibrary, className }: PaperCardProps) {
  const { title = "Recommended Papers", message, papers } = data;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {message && <CardDescription>{message}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-4">
        {papers.map((paper, index) => (
          <div
            key={index}
            className="flex flex-col gap-2 rounded-lg border border-border/50 p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 space-y-1">
                <h4 className="font-semibold leading-tight">{paper.title}</h4>
                {(paper.authors || paper.year) && (
                  <p className="text-sm text-muted-foreground">
                    {paper.authors && paper.authors.join(", ")}
                    {paper.year && ` (${paper.year})`}
                  </p>
                )}
                {paper.url && (
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline"
                  >
                    {paper.url}
                  </a>
                )}
              </div>
              {onAddToLibrary && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onAddToLibrary(paper)}
                >
                  Add to Library
                </Button>
              )}
            </div>
            {paper.reason && (
              <p className="text-sm text-muted-foreground">{paper.reason}</p>
            )}
          </div>
        ))}
      </CardContent>
      {papers.length === 0 && (
        <CardFooter>
          <p className="text-sm text-muted-foreground">No papers found.</p>
        </CardFooter>
      )}
    </Card>
  );
}
