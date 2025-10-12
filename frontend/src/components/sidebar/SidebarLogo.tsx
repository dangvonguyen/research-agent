import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";
import { Zap } from "../Icons";

type SidebarLogoProps = {
  size?: number;
  className?: string;
  showWhenCollapsed?: boolean;
};

export const SidebarLogo = ({ size = 16, className }: SidebarLogoProps) => {
  return (
    <Link
      to="/"
      className={cn("p-1.5 rounded-md hover:bg-sidebar-accent", className)}
    >
      <Zap size={size} />
    </Link>
  );
};
