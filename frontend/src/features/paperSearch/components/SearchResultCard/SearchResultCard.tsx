import styles from "./SearchResultCard.module.css"

interface SearchResultCardProps {
  title: string
  summary: string
}

const SearchResultCard = ({ title, summary }: SearchResultCardProps) => {
  return (
    <div className={styles.card}>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.summary}>{summary}</p>
    </div>
  )
}

export default SearchResultCard
