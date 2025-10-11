import type { ComponentType, ReactNode } from "react"

type ProviderConfig = readonly [ComponentType<object>, object?]

interface ProviderWrapperProps {
  providers: readonly ProviderConfig[]
  children: ReactNode
}

export default function ProviderWrapper({
  providers,
  children,
}: ProviderWrapperProps) {
  return providers.reduceRight(
    (acc, [Provider, props]) => <Provider {...props}>{acc}</Provider>,
    children
  )
}
