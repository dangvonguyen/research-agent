import SearchForm from "../../components/SearchForm/SearchForm"
import SearchResultCard from "../../components/SearchResultCard/SearchResultCard"
import styles from "./SearchPage.module.css"

const SearchPage = () => {
  const results = [
    { title: "Efficient AI Retrieval", summary: "An overview of scalable AI search methods..." },
    { title: "Deep Learning Advances", summary: "This paper discusses the latest trends in DL..." },
  ]

  return (
    <div className={styles.container}>
      <div className={styles.left}>
        <SearchForm />
      </div>
      <div className={styles.right}>
        {results.map((r, i) => (
          <SearchResultCard key={i} title={r.title} summary={r.summary} />
        ))}
      </div>
    </div>
  )
}

export default SearchPage
