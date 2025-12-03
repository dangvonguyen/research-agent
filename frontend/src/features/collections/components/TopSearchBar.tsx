import { useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { SavePaperModal } from "./SavePaperModal";

export function TopSearchBar() {
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);

  return (
    <>
      <div className="sticky top-0 z-40 border-b border-border bg-card">
        <div className="flex items-center justify-between gap-4 px-6 py-3">
          {/* Universal Search Bar */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input placeholder="Search papers by title, authors, DOI, or keywords..." className="pl-10" />
          </div>

          {/* Save Paper Button */}
          <Button onClick={() => setIsSaveModalOpen(true)}>Save Paper</Button>
        </div>
      </div>

      <SavePaperModal isOpen={isSaveModalOpen} onClose={() => setIsSaveModalOpen(false)} />
    </>
  );
}

