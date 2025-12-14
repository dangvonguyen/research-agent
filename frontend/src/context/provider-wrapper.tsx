import type { ComponentType, ReactNode } from "react";

// biome-ignore lint/suspicious/noExplicitAny: Any props types
type ProviderConfig = readonly [ComponentType<any>, any];

interface ProviderWrapperProps {
  providers: readonly ProviderConfig[];
  children: ReactNode;
}

export default function ProviderWrapper({
  providers,
  children,
}: ProviderWrapperProps) {
  return providers.reduceRight(
    (acc, [Provider, props]) => <Provider {...props}>{acc}</Provider>,
    children,
  );
}
