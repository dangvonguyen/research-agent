import { useState } from "react"

import {
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components"

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
      source,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md mx-auto space-y-4">
      {/* Search Query */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="query">Search Query:</Label>
        <Input
          id="query"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g., Large Language Models"
        />
      </div>

      {/* Paper URL */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="url">Paper URL:</Label>
        <Input
          id="url"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="e.g., https://aclanthology.org/2023.acl-long.1"
        />
      </div>

      {/* Source Selector */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="source">Source:</Label>
        <Select
          value={source}
          onValueChange={(source) => setSource(source as PaperSource)}
        >
          <SelectTrigger id="source" className="w-full">
            <SelectValue placeholder="Select source" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="acl_anthology">ACL Anthology</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button type="submit">Search</Button>
    </form>
  )
}
