export type User = {
  id: number
  username: string
  role: string
  display_name: string
}

export type Hatchery = {
  id: number
  name: string
  seawaterSource: string
  notes?: string | null
}

export type Pond = {
  id: number
  hatcheryId: number
  pondCode: string
  species: string
  volumeM3: number
  status: 'stocked' | 'dry' | 'quarantine'
  waterChanging?: boolean
}

export type WaterSample = {
  id: number
  pondId: number
  sampledAt: string
  tempC: number | null
  salinityPpt: number
  doMgL: number | null
  ph: number | null
  notes?: string | null
}

export type FeedEvent = {
  id: number
  pondId: number
  fedAt: string
  feedType: string
  amountKg: number
  operatorName: string
}

export type WaterChangeStroke = {
  id: number
  pondId: number
  outflowM3: number
  inflowM3: number
  startAt: string
  endAt: string | null
  operatorName: string
  note?: string | null
  closingSampleId?: number | null
}

export type DashboardStats = {
  pondTotal: number
  quarantineCount: number
  samplesLast24h: number
  feedKgLast7d: number
}
