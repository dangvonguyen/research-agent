// Mock collections data
export const mockCollections = [
  {
    id: 1,
    name: "Natural Language Processing",
    description: "Papers on NLP, transformers, and language models",
  },
  {
    id: 2,
    name: "Computer Vision",
    description: "Image recognition, object detection, segmentation",
  },
  {
    id: 3,
    name: "Machine Learning Fundamentals",
    description: "Core ML concepts and algorithms",
  },
  {
    id: 4,
    name: "Reinforcement Learning",
    description: "RL, agent-based systems, and control",
  },
  {
    id: 5,
    name: "Graph Neural Networks",
    description: "GNNs and relational learning",
  },
  {
    id: 6,
    name: "Quantum Computing",
    description: "Quantum algorithms and computation",
  },
  {
    id: 7,
    name: "Generative Models",
    description: "GANs, VAEs, and diffusion models",
  },
  {
    id: 8,
    name: "Computer Security",
    description: "Adversarial examples and robustness",
  },
  {
    id: 9,
    name: "Optimization Theory",
    description: "Optimization algorithms and convergence",
  },
  {
    id: 10,
    name: "Probabilistic Models",
    description: "Bayesian methods and graphical models",
  },
  {
    id: 11,
    name: "Time Series Analysis",
    description: "Temporal data and sequence modeling",
  },
  {
    id: 12,
    name: "Federated Learning",
    description: "Distributed and privacy-preserving ML",
  },
];

// Mock papers data
export const mockPapers = [
  {
    id: "1",
    title: "Attention is All You Need",
    authors: ["Ashish Vaswani", "Noam Shazeer", "Parmar Arav"],
    year: 2017,
    venue: "NeurIPS 2017",
    abstract:
      "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. In this work, we propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
    source_type: "url" as const,
    source_url: "https://arxiv.org/abs/1706.03762",
    file_path: null,
    parsed: true,
    created_at: new Date("2017-06-12"),
    updated_at: new Date("2017-06-12"),
    keywords: ["deep learning", "transformers", "NLP", "attention", "sequence modeling"],
    tags: ["important", "core-ml"],
    collectionIds: [1, 2],
  },
  {
    id: "2",
    title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    authors: ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
    year: 2018,
    venue: "NAACL 2019",
    abstract:
      "We introduce a new language representation model called BERT, designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
    source_type: "url" as const,
    source_url: "https://arxiv.org/abs/1810.04805",
    file_path: null,
    parsed: true,
    created_at: new Date("2018-10-11"),
    updated_at: new Date("2018-10-11"),
    keywords: ["NLP", "transformers", "pre-training", "language models", "bidirectional"],
    tags: ["nlp-models"],
    collectionIds: [1],
  },
  {
    id: "3",
    title: "ImageNet Classification with Deep Convolutional Neural Networks",
    authors: ["Alex Krizhevsky", "Ilya Sutskever", "Geoffrey Hinton"],
    year: 2012,
    venue: "NeurIPS 2012",
    abstract:
      "We trained a large, deep convolutional neural network to classify the 1.2 million high-resolution images in the ImageNet LSVRC-2010 contest into 1000 different classes.",
    source_type: "upload" as const,
    source_url: null,
    file_path: "/papers/imagenet-classification.pdf",
    parsed: true,
    created_at: new Date("2012-12-01"),
    updated_at: new Date("2012-12-01"),
    keywords: ["computer vision", "deep learning", "CNN", "image classification", "AlexNet"],
    tags: ["computer-vision"],
    collectionIds: [2],
  },
];

// Helper function to get collection papers count
export function getCollectionPaperCount(collectionId: number): number {
  return mockPapers.filter((p) => p.collectionIds.includes(collectionId)).length;
}

// Helper function to get all papers in a collection
export function getPapersInCollection(collectionId: number) {
  return mockPapers.filter((p) => p.collectionIds.includes(collectionId));
}

