import {
  Button,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Textarea,
} from "@/shared/components"

import type { SearchParams } from "../types"
import type { PaperSource } from "@/shared/api"

interface SearchFormProps {
  onSearch: (params: SearchParams) => void
}

export const SearchForm = ({ onSearch }: SearchFormProps) => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget as HTMLFormElement)
    const values = Object.fromEntries(formData.entries())

    const urlsText = String(values.urls).trim()
    const urls = urlsText
      ? urlsText
          .split("\n")
          .map((url) => url.trim())
          .filter((url) => url.length > 0)
      : null

    onSearch({
      query: String(values.query).trim() || null,
      urls,
      source: values.source as PaperSource,
      maxPapers: values.maxPapers ? Number(values.maxPapers) : null,
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
          name="query"
          placeholder="e.g., Large Language Models"
        />
      </div>

      {/* Paper URLs */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="urls">Paper URLs (one per line):</Label>
        <Textarea
          id="urls"
          name="urls"
          placeholder="e.g., https://aclanthology.org/2023.acl-long.1"
          rows={1}
          className="min-h-0 max-h-32"
        />
      </div>

      {/* Source Selector */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="source">Source:</Label>
        <Select name="source" defaultValue="acl_anthology">
          <SelectTrigger id="source" className="w-full">
            <SelectValue placeholder="Select source" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="acl_anthology">ACL Anthology</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Max Papers */}
      <div className="flex flex-col gap-2">
        <Label htmlFor="maxPapers">Max Papers:</Label>
        <Input id="maxPapers" type="number" name="maxPapers" />
      </div>

      <Button type="submit">Search</Button>
    </form>
  )
}
