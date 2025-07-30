// src/features/paperSearch/api/searchApi.ts
import type { Paper } from "@/types/paper.types"

interface SearchParams {
  query: string
  url: string
  source: string
}

export const searchPapers = async ({
  query,
  url,
  source,
}: SearchParams): Promise<Paper[]> => {
  // return fetch("http://localhost:8000/api/search", {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ query, url, source }),
  // }).then(res => res.json());
  

  // Giả lập response:
  console.log("Search API called with:", { query, url, source })

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
