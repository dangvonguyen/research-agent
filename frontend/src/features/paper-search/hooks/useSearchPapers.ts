import { useState } from "react";
import type { Paper } from "@/api";
import { searchPapers } from "../api/searchApi";
import type { SearchParams } from "../types";

export const useSearchPapers = () => {
  const [results, setResults] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async ({ query, urls, source, maxPapers }: SearchParams) => {
    setLoading(true);
    try {
      const data = await searchPapers({ query, urls, source, maxPapers });
      setResults(data);
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return { results, loading, search };
};
