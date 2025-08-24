import type { Paper } from "@/shared/api"

interface SearchResultCardProps {
  paper: Paper
  onClick?: () => void
}

const ABSTRACT_PREVIEW_WORDS = 15

export const SearchResultCard = ({ paper, onClick }: SearchResultCardProps) => {
  const { title, authors, sections } = paper

  const abstract = sections?.abstract?.content

  // Truncate abstract to show preview of first few words
  const truncatedAbstract = abstract
    ? abstract.split(/\s+/).slice(0, ABSTRACT_PREVIEW_WORDS).join(" ") + "..."
    : null

  return (
    <button
      onClick={onClick}
      className="bg-white border-none text-left w-full p-4 cursor-pointer rounded-lg shadow-md hover:shadow-lg hover:-translate-y-1 transition-transform"
    >
      <h3 className="text-lg mb-2">{title}</h3>

      <p className="text-sm text-gray-600 mb-1">
        <strong>Authors:</strong> {authors?.join(", ")}
      </p>

      {truncatedAbstract && (
        <p className="text-sm text-gray-600">
          <strong>Abstract:</strong> {truncatedAbstract}
        </p>
      )}
    </button>
  )
}
