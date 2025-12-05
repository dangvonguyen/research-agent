import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import apiClient from "@/api/client";

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "var(--color-chart-6)",
  "var(--color-chart-7)",
  "var(--color-chart-8)",
];

interface PapersPerMonth {
  month: string;
  papers: number;
}

interface PapersByCollection {
  name: string;
  value: number;
  fill?: string;
}

interface AnalyticsChartsProps {
  shouldFetch: boolean;
}

export function AnalyticsCharts({ shouldFetch }: AnalyticsChartsProps) {
  const [papersPerMonth, setPapersPerMonth] = useState<PapersPerMonth[]>([]);
  const [collectionData, setCollectionData] = useState<PapersByCollection[]>([]);
  const [loading, setLoading] = useState(true);
  const fetchingRef = useRef(false);

  useEffect(() => {
    // Only fetch when parent indicates stats are ready (sequential loading)
    if (!shouldFetch) {
      return;
    }

    // Prevent concurrent fetches (e.g., from StrictMode double-mount)
    if (fetchingRef.current) {
      return;
    }
    fetchingRef.current = true;

    let isMounted = true;

    const fetchAnalytics = async () => {
      try {
        setLoading(true);
        // Fetch analytics data sequentially after stats
        const monthData = await apiClient.papers.getPapersPerMonth();
        if (!isMounted) return;
        
        const collectionDataResult = await apiClient.collections.getPapersByCollection();
        if (!isMounted) return;

        // Transform month data to include month names
        const transformedMonthData = monthData.map((item) => ({
          month: MONTH_NAMES[item.month - 1],
          papers: item.papers,
        }));
        setPapersPerMonth(transformedMonthData);

        // Add colors to collection data
        const transformedCollectionData = collectionDataResult.map((item, index) => ({
          ...item,
          fill: CHART_COLORS[index % CHART_COLORS.length],
        }));
        setCollectionData(transformedCollectionData);
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to fetch analytics data:", error);
        // Set empty data on error
        setPapersPerMonth(
          MONTH_NAMES.map((month) => ({ month, papers: 0 }))
        );
        setCollectionData([]);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
        fetchingRef.current = false;
      }
    };

    fetchAnalytics();

    // Cleanup function
    return () => {
      isMounted = false;
      fetchingRef.current = false;
    };
  }, [shouldFetch]);

  if (loading || !shouldFetch) {
    return (
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Papers Added</CardTitle>
            <CardDescription>Monthly addition trend</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-[300px]">
              <p className="text-muted-foreground">Loading...</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Papers by Collection</CardTitle>
            <CardDescription>Distribution across research areas</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-center h-[300px]">
              <p className="text-muted-foreground">Loading...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Papers Added Per Month */}
      <Card>
        <CardHeader>
          <CardTitle>Papers Added</CardTitle>
          <CardDescription>Monthly addition trend</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={papersPerMonth}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="papers" fill="var(--color-primary)" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Papers by Collection */}
      <Card>
        <CardHeader>
          <CardTitle>Papers by Collection</CardTitle>
          <CardDescription>Distribution across research areas</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={collectionData as any}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name} (${value})`}
                outerRadius={110}
                fill="#8884d8"
                dataKey="value"
              >
                {collectionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill || CHART_COLORS[index % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

