import type { MouseEvent, ReactNode } from "react";
import { SidebarMenuButton, SidebarMenuItem } from "@/components/ui";

interface SidebarButtonProps {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  isActive?: boolean;
}

export const SidebarButton = ({
  icon,
  label,
  onClick,
  isActive = false,
}: SidebarButtonProps) => {
  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onClick();
  };

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        onClick={handleClick}
        isActive={isActive}
        tooltip={label}
        className="group/button cursor-pointer"
      >
        <div className="flex items-center justify-center size-4">{icon}</div>
        <span className="text-sm">{label}</span>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
};
