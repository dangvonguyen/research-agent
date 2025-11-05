import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/AppLayout";
import { chatRoutes } from "@/features/chat";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: AppLayout,
    children: [...chatRoutes],
  },
]);
