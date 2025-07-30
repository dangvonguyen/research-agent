// src/features/paperSearch/components/SearchForm/SearchForm.tsx
import { useState } from "react"
import styles from "./SearchForm.module.css"

interface Props {
  onSearch: (params: { query: string; source: string; url: string }) => void
}

const SearchForm = ({ onSearch }: Props) => {
  const [query, setQuery] = useState("")
  const [url, setUrl] = useState("")
  const [source, setSource] = useState("acl")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch({ query, source, url })
  }

  return (
    <form className={styles.formWrapper} onSubmit={handleSubmit}>
      <div className={styles.inputGroup}>
        <label htmlFor="query">Search Query:</label>
        <input
          id="query"
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="e.g., Large Language Models"
          className={styles.input}
        />
      </div>

      <div className={styles.inputGroup}>
        <label htmlFor="url">Paper URL:</label>
        <input
          id="url"
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="e.g., https://aclanthology.org/2023.acl-long.1"
          className={styles.input}
        />
      </div>

      <div className={styles.inputGroup}>
        <label htmlFor="source">Source:</label>
        <select
          id="source"
          value={source}
          onChange={e => setSource(e.target.value)}
          className={styles.input}
        >
          <option value="acl">ACL Anthology</option>
          <option value="arxiv">arXiv</option>
        </select>
      </div>

      <button className={styles.button}>Search</button>
    </form>
  )
}

export default SearchForm
