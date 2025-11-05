import { useEffect, useRef } from "react";

type UseScrollOptions<T> = {
  deps?: T[];
  shouldScroll?: (latest: T) => boolean;
  instantOnMount?: boolean;
};

export function useAutoScroll<T>({
  deps = [],
  shouldScroll = () => true,
  instantOnMount = true,
}: UseScrollOptions<T>) {
  const ref = useRef<HTMLDivElement | null>(null);

  // Scroll on mount
  useEffect(() => {
    if (instantOnMount) {
      ref.current?.scrollIntoView({ behavior: "auto" });
    }
  }, [instantOnMount]);

  // On deps update
  useEffect(() => {
    if (deps.length === 0 || !ref.current) return;

    const latest = deps[deps.length - 1];
    if (shouldScroll(latest)) {
      ref.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [deps, shouldScroll]);

  return ref;
}
