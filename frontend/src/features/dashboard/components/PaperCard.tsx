import { useState, useRef, useEffect } from "react";
import { FileText, ExternalLink, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui";
import { cn } from "@/lib/utils";
import { apiClient, type JobStatus } from "@/api";
import type { Paper } from "@/api";

interface PaperCardProps {
  paper: Paper;
  onClick?: () => void;
}

export function PaperCard({ paper, onClick }: PaperCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [popupPosition, setPopupPosition] = useState<{
    side: "right" | "left";
    vertical: "top" | "bottom";
  }>({ side: "right", vertical: "top" });
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { title, authors, year, venues, source, sections, url, pdf_url, job_id } = paper;

  const displayAuthors =
    authors && authors.length > 0
      ? authors.length > 1
        ? `${authors[0]} et al.`
        : authors[0]
      : "Unknown authors";

  const displayVenue = venues && venues.length > 0 ? venues[0] : source;
  const abstract = sections?.abstract?.content;
  const allAuthors = authors && authors.length > 0 ? authors.join(", ") : "Unknown authors";

  // Poll job status if paper has a job_id
  useEffect(() => {
    if (!job_id) return;

    const fetchJobStatus = async () => {
      try {
        const job = await apiClient.crawlerJobs.getById(job_id);
        const currentStatus = job.status;
        setJobStatus(currentStatus);

        // Stop polling if job is completed or failed
        if (currentStatus === "completed" || currentStatus === "failed") {
          if (pollingIntervalRef.current) {
            clearInterval(pollingIntervalRef.current);
            pollingIntervalRef.current = null;
          }
          return false; // Indicate we should stop polling
        }
        return true; // Continue polling
      } catch (error) {
        console.error("Failed to fetch job status:", error);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        return false; // Stop polling on error
      }
    };

    // Fetch immediately
    fetchJobStatus();

    // Poll every 3 seconds
    pollingIntervalRef.current = setInterval(async () => {
      const shouldContinue = await fetchJobStatus();
      if (!shouldContinue && pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }, 3000);

    // Cleanup on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [job_id]);

  // Calculate popup position based on available space
  useEffect(() => {
    if (!isHovered || !cardRef.current) return;

    const calculatePosition = () => {
      if (!cardRef.current) return;

      const cardRect = cardRef.current.getBoundingClientRect();
      const popupWidth = 384; // w-96 = 384px
      const popupHeight = popupRef.current?.offsetHeight || 300;
      const gap = 12;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      // Check horizontal space
      const spaceOnRight = viewportWidth - cardRect.right;
      const spaceOnLeft = cardRect.left;
      const side = spaceOnRight >= popupWidth + gap ? "right" : "left";

      // Check vertical space - prefer showing below, but show above if not enough space
      const spaceBelow = viewportHeight - cardRect.bottom;
      const spaceAbove = cardRect.top;
      const vertical =
        spaceBelow >= popupHeight + gap
          ? "top"
          : spaceAbove >= popupHeight + gap
            ? "bottom"
            : "top"; // Default to top if neither has enough space

      setPopupPosition({ side, vertical });
    };

    // Small delay to ensure popup is rendered
    const timeoutId = setTimeout(calculatePosition, 10);
    calculatePosition();

    // Recalculate on window resize
    window.addEventListener("resize", calculatePosition);
    window.addEventListener("scroll", calculatePosition, true);

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener("resize", calculatePosition);
      window.removeEventListener("scroll", calculatePosition, true);
    };
  }, [isHovered]);

  return (
    <div
      ref={cardRef}
      className="relative"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Card
        className="cursor-pointer hover:shadow-md transition-shadow"
        onClick={onClick}
      >
        <CardContent className="p-0.5">
          <div className="flex items-start gap-2">
            <div className="mt-0.5">
              <FileText className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-1">
                <h3 className="font-semibold text-base leading-tight line-clamp-2">
                  {title}
                </h3>
                <div className="flex items-center gap-1 shrink-0">
                  {job_id && jobStatus && (
                    <span
                      className={cn(
                        "px-2 py-0.5 text-xs rounded flex items-center gap-1",
                        jobStatus === "pending" && "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
                        jobStatus === "running" && "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
                        jobStatus === "completed" && "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
                        jobStatus === "failed" && "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      )}
                    >
                      {(jobStatus === "pending" || jobStatus === "running") && (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                      <span className="capitalize">{jobStatus}</span>
                    </span>
                  )}
                  <span className="px-2 py-0.5 text-xs bg-muted rounded">
                    Paper
                  </span>
                </div>
              </div>
              <div className="space-y-0.5 text-sm text-muted-foreground">
                <p className="truncate">{displayAuthors}</p>
                <p className="text-xs">
                  {year && `${year}, `}
                  {displayVenue}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Hover Popup */}
      {isHovered && (
        <div
          ref={popupRef}
          className={cn(
            "absolute z-50 w-96 p-4 bg-popover border rounded-lg shadow-lg",
            "animate-in fade-in-0 zoom-in-95 duration-200"
          )}
          style={{
            ...(popupPosition.side === "right"
              ? { left: "calc(100% + 12px)" }
              : { right: "calc(100% + 12px)" }),
            ...(popupPosition.vertical === "top"
              ? { top: "8px" }
              : { bottom: "8px" }),
          }}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
        >
          <div className="space-y-3">
            {/* Title */}
            <div>
              <h4 className="font-semibold text-base leading-tight mb-2">
                {title}
              </h4>
            </div>

            {/* Authors */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Authors
              </p>
              <p className="text-sm">{allAuthors}</p>
            </div>

            {/* Year & Venue */}
            <div className="flex gap-4 text-sm">
              {year && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Year
                  </p>
                  <p>{year}</p>
                </div>
              )}
              {displayVenue && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">
                    Venue
                  </p>
                  <p>{displayVenue}</p>
                </div>
              )}
            </div>

            {/* Abstract */}
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Abstract
              </p>
              {abstract ? (
                <p className="text-sm text-muted-foreground line-clamp-5 leading-relaxed">
                  {abstract}
                </p>
              ) : (
                <p className="text-sm text-muted-foreground italic">
                  No abstract available
                </p>
              )}
            </div>

            {/* URL Links */}
            <div className="pt-2 border-t space-y-2">
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Links
              </p>
              <div className="flex flex-col gap-2">
                {url ? (
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline flex items-center gap-2 break-all"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-4 w-4 shrink-0" />
                    <span className="truncate">{url}</span>
                  </a>
                ) : (
                  <p className="text-sm text-muted-foreground italic">
                    No URL available
                  </p>
                )}
                {pdf_url && (
                  <a
                    href={pdf_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline flex items-center gap-2 break-all"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-4 w-4 shrink-0" />
                    <span className="truncate">PDF: {pdf_url}</span>
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Arrow pointing to card */}
          <div
            className={cn(
              "absolute w-4 h-4 bg-popover rotate-45",
              popupPosition.side === "right"
                ? "-left-2 border-l border-b"
                : "-right-2 border-r border-t",
              popupPosition.vertical === "top" ? "top-4" : "bottom-4"
            )}
            style={{ borderColor: "inherit" }}
          />
        </div>
      )}
    </div>
  );
}

