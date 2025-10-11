import { SidebarProvider } from "@/components/ui"
import ProviderWrapper from "@/context/provider-wrapper"

function AppProviders({ children }: { children: React.ReactNode }) {
  const providers = [
    // May add more providers here in the future
    [SidebarProvider, {}],
  ] as const
  return <ProviderWrapper providers={providers}>{children}</ProviderWrapper>
}

export default AppProviders
