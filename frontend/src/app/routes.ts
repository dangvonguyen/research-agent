import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/AppLayout";
import { chatRoutes } from "@/features/chat";
import { collectionsRoutes } from "@/features/collections";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: AppLayout,
    children: [...chatRoutes, ...collectionsRoutes],
  },
]);
