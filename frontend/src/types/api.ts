export type Channel = "Push" | "SMS" | "Digital ads" | "Call";
export type Confidence = "High" | "Medium" | "Testing";

export interface Campaign {
  id: string;
  name: string;
  currentTariff: string;
  arpuSegment: string;
  targetTariff: string;
  channel: Channel;
  audienceSize: number;
  communicationCost: number;
  expectedGrossLift: number;
  expectedNetGain: number;
  confidence: Confidence;
  status: "Ready" | "Testing";
  rationale: string;
}

export interface DashboardData {
  baselineArpu: number;
  campaignNetGain: number;
  budgetUsed: number;
  budgetLimit: number;
  contactsUsed: number;
  contactsLimit: number;
  pilotsUsed: number;
  pilotsLimit: number;
  finalCampaigns: number;
  finalCampaignLimit: number;
  status: "PASS" | "FAIL";
  channelBudget: { name: string; value: number }[];
  campaignNet: { name: string; value: number }[];
  audienceCoverage: { name: string; value: number }[];
}

export interface Pilot {
  id: string;
  phase: "Initial" | "Confirmation";
  title: string;
  audience: number;
  result: string;
  confidence: number;
  status: "Completed" | "Running";
}

export interface SimulationData {
  profitableRuns: number;
  totalRuns: number;
  medianNet: number;
  minimumNet: number;
  maximumNet: number;
  controlSeedNet: number;
  distribution: { bin: string; count: number }[];
  comparison: { name: string; value: number }[];
  source: "api" | "demo";
}

export interface DataLimits {
  subscribers: number;
  baselineArpu: number;
  budget: number;
  contacts: number;
  pilots: number;
  pilotSize: number;
  finalCampaigns: number;
  campaignSize: number;
  channels: { name: Channel; cost: number; multiplier: string }[];
}
