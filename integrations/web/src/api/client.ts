import { env } from '@/config/env'
export class ApiError extends Error {
  constructor(public status: number, message: string, public data?: unknown) {
    super(message); this.name = 'ApiError'
  }
}
export interface RequestOptions { method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'; body?: unknown; token?: string; signal?: AbortSignal }
export class HttpClient {
  private token = ''
  setToken(token: string) { this.token = token }
  constructor(private baseUrl = env.apiBase) {}
  private url(path: string) {
    if (/^https?:\/\//i.test(path)) return path
    return this.baseUrl.replace(/\/+$/, '') + path
  }
  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const headers: Record<string, string> = { accept: 'application/json' }
    if (options.body !== undefined) headers['content-type'] = 'application/json'
    const token = options.token ?? this.token
    if (token) headers.authorization = `Bearer ${token}`
    const res = await fetch(this.url(path), {
      method: options.method ?? 'GET', headers, signal: options.signal,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
    const text = await res.text()
    let data: unknown = text
    try { data = text ? JSON.parse(text) : {} } catch { /* keep raw text */ }
    if (!res.ok) throw new ApiError(res.status, (data as { message?: string })?.message ?? `HTTP ${res.status}`, data)
    return data as T
  }
  get<T>(path: string, token?: string, signal?: AbortSignal) { return this.request<T>(path, { token, signal }) }
  post<T>(path: string, body: unknown, token?: string) { return this.request<T>(path, { method: 'POST', body, token }) }
  delete<T>(path: string, body?: unknown, token?: string) { return this.request<T>(path, { method: 'DELETE', body, token }) }
  patch<T>(path: string, body: unknown, token?: string) { return this.request<T>(path, { method: 'PATCH', body, token }) }
  put<T>(path: string, body: unknown, token?: string) { return this.request<T>(path, { method: 'PUT', body, token }) }
}
export const http = new HttpClient()
