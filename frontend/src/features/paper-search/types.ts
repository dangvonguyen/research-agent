import type { PaperSource } from "@/shared/api"

export interface SearchParams {
  query: string | null
  url: string | null
  source: PaperSource
}
