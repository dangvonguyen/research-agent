import createClient from "openapi-fetch"

import { getApiConfig } from "./config"

import type {
  CrawlerConfig,
  CrawlerConfigCreate,
  CrawlerConfigUpdate,
  CrawlerJob,
  CrawlerJobCreate,
  CrawlerJobUpdate,
  CreateResponse,
  DeleteResponse,
  JobStatus,
  Paper,
  PaperCreate,
  PaperUpdate,
  UpdateResponse,
} from "./models"
import type { paths } from "./openapi.gen"

const config = getApiConfig()
console.log(config.baseUrl)
const client = createClient<paths>({
  baseUrl: config.baseUrl,
  headers: config.defaultHeaders,
})

async function apiCall<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  errorMessage: string,
  options?: { params?: any; body?: any }
): Promise<T> {
  const { data, error } = await (client as any)[method](path, options)
  if (error) throw new Error(`${errorMessage}: ${JSON.stringify(error)}`)
  return data
}

export const apiClient = {
  // Crawler Configs
  crawlerConfigs: {
    list: (skip?: number, limit?: number): Promise<CrawlerConfig[]> =>
      apiCall<CrawlerConfig[]>(
        "GET",
        "/api/v1/crawlers/configs",
        "Failed to fetch crawler configs",
        { params: { query: { skip, limit } } }
      ),

    create: (body: CrawlerConfigCreate): Promise<CreateResponse> =>
      apiCall<CreateResponse>(
        "POST",
        "/api/v1/crawlers/configs",
        "Failed to create crawler config",
        { body }
      ),

    getById: (configId: string): Promise<CrawlerConfig> =>
      apiCall<CrawlerConfig>(
        "GET",
        "/api/v1/crawlers/configs/{config_id}",
        "Failed to fetch crawler config",
        { params: { path: { config_id: configId } } }
      ),

    getByName: (name: string): Promise<CrawlerConfig> =>
      apiCall<CrawlerConfig>(
        "GET",
        "/api/v1/crawlers/configs/name/{name}",
        "Failed to fetch crawler config by name",
        { params: { path: { name } } }
      ),

    update: (
      configId: string,
      body: CrawlerConfigUpdate
    ): Promise<UpdateResponse> =>
      apiCall<UpdateResponse>(
        "PATCH",
        "/api/v1/crawlers/configs/{config_id}",
        "Failed to update crawler config",
        { params: { path: { config_id: configId } }, body }
      ),

    delete: (configId: string): Promise<DeleteResponse> =>
      apiCall<DeleteResponse>(
        "DELETE",
        "/api/v1/crawlers/configs/{config_id}",
        "Failed to delete crawler config",
        { params: { path: { config_id: configId } } }
      ),
  },

  // Crawler Jobs
  crawlerJobs: {
    list: (
      skip?: number,
      limit?: number,
      status?: JobStatus
    ): Promise<CrawlerJob[]> =>
      apiCall<CrawlerJob[]>(
        "GET",
        "/api/v1/crawlers/jobs",
        "Failed to fetch crawler jobs",
        { params: { query: { skip, limit, status } } }
      ),

    create: (body: CrawlerJobCreate): Promise<CreateResponse> =>
      apiCall<CreateResponse>(
        "POST",
        "/api/v1/crawlers/jobs",
        "Failed to create crawler job",
        { body }
      ),

    getById: (jobId: string): Promise<CrawlerJob> =>
      apiCall<CrawlerJob>(
        "GET",
        "/api/v1/crawlers/jobs/{job_id}",
        "Failed to fetch crawler job",
        { params: { path: { job_id: jobId } } }
      ),

    update: (jobId: string, body: CrawlerJobUpdate): Promise<UpdateResponse> =>
      apiCall<UpdateResponse>(
        "PATCH",
        "/api/v1/crawlers/jobs/{job_id}",
        "Failed to update crawler job",
        { params: { path: { job_id: jobId } }, body }
      ),

    delete: (jobId: string): Promise<DeleteResponse> =>
      apiCall<DeleteResponse>(
        "DELETE",
        "/api/v1/crawlers/jobs/{job_id}",
        "Failed to delete crawler job",
        { params: { path: { job_id: jobId } } }
      ),
  },

  // Papers
  papers: {
    list: (
      skip?: number,
      limit?: number,
      status?: JobStatus
    ): Promise<Paper[]> =>
      apiCall<Paper[]>(
        "GET",
        "/api/v1/papers",
        "Failed to fetch papers",
        { params: { query: { skip, limit, status } } }
      ),

    create: (body: PaperCreate): Promise<CreateResponse> =>
      apiCall<CreateResponse>(
        "POST",
        "/api/v1/papers",
        "Failed to create paper",
        { body }
      ),

    getById: (paperId: string): Promise<Paper> =>
      apiCall<Paper>(
        "GET",
        "/api/v1/papers/{paper_id}",
        "Failed to fetch paper",
        { params: { path: { paper_id: paperId } } }
      ),

    update: (paperId: string, body: PaperUpdate): Promise<UpdateResponse> =>
      apiCall<UpdateResponse>(
        "PATCH",
        "/api/v1/papers/{paper_id}",
        "Failed to update paper",
        { params: { path: { paper_id: paperId } }, body }
      ),

    delete: (paperId: string): Promise<DeleteResponse> =>
      apiCall<DeleteResponse>(
        "DELETE",
        "/api/v1/papers/{paper_id}",
        "Failed to delete paper",
        { params: { path: { paper_id: paperId } } }
      ),
  },

  health: {
    check: (): Promise<{ [key: string]: string }> =>
      apiCall<{ [key: string]: string }>(
        "GET",
        "/health",
        "Health check failed"
      ),
  },

  root: {
    get: (): Promise<{ [key: string]: string }> =>
      apiCall<{ [key: string]: string }>(
        "GET",
        "/",
        "Root endpoint failed"
      ),
  },
}

export default apiClient
