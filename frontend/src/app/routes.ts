import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/AppLayout";
import { chatRoutes } from "@/features/chat";
import { dashboardRoutes } from "@/features/dashboard";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: AppLayout,
    children: [...chatRoutes, ...dashboardRoutes],
  },
]);
