import type { components } from "@/types/openapi"

type Paper = components["schemas"]["Paper"]

export const mockSearchPapers = async (): Promise<Paper[]> => {
  console.log("Using MOCK search API")

  return Promise.resolve([
    {
      title: "Exploring Large Language Models Exploring Large Language Models",
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
          content: "This paper explores the capabilities of Large Language Models (LLMs) in understanding, reasoning, and generating human-like text across a wide range of tasks. In particular, it investigates their strengths, limitations, and potential applications in both academic research and real-world scenarios.",
          level: 1,
        },
        introduction: {
        title: "Introduction",
        content:
            "In this study, we investigate the potential and limitations of large language models (LLMs) when applied to complex academic and industrial tasks. Recent advancements in natural language processing have demonstrated that LLMs can perform not only basic text generation, but also reasoning, summarization, and retrieval-based applications at scale. However, questions remain regarding their reliability, interpretability, and integration into real-world systems. This paper provides both a theoretical discussion and an empirical evaluation to shed light on how LLMs can be effectively adopted while mitigating common challenges.",
        level: 1,
        },

        conclusion: {
        title: "Conclusion",
        content:
            "We conclude that LLMs represent a transformative step in artificial intelligence, offering significant benefits for information retrieval, content generation, and decision support. While they show strong performance in tasks requiring linguistic fluency and contextual understanding, they also exhibit limitations such as susceptibility to hallucinations, sensitivity to input phrasing, and high computational demands. Future research should focus on improving trustworthiness, designing hybrid architectures that combine symbolic and neural methods, and developing evaluation benchmarks that better capture real-world requirements. By addressing these challenges, LLMs can be harnessed more responsibly and effectively across diverse domains.",
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
