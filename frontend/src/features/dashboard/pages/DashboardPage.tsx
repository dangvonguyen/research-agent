import { useEffect, useState, useRef } from "react";
import { apiClient, type Paper } from "@/api";
import {
  SearchBar,
  AddPapersSection,
  type AddPapersSectionRef,
  PaperLibrarySection,
  EmptyState,
} from "../index";

export function DashboardPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const addPapersRef = useRef<AddPapersSectionRef>(null);

  useEffect(() => {
    const fetchPapers = async () => {
      try {
        const fetchedPapers = await apiClient.papers.list();
        setPapers(fetchedPapers);
      } catch (error) {
        console.error("Failed to fetch papers:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchPapers();
  }, []);

  const handlePaperAdded = async () => {
    try {
      const fetchedPapers = await apiClient.papers.list();
      setPapers(fetchedPapers);
    } catch (error) {
      console.error("Failed to refresh papers:", error);
    }
  };

  // Poll for new papers if there are papers with job_id that are still processing
  useEffect(() => {
    const papersWithActiveJobs = papers.filter(
      (paper) => paper.job_id && paper.job_id.trim() !== ""
    );

    if (papersWithActiveJobs.length === 0) return;

    const pollingInterval = setInterval(async () => {
      try {
        const fetchedPapers = await apiClient.papers.list();
        // Check if we have new papers or updated papers
        const hasNewPapers = fetchedPapers.length !== papers.length;
        const hasUpdatedPapers = fetchedPapers.some((newPaper) => {
          const oldPaper = papers.find((p) => p._id === newPaper._id);
          return oldPaper && oldPaper.job_id && newPaper.job_id !== oldPaper.job_id;
        });

        if (hasNewPapers || hasUpdatedPapers) {
          setPapers(fetchedPapers);
        }

        // Stop polling if no papers with job_id exist anymore
        const activeJobs = fetchedPapers.filter(
          (paper) => paper.job_id && paper.job_id.trim() !== ""
        );
        if (activeJobs.length === 0) {
          clearInterval(pollingInterval);
        }
      } catch (error) {
        console.error("Failed to poll for papers:", error);
      }
    }, 3000); // Poll every 3 seconds

    return () => {
      clearInterval(pollingInterval);
    };
  }, [papers]);

  const filteredPapers = papers.filter((paper) => {
    if (!searchQuery.trim()) return true;
    const query = searchQuery.toLowerCase();
    return (
      paper.title.toLowerCase().includes(query) ||
      paper.authors.some((author) => author.toLowerCase().includes(query)) ||
      paper.venues?.some((venue) => venue.toLowerCase().includes(query))
    );
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Search Bar */}
      <div className="p-3 border-b">
        <SearchBar
          value={searchQuery}
          onChange={setSearchQuery}
          placeholder="Search papers, authors, venues"
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {papers.length === 0 ? (
          <div className="max-w-4xl mx-auto space-y-8">
            <AddPapersSection ref={addPapersRef} onPaperAdded={handlePaperAdded} />
            <EmptyState
              onUploadClick={() => addPapersRef.current?.triggerFileUpload()}
            />
          </div>
        ) : (
          <div className="max-w-7xl mx-auto space-y-8">
            <AddPapersSection ref={addPapersRef} onPaperAdded={handlePaperAdded} />
            <PaperLibrarySection papers={filteredPapers} />
          </div>
        )}
      </div>
    </div>
  );
}

