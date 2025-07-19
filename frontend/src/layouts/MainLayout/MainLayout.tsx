import { useState } from "react"
import Header from "../Header/Header"
import Sidebar from "../Sidebar/Sidebar"
import styles from "./MainLayout.module.css"

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout = ({ children }: MainLayoutProps) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev)
  }

  return (
    <div className={styles.container}>
      <Header onToggleSidebar={toggleSidebar} />
      <div className={styles.body}>
        <Sidebar isOpen={isSidebarOpen} />
        <main className={styles.content}>{children}</main>
      </div>
    </div>
  )
}

export default MainLayout
