import styles from "./Sidebar.module.css"

interface SidebarProps {
  isOpen: boolean
}

const Sidebar = ({ isOpen }: SidebarProps) => {
  return (
    <aside className={`${styles.sidebar} ${isOpen ? styles.open : styles.closed}`}>
      <nav>
        <ul>
          <li>Menu 1</li>
          <li>Menu 2</li>
          {/* Thêm mục menu nếu cần */}
        </ul>
      </nav>
    </aside>
  )
}

export default Sidebar
