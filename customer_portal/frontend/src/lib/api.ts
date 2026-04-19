const BASE = "/api/v1";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail: any;
    try {
      detail = await res.json();
    } catch {
      detail = { error: { message: res.statusText } };
    }
    throw new Error(detail?.detail?.error?.message || detail?.error?.message || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function requestContestLink(appId: string): Promise<{ contest_url: string; jti: string; expires_in_hours: number }> {
  return call(`/applications/${appId}/request-contest-link`, { method: "POST" });
}

export async function listOperatorCases(): Promise<{ cases: any[] }> {
  return call("/operator/cases");
}

export async function getOperatorCase(appId: string): Promise<any> {
  return call(`/operator/cases/${appId}`);
}
