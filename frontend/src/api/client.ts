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
const client = createClient<paths>({
  baseUrl: config.baseUrl,
  headers: config.defaultHeaders,
})

async function apiCall<
  Path extends keyof paths,
  Method extends Exclude<keyof paths[Path] & string, "parameters">
>(
  path: Path,
  method: Uppercase<Method>,
  errorMessage: string,
  options?: {
    params?: Record<string, unknown>
    body?: Record<string, unknown>
  }
) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data, error } = await (client as any)[method](path, options)
  if (error) throw new Error(`${errorMessage}: ${JSON.stringify(error)}`)
  return data
}

export const apiClient = {
  // Crawler Configs
  crawlerConfigs: {
    list: (skip?: number, limit?: number): Promise<CrawlerConfig[]> =>
      apiCall(
        "/api/v1/crawlers/configs",
        "GET",
        "Failed to fetch crawler configs",
        { params: { query: { skip, limit } } }
      ),

    create: (body: CrawlerConfigCreate): Promise<CreateResponse> =>
      apiCall(
        "/api/v1/crawlers/configs",
        "POST",
        "Failed to create crawler config",
        { body }
      ),

    getById: (configId: string): Promise<CrawlerConfig> =>
      apiCall(
        "/api/v1/crawlers/configs/{config_id}",
        "GET",
        "Failed to fetch crawler config",
        { params: { path: { config_id: configId } } }
      ),

    getByName: (name: string): Promise<CrawlerConfig> =>
      apiCall(
        "/api/v1/crawlers/configs/name/{name}",
        "GET",
        "Failed to fetch crawler config by name",
        { params: { path: { name } } }
      ),

    update: (
      configId: string,
      body: CrawlerConfigUpdate
    ): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/crawlers/configs/{config_id}",
        "PATCH",
        "Failed to update crawler config",
        { params: { path: { config_id: configId } }, body }
      ),

    delete: (configId: string): Promise<DeleteResponse> =>
      apiCall(
        "/api/v1/crawlers/configs/{config_id}",
        "DELETE",
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
      apiCall(
        "/api/v1/crawlers/jobs",
        "GET",
        "Failed to fetch crawler jobs",
        { params: { query: { skip, limit, status } } }
      ),

    create: (body: CrawlerJobCreate): Promise<CreateResponse> =>
      apiCall(
        "/api/v1/crawlers/jobs",
        "POST",
        "Failed to create crawler job",
        { body }
      ),

    getById: (jobId: string): Promise<CrawlerJob> =>
      apiCall(
        "/api/v1/crawlers/jobs/{job_id}",
        "GET",
        "Failed to fetch crawler job",
        { params: { path: { job_id: jobId } } }
      ),

    update: (jobId: string, body: CrawlerJobUpdate): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/crawlers/jobs/{job_id}",
        "PATCH",
        "Failed to update crawler job",
        { params: { path: { job_id: jobId } }, body }
      ),

    delete: (jobId: string): Promise<DeleteResponse> =>
      apiCall(
        "/api/v1/crawlers/jobs/{job_id}",
        "DELETE",
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
      apiCall(
        "/api/v1/papers",
        "GET",
        "Failed to fetch papers",
        { params: { query: { skip, limit, status } } }
      ),

    create: (body: PaperCreate): Promise<CreateResponse> =>
      apiCall("/api/v1/papers", "POST", "Failed to create paper", { body }),

    getById: (paperId: string): Promise<Paper> =>
      apiCall(
        "/api/v1/papers/{paper_id}",
        "GET",
        "Failed to fetch paper",
        { params: { path: { paper_id: paperId } } }
      ),

    update: (paperId: string, body: PaperUpdate): Promise<UpdateResponse> =>
      apiCall(
        "/api/v1/papers/{paper_id}",
        "PATCH",
        "Failed to update paper",
        { params: { path: { paper_id: paperId } }, body }
      ),

    delete: (paperId: string): Promise<DeleteResponse> =>
      apiCall(
        "/api/v1/papers/{paper_id}",
        "DELETE",
        "Failed to delete paper",
        { params: { path: { paper_id: paperId } } }
      ),
  },

  health: {
    check: (): Promise<{ [key: string]: string }> =>
      apiCall("/health", "GET", "Health check failed"),
  },

  root: {
    get: (): Promise<{ [key: string]: string }> =>
      apiCall("/", "GET", "Root endpoint failed"),
  },
}

export default apiClient
