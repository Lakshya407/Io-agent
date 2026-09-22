/**
 * Health hooks — backend liveness and dependency readiness.
 */

import { useQuery } from "@tanstack/react-query";
import { healthApi } from "../api/health";

export function useReadiness() {
  return useQuery({
    queryKey: ["health", "ready"],
    queryFn: () => healthApi.readiness(),
    // Probes should stay fresh while the overview is open.
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}
