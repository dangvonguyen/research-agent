interface MainLayoutProps {
  children: React.ReactNode
}

function MainLayout({ children }: MainLayoutProps) {
  return (
    <>
      <header className="px-8 border-b-2">
        <div className="p-4">
          <a href="/" className="text-xl font-bold">
            Paper Fetcher
          </a>
        </div>
      </header>
      <main className="container mx-auto my-6">{children}</main>
    </>
  )
}

export { MainLayout }
