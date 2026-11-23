export interface StickerMeta {
  id: string
  name: string
  url: string
  mime?: string
}

interface StickerRecord {
  id: string
  url: string
  blob: Blob
  bytes: number
  lastUsedAt: number
}

const DB_NAME = 'hoshinoumi-stickers'
const STORE = 'stickers'
const MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000
const MAX_BYTES = 200 * 1024 * 1024

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') return reject(new Error('IndexedDB unavailable'))
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'id' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error ?? new Error('open sticker cache failed'))
  })
}

function requestToPromise<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error ?? new Error('sticker cache request failed'))
  })
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error ?? new Error('read sticker failed'))
    reader.readAsDataURL(blob)
  })
}

async function readRecord(id: string): Promise<StickerRecord | null> {
  const db = await openDb()
  try {
    const tx = db.transaction(STORE, 'readonly')
    return (await requestToPromise(tx.objectStore(STORE).get(id))) ?? null
  } finally {
    db.close()
  }
}

async function writeRecord(record: StickerRecord): Promise<void> {
  const db = await openDb()
  try {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).put(record)
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error ?? new Error('write sticker failed'))
    })
  } finally {
    db.close()
  }
}

async function touchRecord(record: StickerRecord): Promise<void> {
  record.lastUsedAt = Date.now()
  await writeRecord(record)
}

export async function cleanupStickerCache(now = Date.now()): Promise<void> {
  if (typeof indexedDB === 'undefined') return
  const db = await openDb()
  try {
    const tx = db.transaction(STORE, 'readwrite')
    const store = tx.objectStore(STORE)
    const all = (await requestToPromise(store.getAll())) as StickerRecord[]
    const alive = all.filter(row => now - Number(row.lastUsedAt || 0) <= MAX_AGE_MS)
    for (const row of all) if (!alive.includes(row)) store.delete(row.id)
    let total = alive.reduce((sum, row) => sum + Number(row.bytes || 0), 0)
    for (const row of [...alive].sort((a, b) => Number(a.lastUsedAt) - Number(b.lastUsedAt))) {
      if (total <= MAX_BYTES) break
      store.delete(row.id)
      total -= Number(row.bytes || 0)
    }
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error ?? new Error('cleanup sticker failed'))
    })
  } finally {
    db.close()
  }
}

export async function getStickerDataUrl(sticker: StickerMeta): Promise<string> {
  const cached = await readRecord(sticker.id)
  if (cached && cached.url === sticker.url) {
    await touchRecord(cached)
    return blobToDataUrl(cached.blob)
  }
  const response = await fetch(sticker.url, { cache: 'no-store' })
  if (!response.ok) throw new Error(`sticker HTTP ${response.status}`)
  const blob = await response.blob()
  if (!blob.type.startsWith('image/')) throw new Error('sticker is not an image')
  await writeRecord({ id: sticker.id, url: sticker.url, blob, bytes: blob.size, lastUsedAt: Date.now() })
  return blobToDataUrl(blob)
}

export async function removeSticker(id: string): Promise<void> {
  const db = await openDb()
  try {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).delete(id)
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error ?? new Error('delete sticker failed'))
    })
  } finally {
    db.close()
  }
}

export async function clearStickerCache(): Promise<void> {
  const db = await openDb()
  try {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).clear()
    await new Promise<void>((resolve, reject) => {
      tx.oncomplete = () => resolve()
      tx.onerror = () => reject(tx.error ?? new Error('clear sticker failed'))
    })
  } finally {
    db.close()
  }
}
