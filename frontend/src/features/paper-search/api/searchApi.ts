import { mockSearchPapers } from "@/mocks/searchPapers.mock"
import { apiClient } from "@/shared/api"

import type { SearchParams } from "../types"
import type { JobStatus, Paper } from "@/shared/api"

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"

export const searchPapers = async ({
  query,
  urls,
  source,
  maxPapers,
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
      query: query,
      urls: urls,
      max_papers: maxPapers,
    })
    const jobId = jobRes.created_ids[0]

    // Step 3: Poll job status
    let status: JobStatus = "pending"
    let retryCount = 0
    const TIMEOUT = 3000 // 3 seconds
    const MAX_RETRIES = 40 // Allow up to 3 seconds * 40 = 2 minutes of polling

    while (status !== "completed" && retryCount < MAX_RETRIES) {
      await new Promise((res) => setTimeout(res, TIMEOUT))

      const job = await apiClient.crawlerJobs.getById(jobId)
      status = job.status

      if (status === "failed") throw new Error("Crawler job failed")
      retryCount++
    }

    if (status !== "completed") {
      const error_msg = "Job timed out - paper retrieval took too long"
      alert(error_msg)
      throw new Error(error_msg)
    }

    // Step 4: Fetch papers
    const papers = await apiClient.papers.list()

    return papers.filter((p) => p.job_id === jobId)
  } catch (error) {
    console.error("Search failed:", error)
    return []
  }
}
