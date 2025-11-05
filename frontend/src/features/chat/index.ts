import type { RouteObject } from "react-router-dom";
import { chatLoader, homeLoader } from "./data/loader";
import { ChatView } from "./routes/chat";

export const chatRoutes: RouteObject[] = [
  {
    path: "/",
    children: [
      {
        index: true,
        Component: ChatView,
        loader: homeLoader,
      },
      {
        path: "chat/:chatId",
        Component: ChatView,
        loader: chatLoader,
      },
    ],
  },
];
