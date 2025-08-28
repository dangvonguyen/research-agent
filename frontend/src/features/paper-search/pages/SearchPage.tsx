import { useState } from "react"

import { PaperDetailModal, SearchForm, SearchResultCard } from "../components"
import { useSearchPapers } from "../hooks/useSearchPapers"

import type { Paper } from "@/shared/api"

export function SearchPage() {
  const { search, results, loading } = useSearchPapers()
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)

  return (
    <div className="flex gap-8 p-4">
      <SearchForm onSearch={search} />

      <div className="flex flex-col w-1/2 gap-2">
        {loading ? (
          <div className="text-center text-gray-600">Loading...</div>
        ) : (
          results.map((paper) => (
            <SearchResultCard
              key={paper._id}
              paper={paper}
              onClick={() => setSelectedPaper(paper)}
            />
          ))
        )}
      </div>

      <PaperDetailModal
        paper={selectedPaper}
        onClose={() => setSelectedPaper(null)}
      />
    </div>
  )
}
