import { useEffect, useState, useRef } from "react";
import { apiClient, type Paper, type JobStatus } from "@/api";
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
  // Track job IDs for newly created jobs (only in current session)
  const [newJobIds, setNewJobIds] = useState<Set<string>>(new Set());
  const [jobStatuses, setJobStatuses] = useState<Record<string, JobStatus>>({});
  const addPapersRef = useRef<AddPapersSectionRef>(null);

  useEffect(() => {
    let isMounted = true;

    const fetchPapers = async () => {
      try {
        const fetchedPapers = await apiClient.papers.list();
        
        if (isMounted) {
          // Ensure we have an array
          const papersArray = Array.isArray(fetchedPapers) ? fetchedPapers : [];
          setPapers(papersArray);
          setLoading(false);
        }
      } catch (error) {
        console.error("Failed to fetch papers:", error);
        if (isMounted) {
          setPapers([]);
          setLoading(false);
        }
      }
    };

    fetchPapers();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleJobCreated = (jobId: string) => {
    // Track new job ID - polling will start automatically
    setNewJobIds((prev) => new Set(prev).add(jobId));
  };

  // Poll for job statuses and new papers for new jobs only
  useEffect(() => {
    if (newJobIds.size === 0) {
      setJobStatuses({});
      return;
    }

    const fetchJobStatusesAndPapers = async () => {
      try {
        const jobIdsArray = Array.from(newJobIds);
        
        // Fetch job statuses
        const jobStatusPromises = jobIdsArray.map(async (jobId) => {
          try {
            const job = await apiClient.crawlerJobs.getById(jobId);
            return { jobId, status: job.status };
          } catch (error) {
            console.error(`Failed to fetch job status for ${jobId}:`, error);
            return null;
          }
        });

        const results = await Promise.all(jobStatusPromises);
        const newJobStatuses: Record<string, JobStatus> = {};
        const stillActiveJobIds = new Set<string>();

        results.forEach((result) => {
          if (result) {
            newJobStatuses[result.jobId] = result.status;
            // Only keep jobs that are still pending or running
            if (result.status === "pending" || result.status === "running") {
              stillActiveJobIds.add(result.jobId);
            }
          }
        });

        setJobStatuses((prev) => ({ ...prev, ...newJobStatuses }));
        
        // Fetch papers to check for new ones with the job_id
        try {
          const fetchedPapers = await apiClient.papers.list();
          // Replace papers list to get latest state (including new papers)
          setPapers(fetchedPapers);
        } catch (error) {
          console.error("Failed to fetch papers:", error);
        }
        
        // Remove completed/failed jobs from tracking
        if (stillActiveJobIds.size !== newJobIds.size) {
          setNewJobIds(stillActiveJobIds);
        }
      } catch (error) {
        console.error("Failed to fetch job statuses:", error);
      }
    };

    // Fetch immediately
    fetchJobStatusesAndPapers();

    // Poll every 3 seconds
    const pollingInterval = setInterval(fetchJobStatusesAndPapers, 3000);

    return () => {
      clearInterval(pollingInterval);
    };
  }, [newJobIds]);

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
            <AddPapersSection 
              ref={addPapersRef} 
              onJobCreated={handleJobCreated}
            />
            <EmptyState
              onUploadClick={() => addPapersRef.current?.triggerFileUpload()}
            />
          </div>
        ) : (
          <div className="max-w-7xl mx-auto space-y-8">
            <AddPapersSection 
              ref={addPapersRef} 
              onJobCreated={handleJobCreated}
            />
            <PaperLibrarySection 
              papers={filteredPapers} 
              jobStatuses={jobStatuses}
              newJobIds={newJobIds}
            />
          </div>
        )}
      </div>
    </div>
  );
}

