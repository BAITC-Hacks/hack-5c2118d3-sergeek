import {
  mockCampaigns,
  mockDashboard,
  mockLimits,
  mockPilots,
  mockSimulation,
} from "../data/mockData";
import type {
  Campaign,
  Channel,
  DashboardData,
  DataLimits,
  Pilot,
  SimulationData,
} from "../types/api";

const apiBase = import.meta.env.VITE_API_URL ?? "";
type Source<T> = Promise<{ data: T; source: "api" | "demo" }>;

function humanizeTariff(value: string | null): string {
  return value ? value.replace(/^tariff_/, "Тариф ") : "Не указан";
}

function humanizeSegment(value: string | null): string {
  const labels: Record<string, string> = {
    LOW: "Низкий ARPU", MID: "Средний ARPU", HIGH: "Высокий ARPU",
  };
  return value ? labels[value] ?? value : "Не указан";
}

function channelLabel(value: string): string {
  return ({ Push: "Пуш", SMS: "SMS", "Digital ads": "Цифровая реклама", Call: "Звонок" } as Record<string, string>)[value] ?? value;
}

type ApiDashboard = {
  baseline_arpu: number;
  net_gain: number;
  total_cost: number;
  total_contacts: number;
  pilot_count: number;
  final_campaign_count: number;
  status: "PASS" | "FAIL";
  limits: {
    budget: number;
    contacts: number;
    pilots: number;
    campaigns: number;
    customers_per_campaign: number;
  };
  channels: Record<
    string,
    { cost_per_contact: number; conversion_multiplier: number }
  >;
  audience_size: number;
};

type ApiCampaign = {
  campaign_name: string;
  current_tariff: string | null;
  arpu_segment: string | null;
  target_tariff: string;
  channel: string;
  audience_size: number;
  communication_cost: number;
  gross_lift: number;
  net_gain: number;
  pilot_sample_size: number;
  observed_lift_ratio: number | null;
  standard_error: number | null;
  lower_bound: number | null;
  status: string;
};
type ApiPilot = {
  name: string;
  customers: number;
  observed_lift_ratio: number;
  standard_error: number;
  lower_bound: number;
  channel: string;
  cost: number;
};
type ApiSimulation = {
  seed_start: number;
  runs: number;
  positive_runs: number;
  median_net: number;
  min_net: number;
  max_net: number;
  values?: number[];
  source: string;
  is_mock: boolean;
};

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    signal: AbortSignal.timeout(path.endsWith("/run") ? 120_000 : 15_000),
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

function titleChannel(channel: string): Channel {
  const names: Record<string, Channel> = {
    push: "Push",
    sms: "SMS",
    digital_ads: "Digital ads",
    call: "Call",
  };
  return names[channel] ?? "Push";
}

function mapCampaign(item: ApiCampaign, index: number): Campaign {
  return {
    id: `C-${String(index + 1).padStart(2, "0")}`,
    name: `Предложение ${index + 1}`,
    currentTariff: humanizeTariff(item.current_tariff),
    arpuSegment: humanizeSegment(item.arpu_segment),
    targetTariff: humanizeTariff(item.target_tariff),
    channel: titleChannel(item.channel),
    audienceSize: item.audience_size,
    communicationCost: item.communication_cost,
    expectedGrossLift: item.gross_lift,
    expectedNetGain: item.net_gain,
    pilotSampleSize: item.pilot_sample_size,
    observedLiftRatio: item.observed_lift_ratio,
    standardError: item.standard_error,
    lowerBound: item.lower_bound,
    status: item.status === "selected" ? "Ready" : "Testing",
    rationale:
      "Кампания выбрана по результатам пилотов с учётом неопределённости, бюджета и пересечения аудиторий.",
  };
}

function mapSimulation(data: ApiSimulation): SimulationData {
  const values = data.values ?? [];
  const distribution = values.length
    ? buildDistribution(values)
    : [];
  return {
    profitableRuns: data.positive_runs,
    seedStart: data.seed_start,
    totalRuns: data.runs,
    medianNet: data.median_net,
    minimumNet: data.min_net,
    maximumNet: data.max_net,
    controlSeedNet: 2_702_002,
    distribution,
    comparison: [
      { name: "Минимум", value: data.min_net / 1_000_000 },
      {
        name: "Медиана",
        value: Number((data.median_net / 1_000_000).toFixed(2)),
      },
      { name: "Максимум", value: data.max_net / 1_000_000 },
    ],
    source: "api",
  };
}

function buildDistribution(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const size = Math.max((max - min) / 5, 1);
  return Array.from({ length: 5 }, (_, index) => {
    const floor = min + index * size;
    const ceiling = floor + size;
    return {
      bin: `${(floor / 1_000_000).toFixed(1).replace(".", ",")} млн`,
      count: values.filter((value) =>
        index === 4
          ? value >= floor && value <= ceiling
          : value >= floor && value < ceiling,
      ).length,
    };
  });
}

export const api = {
  dashboard: async (): Source<DashboardData> => {
    try {
      const [overview, campaignResponse] = await Promise.all([
        fetchApi<ApiDashboard>("/api/dashboard"),
        fetchApi<{ items: ApiCampaign[] }>("/api/campaigns"),
      ]);
      const mappedCampaigns = campaignResponse.items.map(mapCampaign);
      const channelBudget = Object.values(
        mappedCampaigns.reduce<Record<string, number>>(
          (totals, item) => ({
            ...totals,
            [item.channel]:
              (totals[item.channel] ?? 0) + item.communicationCost,
          }),
          {},
        ),
      ).length
        ? Object.entries(
            mappedCampaigns.reduce<Record<string, number>>(
              (totals, item) => ({
                ...totals,
                [item.channel]:
                  (totals[item.channel] ?? 0) + item.communicationCost,
              }),
              {},
            ),
          ).map(([name, value]) => ({ name: channelLabel(name), value }))
        : mockDashboard.channelBudget;
      return {
        source: "api",
        data: {
          baselineArpu: overview.baseline_arpu,
          campaignNetGain: overview.net_gain,
          budgetUsed: overview.total_cost,
          budgetLimit: overview.limits.budget,
          contactsUsed: overview.total_contacts,
          contactsLimit: overview.limits.contacts,
          pilotsUsed: overview.pilot_count,
          pilotsLimit: overview.limits.pilots,
          finalCampaigns: overview.final_campaign_count,
          finalCampaignLimit: overview.limits.campaigns,
          status: overview.status,
          channelBudget,
          campaignNet: mappedCampaigns.map((item) => ({
            name: item.name,
            value: Math.round(item.expectedNetGain / 1000),
          })),
          audienceCoverage: [
            { name: "Использовано контактов", value: overview.total_contacts },
            {
              name: "Осталось контактов",
              value: Math.max(
                0,
                overview.limits.contacts - overview.total_contacts,
              ),
            },
          ],
        },
      };
    } catch {
      return { data: mockDashboard, source: "demo" };
    }
  },
  campaigns: async (): Source<Campaign[]> => {
    try {
      const response = await fetchApi<{ items: ApiCampaign[] }>(
        "/api/campaigns",
      );
      return { data: response.items.map(mapCampaign), source: "api" };
    } catch {
      return { data: mockCampaigns, source: "demo" };
    }
  },
  pilots: async (): Source<Pilot[]> => {
    try {
      const response = await fetchApi<{ items: ApiPilot[] }>("/api/pilots");
      return {
        data: response.items.map((item, index) => ({
          id: `P-${String(index + 1).padStart(2, "0")}`,
          phase: index < 12 ? "Initial" : "Confirmation",
          title: `Пилот ${index + 1}`,
          audience: item.customers,
          result: `${(item.observed_lift_ratio * 100).toFixed(1).replace(".", ",")}% наблюдаемый эффект`,
          observedLiftRatio: item.observed_lift_ratio,
          standardError: item.standard_error,
          lowerBound: item.lower_bound,
          status: "Completed",
        })),
        source: "api",
      };
    } catch {
      return { data: mockPilots, source: "demo" };
    }
  },
  simulation: async (): Source<SimulationData> => {
    try {
      return {
        data: mapSimulation(
          await fetchApi<ApiSimulation>("/api/simulations/latest"),
        ),
        source: "api",
      };
    } catch {
      return { data: mockSimulation, source: "demo" };
    }
  },
  limits: async (): Source<DataLimits> => {
    try {
      const data = await fetchApi<ApiDashboard>("/api/dashboard");
      return {
        source: "api",
        data: {
          subscribers: data.audience_size,
          baselineArpu: data.baseline_arpu,
          budget: data.limits.budget,
          contacts: data.limits.contacts,
          pilots: data.limits.pilots,
          pilotSize: 200,
          finalCampaigns: data.limits.campaigns,
          campaignSize: data.limits.customers_per_campaign,
          channels: Object.entries(data.channels).map(([name, details]) => ({
            name: titleChannel(name),
            cost: details.cost_per_contact,
            multiplier: `${details.conversion_multiplier.toFixed(2)}×`,
          })),
        },
      };
    } catch {
      return { data: mockLimits, source: "demo" };
    }
  },
  runSimulation: async (seedStart: number): Source<SimulationData> => {
    try {
      return {
        data: mapSimulation(
          await fetchApi<ApiSimulation>("/api/simulations/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ runs: 10, seed_start: seedStart }),
          }),
        ),
        source: "api",
      };
    } catch {
      return { data: mockSimulation, source: "demo" };
    }
  },
};
