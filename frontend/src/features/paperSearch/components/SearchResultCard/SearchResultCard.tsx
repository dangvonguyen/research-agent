import styles from "./SearchResultCard.module.css"

interface SearchResultCardProps {
  title: string
  summary: string
  onClick?: () => void
}

const SearchResultCard = ({ title, summary, onClick }: SearchResultCardProps) => {
  return (
    <button className={styles.card} onClick={onClick}>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.summary}>{summary}</p>
    </button>
  )
}

export default SearchResultCard
