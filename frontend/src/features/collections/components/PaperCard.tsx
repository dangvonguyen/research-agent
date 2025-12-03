import { Trash2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import type { Paper } from "../types";

interface PaperCardProps {
  paper: Paper;
  isSelected: boolean;
  onSelect: () => void;
}

export function PaperCard({ paper, isSelected, onSelect }: PaperCardProps) {
  return (
    <Card
      onClick={onSelect}
      className={`cursor-pointer transition-all p-4 ${
        isSelected ? "ring-2 ring-primary bg-primary/5" : "hover:shadow-md hover:bg-accent/50"
      }`}
    >
      <div className="space-y-3">
        {/* Title */}
        <h3 className="font-semibold text-foreground line-clamp-2 text-balance">{paper.title}</h3>

        {/* Authors */}
        <p className="text-sm text-muted-foreground line-clamp-1">{paper.authors.join(", ")}</p>

        {/* Year and Abstract Preview */}
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground font-medium">{paper.year}</p>
          <p className="text-sm text-muted-foreground line-clamp-2">{paper.abstract}</p>
        </div>

        {/* Keywords and Tags */}
        {paper.keywords && paper.keywords.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {paper.keywords.map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-xs font-medium text-muted-foreground"
              >
                {keyword}
              </span>
            ))}
          </div>
        )}

        {/* DOI and Actions */}
        <div className="flex items-center justify-between pt-2">
          {paper.source_url && (
            <a
              href={paper.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary hover:underline truncate"
              onClick={(e) => e.stopPropagation()}
            >
              {paper.source_url}
            </a>
          )}
          <div className="flex gap-2">
            {paper.source_url && (
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(paper.source_url || "", "_blank");
                }}
              >
                <ExternalLink className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                // Handle remove
              }}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}

