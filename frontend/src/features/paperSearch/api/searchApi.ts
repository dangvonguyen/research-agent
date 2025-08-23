// import type { components } from "@/types/openapi"

// type CrawlerConfig = components["schemas"]["CrawlerConfig"]
// type CrawlerJob = components["schemas"]["CrawlerJob"]
// type Paper = components["schemas"]["Paper"]

// interface SearchParams {
//   query: string
//   url: string
//   source: string // e.g., "acl"
// }

// const API_BASE = import.meta.env.VITE_API_BASE_URL

// export const searchPapers = async ({
//   query,
//   url,
//   source,
// }: SearchParams): Promise<Paper[]> => {
//   try {
//     // Step 1: Fetch all crawler configs
//     const configRes = await fetch(`${API_BASE}/v1/crawlers/configs`)
//     const configs: CrawlerConfig[] = await configRes.json()

//     const matchedConfig = configs.find(
//       (c) => c.source === source.toLowerCase()
//     )

//     if (!matchedConfig) {
//       throw new Error(`No config found for source: ${source}`)
//     }

//     const configName = matchedConfig.name

//     // Step 2: Submit crawl job
//     const jobRes = await fetch(`${API_BASE}/v1/crawlers/jobs`, {
//       method: "POST",
//       headers: { "Content-Type": "application/json" },
//       body: JSON.stringify({
//         config_name: configName,
//         query: query || null,
//         urls: url ? [url] : [],
//       }),
//     })

//     if (!jobRes.ok) {
//       throw new Error("Failed to create crawler job")
//     }

//     const jobData: { created_ids: string[] } = await jobRes.json()
//     const jobId = jobData.created_ids[0]

//     // Step 3: Poll job status until completed
//     let status: CrawlerJob["status"] = "pending"
//     let retryCount = 0
//     while (status !== "completed" && retryCount < 20) {
//       await new Promise(res => setTimeout(res, 3000)) // Wait 3s

//       const statusRes = await fetch(`${API_BASE}/v1/crawlers/jobs/${jobId}`)
//       const job: CrawlerJob = await statusRes.json()
//       status = job.status

//       if (status === "failed") throw new Error("Crawler job failed")
//       retryCount++
//     }

//     // Step 4: Fetch papers
//     const paperRes = await fetch(`${API_BASE}/v1/papers`)
//     const papers: Paper[] = await paperRes.json()

//     // Filter papers by job_id
//     const filtered = papers.filter((p) => p.job_id === jobId)
//     return filtered
//   } catch (error) {
//     console.error("Search failed:", error)
//     return []
//   }
// }

// // // src/features/paperSearch/api/searchApi.ts
// // import type { Paper } from "@/types/paper.types"

// // interface SearchParams {
// //   query: string
// //   url: string
// //   source: string
// // }

// // export const searchPapers = async ({
// //   query,
// //   url,
// //   source,
// // }: SearchParams): Promise<Paper[]> => {
// //   // return fetch("http://localhost:8000/api/search", {
// //   //   method: "POST",
// //   //   headers: { "Content-Type": "application/json" },
// //   //   body: JSON.stringify({ query, url, source }),
// //   // }).then(res => res.json());

// //   // Giả lập response:
// //   console.log("Search API called with:", { query, url, source })

// //   return Promise.resolve([
// //     {
// //       id: "paper1",
// //       title: "Exploring Large Language Models",
// //       authors: ["Alice Smith", "Bob Lee"],
// //       year: 2023,
// //       url: "https://example.com/paper1.pdf",
// //       abstract: "This paper explores the capabilities of LLMs...",
// //       introduction: "In this study, we investigate...",
// //       conclusion: "We conclude that LLMs are powerful..."
// //     },
// //     {
// //       id: "paper2",
// //       title: "Neural Networks for NLP",
// //       authors: ["John Doe"],
// //       year: 2022,
// //       url: "https://example.com/paper2.pdf",
// //       abstract: "This paper reviews recent progress in NLP...",
// //       introduction: "The paper begins by discussing...",
// //       conclusion: "Future work includes improving model robustness..."
// //     }
// //   ])
// // }

import { mockSearchPapers } from "@/mocks/searchPapers.mock"

import type { CrawlerConfig, CrawlerJob, Paper } from "@/shared/api"

interface SearchParams {
  query: string
  url: string
  source: string
}

const API_BASE = import.meta.env.VITE_API_BASE_URL
//const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true"
const USE_MOCK = true

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
    const configRes = await fetch(`${API_BASE}/v1/crawlers/configs`)
    const configs: CrawlerConfig[] = await configRes.json()

    const matchedConfig = configs.find((c) => c.source === source.toLowerCase())
    if (!matchedConfig) {
      throw new Error(`No config found for source: ${source}`)
    }

    const configName = matchedConfig.name

    // Step 2: Submit crawl job
    const jobRes = await fetch(`${API_BASE}/v1/crawlers/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        config_name: configName,
        query: query || null,
        urls: url ? [url] : [],
      }),
    })
    if (!jobRes.ok) throw new Error("Failed to create crawler job")

    const jobData: { created_ids: string[] } = await jobRes.json()
    const jobId = jobData.created_ids[0]

    // Step 3: Poll job status
    let status: CrawlerJob["status"] = "pending"
    let retryCount = 0
    while (status !== "completed" && retryCount < 20) {
      await new Promise((res) => setTimeout(res, 3000))

      const statusRes = await fetch(`${API_BASE}/v1/crawlers/jobs/${jobId}`)
      const job: CrawlerJob = await statusRes.json()
      status = job.status

      if (status === "failed") throw new Error("Crawler job failed")
      retryCount++
    }

    // Step 4: Fetch papers
    const paperRes = await fetch(`${API_BASE}/v1/papers`)
    const papers: Paper[] = await paperRes.json()

    return papers.filter((p) => p.job_id === jobId)
  } catch (error) {
    console.error("Search failed:", error)
    return []
  }
}
