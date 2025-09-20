// API Configuration
export const apiConfig = {
  // Base URL for the API - can be overridden via environment variables
  baseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",

  // Default headers
  defaultHeaders: {
    "Content-Type": "application/json",
  },

  // Request timeout in milliseconds
  timeout: 10000,

  // Retry configuration
  retry: {
    attempts: 3,
    delay: 1000,
    backoffFactor: 2,
  },
} as const

// Environment-specific configurations
export const getApiConfig = () => {
  const env = import.meta.env.MODE || "development"

  switch (env) {
    case "production":
      return {
        ...apiConfig,
        baseUrl: "",
      }
    case "staging":
      return {
        ...apiConfig,
        baseUrl:
          import.meta.env.VITE_API_BASE_URL || "https://staging-api.example.com",
      }
    default:
      return apiConfig
  }
}
