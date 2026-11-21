type DesktopConfig = { apiBase?: string; apiPrefix?: string }

const desktop = (typeof window !== 'undefined' ? (window as unknown as { desktopShell?: { config?: DesktopConfig } }).desktopShell?.config : undefined) ?? {}

function joinBase(rawBase: string | undefined, prefix: string | undefined) {
  const base = (rawBase ?? '').replace(/\/+$/, '')
  const cleanPrefix = (prefix ?? '').replace(/^\/+|\/+$/g, '')
  if (!base) return ''
  return cleanPrefix ? `${base}/${cleanPrefix}` : base
}

export const env = {
  apiBase: joinBase(desktop.apiBase ?? (import.meta.env.VITE_API_BASE as string | undefined), desktop.apiPrefix),
  appName: (import.meta.env.VITE_APP_NAME as string | undefined) ?? 'Hoshinoumi Web',
}
