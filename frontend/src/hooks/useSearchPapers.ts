// src/features/paperSearch/hooks/useSearchPapers.ts
import { useState } from "react"
import { searchPapers } from "@/features/paperSearch/api/searchApi"
import type { Paper } from "@/types/paper.types"

export const useSearchPapers = () => {
  const [results, setResults] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)

  const search = async (query: string, url: string, source: string) => {
    setLoading(true)
    try {
      const data = await searchPapers({ query, url, source })
      setResults(data)
    } catch (error) {
      console.error("Search error:", error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  return { results, loading, search }
}
