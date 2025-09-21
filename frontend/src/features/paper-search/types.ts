import type { PaperSource } from "@/api"

export interface SearchParams {
  query: string | null
  urls: string[] | null
  source: PaperSource
  maxPapers: number | null
}
