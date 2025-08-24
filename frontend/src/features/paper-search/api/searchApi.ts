import { mockSearchPapers } from "@/mocks/searchPapers.mock"
import { apiClient } from "@/shared/api"

import type { SearchParams } from "../types"
import type { JobStatus, Paper } from "@/shared/api"

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

export const searchPapers = async ({
  query,
  url,
  source,
}: SearchParams): Promise<Paper[]> => {
  if (USE_MOCK) {
    return mockSearchPapers()
  }

  try {
    // Step 1: Fetch configs
    const configs = await apiClient.crawlerConfigs.list()

    const matchedConfig = configs.find((c) => c.source === source.toLowerCase())
    if (!matchedConfig) {
      throw new Error(`No config found for source: ${source}`)
    }

    // Step 2: Submit crawl job
    const jobRes = await apiClient.crawlerJobs.create({
      config_name: matchedConfig.name,
      query: query || null,
      urls: url ? [url] : null,
    })
    const jobId = jobRes.created_ids[0]

    // Step 3: Poll job status
    let status: JobStatus = "pending"
    let retryCount = 0
    while (status !== "completed" && retryCount < 3) {
      await new Promise((res) => setTimeout(res, 3000))

      const job = await apiClient.crawlerJobs.getById(jobId)
      status = job.status

      if (status === "failed") throw new Error("Crawler job failed")
      retryCount++
    }

    // Step 4: Fetch papers
    const papers = await apiClient.papers.list()

    return papers.filter((p) => p.job_id === jobId)
  } catch (error) {
    console.error("Search failed:", error)
    return []
  }
}
