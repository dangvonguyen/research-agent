import { useState } from "react"

import { searchPapers } from "../api/searchApi"

import type { Paper } from "@/shared/api"



export type SearchParams = {
  query?: string
  url?: string
  source: "acl_anthology" | "arxiv"
}

export const useSearchPapers = () => {
  const [results, setResults] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)

  const search = async ({ query, url, source }: SearchParams) => {
    setLoading(true)
    try {
      // fallback về chuỗi rỗng nếu undefined
      const data = await searchPapers({
        query: query ?? "",
        url: url ?? "",
        source,
      })
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
