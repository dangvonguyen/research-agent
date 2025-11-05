import type { MouseEvent, ReactNode } from "react";
import { SidebarMenuButton, SidebarMenuItem } from "@/components/ui";

interface SidebarButtonProps {
  icon: ReactNode;
  label: string;
  onClick: () => void;
}

export const SidebarButton = ({ icon, label, onClick }: SidebarButtonProps) => {
  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onClick();
  };

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        onClick={handleClick}
        tooltip={label}
        className="group/button cursor-pointer"
      >
        <div className="flex items-center justify-center size-4">{icon}</div>
        <span className="text-sm">{label}</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
};
