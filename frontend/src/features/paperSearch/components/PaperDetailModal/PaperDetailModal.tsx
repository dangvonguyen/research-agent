import Modal from "@/components/modal/modal"
import type { Paper } from "@/types/paper.types"
import styles from "./PaperDetailModal.module.css"

interface PaperDetailModalProps {
  paper: Paper | null
  onClose: () => void
}

const PaperDetailModal = ({ paper, onClose }: PaperDetailModalProps) => {
  if (!paper) return null

  return (
    <Modal isOpen={!!paper} onClose={onClose}>
      <div className={styles.content}>
        <div className={styles.header}>
          <h2 className={styles.title}>{paper.title}</h2>
          <p className={styles.authors}>{paper.authors}</p>
        </div>

        <p><strong>Year:</strong> {paper.year}</p>

        <div className={styles.section}>
          <strong>Abstract</strong>
          <div>{paper.abstract}</div>
        </div>

        <div className={styles.section}>
          <strong>Introduction</strong>
          <div>{paper.introduction}</div>
        </div>

        <div className={styles.section}>
          <strong>Conclusion</strong>
          <div>{paper.conclusion}</div>
        </div>

        <div className={styles.linkWrapper}>
          <a href={paper.url} target="_blank" rel="noopener noreferrer">
            📄 View PDF
          </a>
        </div>
      </div>
    </Modal>
  )
}

export default PaperDetailModal
