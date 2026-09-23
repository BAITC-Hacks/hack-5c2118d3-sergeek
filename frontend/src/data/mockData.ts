import type { Campaign, DashboardData, DataLimits, Pilot, SimulationData } from '../types/api'

export const mockDashboard: DashboardData = {
  baselineArpu: 150_641_084, campaignNetGain: 3_630_000, budgetUsed: 71_840, budgetLimit: 100_000,
  contactsUsed: 8_940, contactsLimit: 15_000, pilotsUsed: 14, pilotsLimit: 20, finalCampaigns: 5, finalCampaignLimit: 10, status: 'PASS',
  channelBudget: [{ name: 'Push', value: 8_640 }, { name: 'SMS', value: 31_200 }, { name: 'Digital ads', value: 32_000 }],
  campaignNet: [{ name: 'Family', value: 980 }, { name: 'Weekend', value: 760 }, { name: 'Mega', value: 710 }, { name: 'Comfort', value: 640 }, { name: 'More', value: 540 }],
  audienceCoverage: [{ name: 'Reached', value: 8_940 }, { name: 'Remaining', value: 6_060 }],
}

export const mockCampaigns: Campaign[] = [
  { id: 'C-01', name: 'Family upgrade', currentTariff: 'All inclusive', arpuSegment: 'High ARPU', targetTariff: 'Premium Family', channel: 'SMS', audienceSize: 1_240, communicationCost: 24_800, expectedGrossLift: 1_260_000, expectedNetGain: 980_000, confidence: 'High', status: 'Ready', rationale: 'The confirmation cohort shows a stable lower confidence bound above zero.' },
  { id: 'C-02', name: 'Weekend data', currentTariff: 'Start', arpuSegment: 'Mid ARPU', targetTariff: 'Weekend 5 990', channel: 'Push', audienceSize: 3_180, communicationCost: 0, expectedGrossLift: 760_000, expectedNetGain: 760_000, confidence: 'High', status: 'Ready', rationale: 'High-data behaviour makes the larger bundle relevant at a zero-cost channel.' },
  { id: 'C-03', name: 'Mega data', currentTariff: 'Internet+', arpuSegment: 'Mid ARPU', targetTariff: 'Mega 7 999', channel: 'Digital ads', audienceSize: 860, communicationCost: 17_200, expectedGrossLift: 727_000, expectedNetGain: 710_000, confidence: 'Medium', status: 'Ready', rationale: 'Digital ads outperformed push for this visual, data-heavy proposition.' },
  { id: 'C-04', name: 'Comfort step-up', currentTariff: 'Comfort Lite', arpuSegment: 'Low ARPU', targetTariff: 'Comfort', channel: 'Digital ads', audienceSize: 1_440, communicationCost: 14_800, expectedGrossLift: 655_000, expectedNetGain: 640_000, confidence: 'Medium', status: 'Ready', rationale: 'A controlled pilot produced a positive weighted mean after channel costs.' },
  { id: 'C-05', name: 'More minutes', currentTariff: 'Start', arpuSegment: 'Low ARPU', targetTariff: 'More 4 990', channel: 'SMS', audienceSize: 2_220, communicationCost: 6_400, expectedGrossLift: 546_000, expectedNetGain: 540_000, confidence: 'Testing', status: 'Testing', rationale: 'Initial effect is positive; one final confirmation pilot is in progress.' },
]

export const mockPilots: Pilot[] = [
  { id: 'P-01', phase: 'Initial', title: 'Family upgrade', audience: 120, result: '+18.4% net lift', confidence: 94, status: 'Completed' },
  { id: 'P-02', phase: 'Initial', title: 'Weekend data', audience: 120, result: '+13.1% net lift', confidence: 91, status: 'Completed' },
  { id: 'P-09', phase: 'Initial', title: 'Mega data', audience: 120, result: '+9.6% net lift', confidence: 78, status: 'Completed' },
  { id: 'P-11', phase: 'Confirmation', title: 'Family upgrade', audience: 200, result: 'Confirmed', confidence: 96, status: 'Completed' },
  { id: 'P-14', phase: 'Confirmation', title: 'More minutes', audience: 200, result: 'Collecting', confidence: 62, status: 'Running' },
]

export const mockSimulation: SimulationData = {
  profitableRuns: 100, totalRuns: 100, medianNet: 3_630_000, minimumNet: 2_020_000, maximumNet: 4_110_000, controlSeedNet: 2_580_000,
  distribution: [{ bin: '2.0m', count: 4 }, { bin: '2.5m', count: 18 }, { bin: '3.0m', count: 31 }, { bin: '3.5m', count: 29 }, { bin: '4.0m', count: 18 }],
  comparison: [{ name: 'Push-only', value: 2.58 }, { name: 'Channel-optimized', value: 3.63 }], source: 'demo',
}

export const mockLimits: DataLimits = {
  subscribers: 23_441, baselineArpu: 150_641_084, budget: 100_000, contacts: 15_000, pilots: 20, pilotSize: 200, finalCampaigns: 10, campaignSize: 5_000,
  channels: [{ name: 'Push', cost: 0, multiplier: '1.00×' }, { name: 'SMS', cost: 20, multiplier: '1.16×' }, { name: 'Digital ads', cost: 20, multiplier: '1.22×' }, { name: 'Call', cost: 180, multiplier: '1.38×' }],
}
