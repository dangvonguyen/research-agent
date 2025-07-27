// src/features/paperSearch/hooks/useSearchPapers.ts
import { useState } from "react"
import { searchPapers } from "@/features/paperSearch/api/searchApi"
import type { Paper } from "@/types/paper.types"

export const useSearchPapers = () => {
  const [results, setResults] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)

  const search = async (query: string, source: string) => {
    setLoading(true)
    const data = await searchPapers(query, source)
    setResults(data)
    setLoading(false)
  }

  return { results, loading, search }
}
