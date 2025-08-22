interface SidebarProps {
  isOpen: boolean
}

const Sidebar = ({ isOpen }: SidebarProps) => {
  return (
    <aside
      className={`w-[200px] bg-gray-50 border-r border-gray-200 p-4 transform transition-transform duration-300 ease-in-out
        ${isOpen ? "translate-x-0" : "-translate-x-full"}`}
    >
      <nav>
        <ul className="list-none p-0">
          <li className="mb-4 font-medium cursor-pointer hover:text-blue-600">
            Menu 1
          </li>
          <li className="mb-4 font-medium cursor-pointer hover:text-blue-600">
            Menu 2
          </li>
          {/* Thêm mục menu nếu cần */}
        </ul>
      </nav>
    </aside>
  )
}

export default Sidebar
