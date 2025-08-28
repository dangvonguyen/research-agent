import { Card, CardContent, CardHeader, CardTitle } from "@/shared/components"

import type { Paper } from "@/shared/api"

interface SearchResultCardProps {
  paper: Paper
  onClick?: () => void
}

export const SearchResultCard = ({ paper, onClick }: SearchResultCardProps) => {
  const { title, authors, sections } = paper

  const abstract = sections?.abstract?.content

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
          <p className="text-sm text-gray-600 truncate">
            <strong>Authors:</strong> {authors?.join(", ")}
          </p>
          <p className="text-sm text-gray-600 truncate">
            <strong>Abstract:</strong> {abstract ? abstract : "N/A"}
          </p>
        </CardContent>
      </Card>
    </button>
  )
}
