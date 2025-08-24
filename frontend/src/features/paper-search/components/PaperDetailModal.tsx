import { Modal } from "@/shared/components"

import type { Paper } from "@/shared/api"

interface PaperDetailModalProps {
  paper: Paper | null
  onClose: () => void
}

export const PaperDetailModal = ({ paper, onClose }: PaperDetailModalProps) => {
  if (!paper) return null

  return (
    <Modal isOpen={!!paper} onClose={onClose}>
      <div className="space-y-4">
        {/* Tiêu đề và tác giả */}
        <div className="text-center mb-4">
          <h2 className="text-2xl font-bold">{paper.title}</h2>
          <p className="text-gray-600 text-sm mt-1">
            {paper.authors?.join(", ")}
          </p>
        </div>

        {/* Năm, nguồn, venue */}
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
          <div className="mt-4">
            <strong>{paper.sections.abstract.title}</strong>
            <div className="text-justify mt-2">
              {paper.sections.abstract.content}
            </div>
          </div>
        )}

        {/* Các section còn lại */}
        {Object.entries(paper.sections ?? {})
          .filter(([key]) => key !== "abstract")
          .map(([key, section]) => (
            <div className="mt-4" key={key}>
              <strong>{section.title}</strong>
              <div className="text-justify mt-2">{section.content}</div>
            </div>
          ))}

        {/* Link PDF */}
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
    </Modal>
  )
}
