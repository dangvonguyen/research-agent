import styles from "./SearchForm.module.css"

const SearchForm = () => {
  return (
    <div className={styles.formWrapper}>
      <div className={styles.inputGroup}>
        <label htmlFor="query">Search Query:</label>
        <input id="query" type="text" placeholder="e.g., Large Language Models" className={styles.input} />
      </div>
      <div className={styles.inputGroup}>
        <label htmlFor="source">Source:</label>
        <select id="source" className={styles.input}>
          <option value="arxiv">arXiv</option>
          <option value="springer">Springer</option>
        </select>
      </div>
      <button className={styles.button}>Search</button>
    </div>
  )
}

export default SearchForm
