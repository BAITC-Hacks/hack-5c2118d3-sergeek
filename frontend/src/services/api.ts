import { mockCampaigns, mockDashboard, mockLimits, mockPilots, mockSimulation } from '../data/mockData'
import type { Campaign, DashboardData, DataLimits, Pilot, SimulationData } from '../types/api'

const apiBase = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, fallback: T, init?: RequestInit): Promise<{ data: T; source: 'api' | 'demo' }> {
  try {
    const response = await fetch(`${apiBase}${path}`, init)
    if (!response.ok) throw new Error(`Request failed: ${response.status}`)
    return { data: await response.json() as T, source: 'api' }
  } catch {
    return { data: fallback, source: 'demo' }
  }
}

export const api = {
  dashboard: () => request<DashboardData>('/api/dashboard', mockDashboard),
  campaigns: () => request<Campaign[]>('/api/campaigns', mockCampaigns),
  pilots: () => request<Pilot[]>('/api/pilots', mockPilots),
  simulation: () => request<SimulationData>('/api/simulations/latest', mockSimulation),
  limits: () => request<DataLimits>('/api/dashboard/limits', mockLimits),
  runSimulation: () => request<SimulationData>('/api/simulations/run', mockSimulation, { method: 'POST' }),
}
