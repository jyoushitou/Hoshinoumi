export interface ApiResponse<T> { ok: boolean; data?: T; message?: string; [key: string]: unknown }
export interface Health { status?: string; version?: string; [key: string]: unknown }
