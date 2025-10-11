import type { RouteObject } from "react-router-dom";
import Chat from "./components/Chat";
import { chatLoader, homeLoader } from "./data/loader";

export const chatRoutes: RouteObject[] = [
  {
    path: "/",
    children: [
      {
        index: true,
        Component: Chat,
        loader: homeLoader,
      },
      {
        path: "chat/:chatId",
        Component: Chat,
        loader: chatLoader,
      },
    ],
  },
];
