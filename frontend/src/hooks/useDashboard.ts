import { useEffect, useState } from "react";
import { api } from "../services/api";
import type {
  Campaign,
  DashboardData,
  DataLimits,
  Pilot,
  SimulationData,
} from "../types/api";

export function useDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData>();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [pilots, setPilots] = useState<Pilot[]>([]);
  const [simulation, setSimulation] = useState<SimulationData>();
  const [limits, setLimits] = useState<DataLimits>();
  const [isDemo, setIsDemo] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.dashboard(),
      api.campaigns(),
      api.pilots(),
      api.simulation(),
      api.limits(),
    ]).then(([overview, portfolio, pilotData, simulationData, limitsData]) => {
      setDashboard(overview.data);
      setCampaigns(portfolio.data);
      setPilots(pilotData.data);
      setSimulation(simulationData.data);
      setLimits(limitsData.data);
      setIsDemo(
        [overview, portfolio, pilotData, simulationData, limitsData].some(
          (result) => result.source === "demo",
        ),
      );
      setIsLoading(false);
    });
  }, []);

  return {
    dashboard,
    campaigns,
    pilots,
    simulation,
    limits,
    isDemo,
    isLoading,
    runSimulation: api.runSimulation,
  };
}
