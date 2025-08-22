// src/features/paperSearch/pages/SearchPage.tsx
import { useState } from "react"
import SearchForm from "../components/SearchForm"
import SearchResultCard from "../components/SearchResultCard"
import PaperDetailModal from "../components/PaperDetailModal"
import { useSearchPapers } from "../hooks/useSearchPapers"
import type { components } from "@/shared/api/openapi.gen"

type Paper = components["schemas"]["Paper"]

const SearchPage = () => {
  const { search, results, loading } = useSearchPapers()
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)

  return (
    <div className="flex gap-8 p-4">
      <div className="flex-1">
        <SearchForm onSearch={search} />
      </div>

      <div className="basis-2/3 flex flex-col gap-4">
        {loading && <p>Loading...</p>}
        {results.map((paper) => (
          <SearchResultCard
            key={paper.source_id ?? paper._id} // chọn key duy nhất
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

export default SearchPage
