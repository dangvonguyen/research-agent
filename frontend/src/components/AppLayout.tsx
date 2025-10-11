import { Outlet, useMatch } from "react-router-dom";
import { SidebarInset, Toaster } from "@/components/ui";
import AppProviders from "./AppProviders";
import AppSidebar from "./AppSidebar";

export function AppLayout() {
  const { chatId } = useMatch("chat/:chatId")?.params || {};

  return (
    <AppProviders>
      <Toaster position="top-center" />

      <AppSidebar />
      <SidebarInset className="flex flex-col relative">
        <Outlet key={chatId} />
      </SidebarInset>
    </AppProviders>
  );
}
