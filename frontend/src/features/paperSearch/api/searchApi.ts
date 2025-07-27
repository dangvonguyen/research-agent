// src/features/paperSearch/api/searchApi.ts

import type { Paper } from "@/types/paper.types"

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const searchPapers = async (query: string, source: string): Promise<Paper[]> => {
  // Giả lập response từ backend
  return Promise.resolve([
    {
      id: "paper1",
      title: "Exploring Large Language Models",
      authors: ["Alice Smith", "Bob Lee"],
      year: 2023,
      url: "https://example.com/paper1.pdf",
      abstract: "This paper explores the capabilities of LLMs...",
      introduction: "In this study, we investigate...",
      conclusion: "We conclude that LLMs are powerful..."
    },
    {
      id: "paper2",
      title: "Neural Networks for NLP",
      authors: ["John Doe"],
      year: 2022,
      url: "https://example.com/paper2.pdf",
      abstract: "This paper reviews recent progress in NLP...",
      introduction: "The paper begins by discussing...",
      conclusion: "Future work includes improving model robustness..."
    }
  ])
}
