import type { components } from "@/types/openapi"

type Paper = components["schemas"]["Paper"]

export const mockSearchPapers = async (): Promise<Paper[]> => {
  console.log("Using MOCK search API")

  return Promise.resolve([
    {
      title: "Exploring Large Language Models",
      authors: ["Alice Smith", "Bob Lee"],
      source: "acl_anthology",
      source_id: "ACL2023-001",
      year: 2023,
      url: "https://example.com/paper1",
      pdf_url: "https://example.com/paper1.pdf",
      local_pdf_path: null,
      venues: ["ACL 2023"],
      sections: {
        abstract: {
          title: "Abstract",
          content: "This paper explores the capabilities of LLMs...",
          level: 1,
        },
        introduction: {
          title: "Introduction",
          content: "In this study, we investigate...",
          level: 1,
        },
        conclusion: {
          title: "Conclusion",
          content: "We conclude that LLMs are powerful...",
          level: 1,
        },
      },
      job_id: null,
      _id: "paper1",
      created_at: "2023-07-01T10:00:00.000Z",
      updated_at: "2023-07-02T10:00:00.000Z",
    },
    {
      title: "Neural Networks for NLP",
      authors: ["John Doe"],
      source: "acl_anthology",
      source_id: "ACL2022-123",
      year: 2022,
      url: "https://example.com/paper2",
      pdf_url: "https://example.com/paper2.pdf",
      local_pdf_path: null,
      venues: ["ACL 2022"],
      sections: {
        abstract: {
          title: "Abstract",
          content: "This paper reviews recent progress in NLP...",
          level: 1,
        },
        introduction: {
          title: "Introduction",
          content: "The paper begins by discussing...",
          level: 1,
        },
        conclusion: {
          title: "Conclusion",
          content: "Future work includes improving model robustness...",
          level: 1,
        },
      },
      job_id: null,
      _id: "paper2",
      created_at: "2022-07-01T10:00:00.000Z",
      updated_at: "2022-07-02T10:00:00.000Z",
    },
  ])
}
