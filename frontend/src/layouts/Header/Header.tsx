import styles from "./Header.module.css"

interface HeaderProps {
  onToggleSidebar: () => void
}

const Header = ({ onToggleSidebar }: HeaderProps) => {
  return (
    <header className={styles.header}>
      <button className={styles.toggleButton} onClick={onToggleSidebar}>
        ☰
      </button>
      <h1 className={styles.title}>PaperFetcher</h1>
    </header>
  )
}

export default Header
