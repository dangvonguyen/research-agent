import { useState } from "react"
import SearchForm from "../../components/SearchForm/SearchForm"
import SearchResultCard from "../../components/SearchResultCard/SearchResultCard"
import { useSearchPapers } from "@/hooks/useSearchPapers"
import styles from "./SearchPage.module.css"
import type { Paper } from "@/types/paper.types"
import PaperDetailModal from "../../components/PaperDetailModal/PaperDetailModal"

const SearchPage = () => {
  const { search, results, loading } = useSearchPapers()
  const [selectedPaper, setSelectedPaper] = useState<Paper | null>(null)

  return (
    <div className={styles.container}>
      <div className={styles.left}>
        <SearchForm onSearch={search}/>
      </div>
      <div className={styles.right}>
        {loading && <p>Loading...</p>}
        {results.map(paper => (
            <SearchResultCard key={paper.id} {...paper} onClick={() => setSelectedPaper(paper)} />
          ))}
      </div>
    
    <PaperDetailModal paper={selectedPaper} onClose={() => setSelectedPaper(null)} />
    </div>
  )
}
export default SearchPage
