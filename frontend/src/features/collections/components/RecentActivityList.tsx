import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { FileText, FolderOpen } from "lucide-react";

const recentItems = [
  {
    id: 1,
    type: "paper",
    title: "Attention Is All You Need",
    authors: "Vaswani et al.",
    date: "2 hours ago",
    collection: "NLP",
  },
  {
    id: 2,
    type: "paper",
    title: "BERT: Pre-training of Deep Bidirectional Transformers",
    authors: "Devlin et al.",
    date: "1 day ago",
    collection: "NLP",
  },
  {
    id: 3,
    type: "paper",
    title: "ImageNet-21K Pretraining for the Masses",
    authors: "Ridnik et al.",
    date: "3 days ago",
    collection: "CV",
  },
  {
    id: 4,
    type: "collection",
    title: "Reinforcement Learning Basics",
    date: "1 week ago",
  },
];

export function RecentActivityList() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <CardDescription>Recently viewed and added papers</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {recentItems.map((item) => (
            <div
              key={item.id}
              className="flex items-start justify-between rounded-lg border border-border p-3 hover:bg-secondary transition-colors"
            >
              <div className="flex gap-3">
                {item.type === "paper" ? (
                  <FileText className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                ) : (
                  <FolderOpen className="h-5 w-5 text-accent mt-0.5 flex-shrink-0" />
                )}
                <div>
                  <p className="font-medium text-foreground">{item.title}</p>
                  {item.type === "paper" && (
                    <>
                      <p className="text-sm text-muted-foreground">{item.authors}</p>
                      <div className="flex gap-2 mt-1">
                        <span className="inline-block rounded-full bg-primary/10 px-2 py-1 text-xs text-primary">
                          {item.collection}
                        </span>
                      </div>
                    </>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">{item.date}</p>
                </div>
              </div>
              <Button variant="ghost" size="sm">
                Open
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

