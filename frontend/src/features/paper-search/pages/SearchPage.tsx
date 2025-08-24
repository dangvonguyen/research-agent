import { useState } from "react"

import { PaperDetailModal, SearchForm, SearchResultCard } from "../components"
import { useSearchPapers } from "../hooks/useSearchPapers"

import type { Paper } from "@/shared/api"

export const SearchPage = () => {
  const { search, results, loading } = useSearchPapers()
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)

  return (
    <div className="flex gap-8 p-4">
      <div className="flex-1">
        <SearchForm onSearch={search} />
      </div>

      <div className="basis-2/3 flex flex-col gap-4">
        {loading && (
          <div className="text-center text-gray-600">Loading...</div>
        )}
        {results.map((paper) => (
          <SearchResultCard
            key={paper.source_id ?? paper._id} // Use unique identifier as key
            paper={paper}
            onClick={() => setSelectedPaper(paper)}
          />
        ))}
      </div>

      <PaperDetailModal
        paper={selectedPaper}
        onClose={() => setSelectedPaper(null)}
      />
    </div>
  )
}
