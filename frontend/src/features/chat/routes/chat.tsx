import { useLoaderData } from "react-router-dom";
import Chat from "../components/Chat";
import type { ChatLoaderData } from "../types";

export function ChatView() {
  const { id, initialMessages } = useLoaderData() as ChatLoaderData;

  return <Chat key={id} id={id} initialMessages={initialMessages} />;
}
