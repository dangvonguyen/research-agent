import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui";
import {
  NavigationMenu,
  NavigationMenuList,
  NavigationMenuItem,
  NavigationMenuLink,
} from "@/components/ui/navigation-menu";
import { SavePaperModal } from "./SavePaperModal";

export function CollectionsNavBar() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);

  const isOverviewPage =
    location.pathname === "/collections" ||
    location.pathname === "/collections/overview";

  const isCollectionsPage =
    location.pathname === "/collections/list" ||
    (location.pathname.startsWith("/collections/") &&
      !location.pathname.startsWith("/collections/papers") &&
      !location.pathname.startsWith("/collections/overview") &&
      location.pathname !== "/collections");

  const isPapersPage = location.pathname === "/collections/papers";

  const handleNavigation = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    navigate(path);
  };

  return (
    <>
      <div className="sticky top-0 z-40 border-b border-border bg-card">
        <div className="flex items-center justify-between gap-4 px-6 py-3">
          <NavigationMenu viewport={false}>
            <NavigationMenuList className="gap-6">
              <NavigationMenuItem>
                <NavigationMenuLink
                  data-active={isOverviewPage}
                  onClick={(e) => handleNavigation("/collections", e)}
                  className="
                  flex items-center gap-2 
                  text-base font-semibold 
                  data-[active=true]:text-primary
                "
                >
                  Overview
                </NavigationMenuLink>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavigationMenuLink
                  data-active={isCollectionsPage}
                  onClick={(e) => handleNavigation("/collections/list", e)}
                  className="
                  flex items-center gap-2 
                  text-base font-semibold 
                  data-[active=true]:text-primary
                "
                >
                  Collections
                </NavigationMenuLink>
              </NavigationMenuItem>
              <NavigationMenuItem>
                <NavigationMenuLink
                  data-active={isPapersPage}
                  onClick={(e) => handleNavigation("/collections/papers", e)}
                  className="
                  flex items-center gap-2 
                  text-base font-semibold 
                  data-[active=true]:text-primary
                "
                >
                  Papers
                </NavigationMenuLink>
              </NavigationMenuItem>
            </NavigationMenuList>
          </NavigationMenu>
          <Button onClick={() => setIsSaveModalOpen(true)}>Save Paper</Button>
        </div>
      </div>
      <SavePaperModal
        isOpen={isSaveModalOpen}
        onClose={() => setIsSaveModalOpen(false)}
      />
    </>
  );
}
