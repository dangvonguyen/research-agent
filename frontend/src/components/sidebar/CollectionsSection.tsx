import { FolderKanban } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  SidebarGroup,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui";

export const CollectionsSection = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <SidebarGroup>
      <SidebarMenu className="gap-2">
        <SidebarMenuItem>
          <SidebarMenuButton
            onClick={() => navigate("/collections")}
            isActive={location.pathname.startsWith("/collections")}
            tooltip="Collections"
            className="group/button cursor-pointer"
          >
            <FolderKanban className="h-4 w-4" />
            <span className="text-sm">Collections</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarGroup>
  );
};

