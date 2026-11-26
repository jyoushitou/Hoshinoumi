// 信息页跨端契约：Web / 手机 / 套壳共用同一组字段与布局断点。
export interface InfoStatus {
  status?: string
  master_qq?: string
  schema?: number | string
  version?: string
  uptime_seconds?: number
  napcat?: { connected?: boolean; port?: number; mode?: string; self_qq?: string; ws_url?: string; listening?: boolean }
  db?: { engine?: string; tables?: number; size_mb?: number }
  backup?: { last_at?: string; size_mb?: number; kept?: number; checksum?: string }
  stats?: Record<string, number>
}

export interface BalanceInfo {
  currency?: string
  total_balance?: string
  granted_balance?: string
  topped_up_balance?: string
}

export interface InfoBalance {
  is_available?: boolean
  balance_infos?: BalanceInfo[]
  fetched_at?: string
}

export const INFO_BREAKPOINTS = {
  desktopRuntimeColumns: 4,
  mobileRuntimeColumns: 2,
  desktopSectionColumns: 3,
  mobileSectionColumns: 1,
} as const
