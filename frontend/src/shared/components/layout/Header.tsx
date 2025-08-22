interface HeaderProps {
  onToggleSidebar: () => void
}

const Header = ({ onToggleSidebar }: HeaderProps) => {
  return (
    <header className="flex items-center px-4 py-1 bg-white border-b border-gray-200">
      <button
        onClick={onToggleSidebar}
        className="mr-4 text-xl bg-transparent cursor-pointer focus:outline-none"
      >
        ☰
      </button>
      <h2 className="text-xl font-bold">PaperFetcher</h2>
    </header>
  )
}

export default Header
