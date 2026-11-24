export function isNativeClient(): boolean {
  if (typeof window === 'undefined') return false
  const bridge = (window as any).HoshinoumiConfig
  const capacitor = (window as any).Capacitor
  return Boolean(bridge?.getEnvironment || capacitor?.isNativePlatform?.())
}
