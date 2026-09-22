/**
 * Health API — unversioned liveness/readiness probes (`/health*`).
 *
 * These sit outside `/api/v1`. The readiness probe returns 503 when a
 * dependency is degraded, and the payload still describes which check
 * failed, so the response body is parsed for both 200 and 503.
 */

const HEALTH_TIMEOUT_MS = 8_000;

export interface ReadinessCheck {
  name: string;
  status: "ok" | "degraded" | "down";
  detail?: string;
}

function origin(): string {
  const base = (import.meta.env.VITE_API_BASE_URL ??
    "http://localhost:8000/api/v1") as string;
  return base.replace(/\/+$/, "").replace(/\/api\/v\d+$/, "");
}

async function fetchJsonWithTimeout(
  url: string,
  timeoutMs = HEALTH_TIMEOUT_MS,
): Promise<{ status: number; body: unknown }> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json", "X-Request-ID": crypto.randomUUID() },
    });
    const body = await response.json().catch(() => null);
    return { status: response.status, body };
  } finally {
    window.clearTimeout(timeout);
  }
}

export const healthApi = {
  /** `GET /health` — liveness probe. */
  async liveness(): Promise<boolean> {
    try {
      const { status } = await fetchJsonWithTimeout(`${origin()}/health`);
      return status === 200;
    } catch {
      return false;
    }
  },

  /**
   * `GET /health/ready` — readiness probe.
   * Returns one entry per backend dependency (postgres, redis, …) plus the
   * configured LLM provider, so the admin overview shows the whole picture.
   */
  async readiness(): Promise<ReadinessCheck[]> {
    try {
      const { status, body } = await fetchJsonWithTimeout(
        `${origin()}/health/ready`,
      );
      const payload = (body ?? {}) as {
        status?: string;
        checks?: Record<string, string>;
      };
      const checks = payload.checks ?? {};
      const overall = status === 200 ? "ok" : "degraded";
      const entries = Object.entries(checks);
      const rows: ReadinessCheck[] = entries.length
        ? entries.map(([name, value]) => {
            const healthy =
              typeof value === "string" && value.startsWith("ok");
            return {
              name: name.charAt(0).toUpperCase() + name.slice(1),
              status: healthy ? "ok" : "down",
              detail: typeof value === "string" ? value : undefined,
            };
          })
        : [{ name: "API Services", status: overall }];
      // The LLM probe is separate (it can fail without taking the backend
      // down) and must never silence the dependency checks above.
      return [...rows, await this.llm()];
    } catch {
      return [{ name: "API Services", status: "down" }];
    }
  },

  /** `GET /health/llm` — can the backend reach the configured LLM provider? */
  async llm(): Promise<ReadinessCheck> {
    try {
      const { body } = await fetchJsonWithTimeout(`${origin()}/health/llm`);
      const payload = (body ?? {}) as {
        status?: string;
        provider?: string;
        base_url?: string;
        model?: string;
      };
      const healthy = payload.status === "healthy";
      return {
        name: "Ollama LLM",
        status: healthy ? "ok" : "down",
        detail: healthy
          ? payload.model
            ? `model: ${payload.model}`
            : payload.provider
          : "AI service unavailable",
      };
    } catch {
      return { name: "Ollama LLM", status: "down" };
    }
  },
};
