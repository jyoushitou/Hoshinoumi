import { describe, it, expect, vi, beforeEach } from 'vitest'
import { HttpClient, ApiError } from '@/api/client'
describe('HttpClient', () => {
  beforeEach(() => vi.restoreAllMocks())
  it('parses json', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 })))
    await expect(new HttpClient('http://x').get('/healthz')).resolves.toEqual({ ok: true })
  })
  it('throws ApiError on non-2xx', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ message: 'no' }), { status: 401 })))
    await expect(new HttpClient('http://x').get('/x')).rejects.toBeInstanceOf(ApiError)
  })
})
