// src/features/paperSearch/components/SearchForm/SearchForm.tsx
import { useState } from "react"
import styles from "./SearchForm.module.css"

interface Props {
  onSearch: (query: string, source: string) => void
}

const SearchForm = ({ onSearch }: Props) => {
  const [query, setQuery] = useState("")
  const [source, setSource] = useState("acl")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSearch(query, source)
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
