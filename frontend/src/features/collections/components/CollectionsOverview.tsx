import { BookOpen, FolderOpen } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { AnalyticsCharts } from "./AnalyticsCharts";
import { CollectionsNavBar } from "./CollectionsNavBar";

export function CollectionsOverview() {
  const [stats, setStats] = useState({
    totalPapers: 0,
    totalCollections: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [statsReady, setStatsReady] = useState(false);
  const fetchingRef = useRef(false);

  useEffect(() => {
    // Prevent concurrent fetches (e.g., from StrictMode double-mount)
    if (fetchingRef.current) {
      return;
    }
    fetchingRef.current = true;

    let isMounted = true;

    const fetchData = async () => {
      try {
        setIsLoading(true);

        // 1. First: Fetch papers (for stats)
        const papersData = await apiClient.papers.list();
        if (!isMounted) return;

        // 2. Second: Fetch collections (for stats)
        const collections = await apiClient.collections.list();
        if (!isMounted) return;

        if (!isMounted) return;
        setStats({
          totalPapers: papersData.length,
          totalCollections: collections.length,
        });
        setIsLoading(false);
        setStatsReady(true); // Signal that stats are ready, analytics can start
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to fetch stats:", error);
        toast.error("Failed to load dashboard data");
        setIsLoading(false);
        setStatsReady(true); // Still allow other components to render
      } finally {
        fetchingRef.current = false;
      }
    };

    fetchData();

    // Cleanup function
    return () => {
      isMounted = false;
      fetchingRef.current = false;
    };
  }, []);

  return (
    <div className="flex flex-col h-screen">
      <CollectionsNavBar />
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
          {/* Page Header */}
          <div className="space-y-2">
            <h1 className="text-3xl font-bold text-foreground">
              Collections Overview
            </h1>
            <p className="text-muted-foreground">
              Welcome back! Here's your research library at a glance.
            </p>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* Total Papers Card */}
            <Card className="bg-linear-to-br from-primary/5 to-primary/15">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Papers
                </CardTitle>
                <BookOpen className="h-5 w-5 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {isLoading ? "..." : stats.totalPapers}
                </div>
                <p className="text-xs text-muted-foreground">
                  papers in your library
                </p>
              </CardContent>
            </Card>

            {/* Total Collections Card */}
            <Card className="bg-linear-to-br from-primary/5 to-primary/15">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Collections
                </CardTitle>
                <FolderOpen className="h-5 w-5 text-blue-600" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {isLoading ? "..." : stats.totalCollections}
                </div>
                <p className="text-xs text-muted-foreground">
                  organized collections
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Charts Section */}
          <AnalyticsCharts shouldFetch={statsReady} />
        </div>
      </div>
    </div>
  );
}
