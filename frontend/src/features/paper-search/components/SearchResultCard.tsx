import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components"

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
      className="cursor-pointer hover:rounded-xl hover:shadow-md hover:-translate-y-0.5 transition-transform"
    >
      <Card className="w-full text-left gap-0 py-4">
        <CardHeader>
          <CardTitle className="leading-snug">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            <strong>Authors:</strong> {authors?.join(", ")}
          </p>
          <p className="text-sm text-gray-600">
            <strong>Abstract:</strong>{" "}
            {truncatedAbstract ? truncatedAbstract : "N/A"}
          </p>
        </CardContent>
      </Card>
    </button>
  )
}