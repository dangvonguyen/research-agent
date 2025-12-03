import { useState, useEffect } from "react";
import { toast } from "sonner";
import { apiClient } from "@/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BookOpen, FolderOpen, Clock } from "lucide-react";
import { RecentActivityList } from "./RecentActivityList";
import { AnalyticsCharts } from "./AnalyticsCharts";
import { TopSearchBar } from "./TopSearchBar";

export function CollectionsOverview() {
  const [stats, setStats] = useState({
    totalPapers: 0,
    totalCollections: 0,
    recentlyAdded: 0,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setIsLoading(true);
        const [papers, collections] = await Promise.all([
          apiClient.papers.list(0, 1000), // Get all papers for count
          apiClient.collections.list(0, 1000), // Get all collections for count
        ]);

        // Calculate recently added (papers added in last 7 days)
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);
        const recentlyAdded = papers.filter(
          (p) => new Date(p.created_at) >= weekAgo
        ).length;

        setStats({
          totalPapers: papers.length,
          totalCollections: collections.length,
          recentlyAdded,
        });
      } catch (error) {
        console.error("Failed to fetch stats:", error);
        toast.error("Failed to load dashboard data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);

  return (
    <div className="flex flex-col h-screen">
      <TopSearchBar />
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl space-y-6 px-6 py-8">
      {/* Page Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-foreground">Dashboard Overview</h1>
        <p className="text-muted-foreground">Welcome back! Here's your research library at a glance.</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Total Papers Card */}
        <Card className="bg-gradient-to-br from-primary/5 to-primary/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Papers</CardTitle>
            <BookOpen className="h-5 w-5 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "..." : stats.totalPapers}</div>
            <p className="text-xs text-muted-foreground">papers in your library</p>
          </CardContent>
        </Card>

        {/* Total Collections Card */}
        <Card className="bg-gradient-to-br from-accent/5 to-accent/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collections</CardTitle>
            <FolderOpen className="h-5 w-5 text-accent" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "..." : stats.totalCollections}</div>
            <p className="text-xs text-muted-foreground">organized collections</p>
          </CardContent>
        </Card>

        {/* Recently Added Card */}
        <Card className="bg-gradient-to-br from-green-500/5 to-green-500/10">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Recently Added</CardTitle>
            <Clock className="h-5 w-5 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{isLoading ? "..." : stats.recentlyAdded}</div>
            <p className="text-xs text-muted-foreground">this week</p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <AnalyticsCharts />

      {/* Recent Activity Section */}
      <RecentActivityList />
        </div>
      </div>
    </div>
  );
}

