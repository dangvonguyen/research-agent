import { type LoaderFunctionArgs, redirect } from "react-router-dom";
import { apiClient } from "@/api";
import { generateUUID, isValidUUID } from "@/lib/utils";
import type { ChatLoaderData } from "../types";

export async function homeLoader(): Promise<ChatLoaderData> {
  const id = generateUUID();

  return {
    id,
    initialMessages: [],
  };
}

export async function chatLoader({
  params,
}: LoaderFunctionArgs): Promise<ChatLoaderData> {
  const { chatId } = params;

  if (!chatId || !isValidUUID(chatId)) {
    sessionStorage.setItem("toastError", `Conversation not found ${chatId}`);
    throw redirect("/");
  }

  try {
    const [conversation, messages] = await Promise.all([
      apiClient.conversations.getById(chatId),
      apiClient.conversations.getMessages(chatId),
    ]);

    return {
      id: conversation.data.id,
      initialMessages: messages.data,
    };
  } catch (error) {
    console.error("Failed to load conversation:", error);

    sessionStorage.setItem("toastError", `Conversation not found ${chatId}`);
    throw redirect("/");
  }
}
