// src/features/paperSearch/components/SearchResultCard/SearchResultCard.tsx
import styles from "./SearchResultCard.module.css"
import type { Paper } from "@/types/paper.types"

interface SearchResultCardProps extends Paper {
  onClick?: () => void // nếu cần truyền sự kiện khi nhấn card
}

const SearchResultCard = ({
  title,
  authors,
  year,
  abstract,
  onClick,
}: SearchResultCardProps) => {
  return (
    <button className={styles.card} onClick={onClick}>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.meta}>
          <strong>Authors:</strong> {authors} | <strong>Year:</strong> {year}
        </p>
        <p className={styles.abstract}>
          <strong>Abstract:</strong> {abstract}
        </p>
    </button>
  )
}

export default SearchResultCard
