export interface Message {
  id: string
  content: string
  role: "user" | "assistant"
  createdAt: Date
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  lastMessageAt: Date
}
