import { type FocusEvent, type MouseEvent, useCallback, useState } from "react";
import { useSidebar } from "@/components/ui";

type SidebarInteractionsHandlers = {
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onFocus: () => void;
  onBlur: (event: FocusEvent<HTMLElement>) => void;
};

export const useSidebarInteractions = () => {
  const { open, setOpen } = useSidebar();
  const [headerInteractive, setHeaderInteractive] = useState(false);

  const handleMouseEnter = useCallback(() => {
    if (!open) {
      setHeaderInteractive(true);
    }
  }, [open]);

  const handleMouseLeave = useCallback(() => {
    if (!open) {
      setHeaderInteractive(false);
    }
  }, [open]);

  const handleFocus = useCallback(() => {
    if (!open) {
      setHeaderInteractive(true);
    }
  }, [open]);

  const handleBlur = useCallback(
    (event: FocusEvent<HTMLElement>) => {
      const relatedTarget = event.relatedTarget as Node | null;

      if (
        !open &&
        (!relatedTarget || !event.currentTarget.contains(relatedTarget))
      ) {
        setHeaderInteractive(false);
      }
    },
    [open],
  );

  const headerHandlers: SidebarInteractionsHandlers = {
    onMouseEnter: handleMouseEnter,
    onMouseLeave: handleMouseLeave,
    onFocus: handleFocus,
    onBlur: handleBlur,
  };

  const showLogo = open || (!open && !headerInteractive);
  const showTrigger = open || (!open && headerInteractive);

  const handleEmptySpaceClick = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (open) {
        return;
      }

      if (event.target !== event.currentTarget) {
        return;
      }

      setOpen(true);
    },
    [open, setOpen],
  );

  return {
    open,
    headerInteractive,
    showLogo,
    showTrigger,
    headerHandlers,
    handleEmptySpaceClick,
  };
};
