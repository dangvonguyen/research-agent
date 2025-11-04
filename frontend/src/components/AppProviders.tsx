import { SidebarProvider } from "@/components/ui";
import ProviderWrapper from "@/context/provider-wrapper";
import { ThemeProvider } from "@/context/theme-provider";

function AppProviders({ children }: { children: React.ReactNode }) {
  const providers = [
    [SidebarProvider, {}],
    [ThemeProvider, {}],
  ] as const;
  return <ProviderWrapper providers={providers}>{children}</ProviderWrapper>;
}

export default AppProviders;
