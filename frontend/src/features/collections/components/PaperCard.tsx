import { Trash2 } from "lucide-react";
import { Button, Card, CardContent } from "@/components/ui";
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
      className={`relative cursor-pointer transition-all gap-2 py-2 ${
        isSelected ? "ring-2 ring-primary bg-primary/5" : "hover:bg-accent"
      }`}
    >
      <CardContent className="space-y-2 pr-10 px-4 py-3">
        {/* Title */}
        <h3 className="font-semibold text-foreground line-clamp-2 text-balance">
          {paper.title}
        </h3>

        {/* Authors */}
        <p className="text-sm text-muted-foreground line-clamp-1">
          {paper.authors.join(", ")}
        </p>

        {/* Year and Abstract Preview */}
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground font-medium">
            {paper.year}
          </p>
          <p className="text-sm text-muted-foreground line-clamp-2">
            {paper.abstract}
          </p>
        </div>
      </CardContent>

      {/* Delete Button - Right Center */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2">
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
    </Card>
  );
}
