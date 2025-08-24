import { useState } from "react"

import type { SearchParams } from "../types"
import type { PaperSource } from "@/shared/api"

interface SearchFormProps {
  onSearch: (params: SearchParams) => void
}

export const SearchForm = ({ onSearch }: SearchFormProps) => {
  const [query, setQuery] = useState("")
  const [url, setUrl] = useState("")
  const [source, setSource] = useState<PaperSource>("acl_anthology")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch({ 
      query: query.trim() || null, 
      url: url.trim() || null, 
      source 
    })
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-6 w-full max-w-md mx-auto"
    >
      {/* Search Query */}
      <div className="flex flex-col gap-2">
        <label htmlFor="query" className="text-base font-medium text-gray-800">
          Search Query:
        </label>
        <input
          id="query"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., Large Language Models"
          className="border border-gray-300 rounded-lg px-4 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Paper URL */}
      <div className="flex flex-col gap-2">
        <label htmlFor="url" className="text-base font-medium text-gray-800">
          Paper URL:
        </label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="e.g., https://aclanthology.org/2023.acl-long.1"
          className="border border-gray-300 rounded-lg px-4 py-3 text-base text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* Source Selector */}
      <div className="flex flex-col gap-2">
        <label htmlFor="source" className="text-base font-medium text-gray-800">
          Source:
        </label>
        <select
          id="source"
          value={source}
          onChange={(e) => setSource(e.target.value as PaperSource)}
          className="border border-gray-300 rounded-lg px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="acl_anthology">ACL Anthology</option>
          <option value="arxiv">arXiv</option>
        </select>
      </div>

      <button
        type="submit"
        className="w-full !bg-blue-600 hover:bg-blue-700 !hover:bg-blue-700 text-white text-base font-semibold py-3 rounded-lg transition-colors border border-gray-300"
      >
        Search
      </button>
    </form>
  )
}
