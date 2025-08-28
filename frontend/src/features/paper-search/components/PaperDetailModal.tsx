import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/components"

import type { Paper } from "@/shared/api"

interface PaperDetailModalProps {
  paper: Paper | null
  onClose: () => void
}

export const PaperDetailModal = ({ paper, onClose }: PaperDetailModalProps) => {
  if (!paper) return <></>

  return (
    <Dialog open={!!paper} onOpenChange={onClose}>
      <DialogContent className="max-w-[500px] sm:w-max md:min-w-4/5 lg:min-w-1/2 max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-center text-xl">{paper.title}</DialogTitle>
          <DialogDescription className="text-center">{paper.authors.join(", ")}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <p>
            <strong>Year:</strong> {paper.year ?? "N/A"}
          </p>
          <p>
            <strong>Source:</strong> {paper.source}
          </p>
          <p>
            <strong>Venues:</strong> {paper.venues?.join(", ") || "N/A"}
          </p>
          {/* Abstract */}
          {paper.sections?.abstract && (
            <div>
              <strong>{paper.sections.abstract.title}</strong>
              <div className="text-justify">
                {paper.sections.abstract.content}
              </div>
            </div>
          )}
          {/* Other Sections */}
          {Object.entries(paper.sections ?? {})
            .filter(([key]) => key !== "abstract")
            .map(([key, section]) => (
              <div key={key}>
                <strong>{section.title}</strong>
                <div className="text-justify">{section.content}</div>
              </div>
            ))}
          {/* PDF Link */}
          <div className="mt-6">
            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                📄 View PDF
              </a>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
