export const env = {
  apiBase: (import.meta.env.VITE_API_BASE as string | undefined) ?? '',
  appName: (import.meta.env.VITE_APP_NAME as string | undefined) ?? 'Hoshinoumi Web',
}
