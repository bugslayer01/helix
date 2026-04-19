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

export interface ApplicationStart {
  full_name: string;
  dob: string;
  email: string;
  phone?: string;
  amount: number;
  purpose?: string;
}

export interface StartResponse {
  application_id: string;
  applicant_id: string;
  status: string;
}

export async function startApplication(req: ApplicationStart): Promise<StartResponse> {
  return call("/applications", { method: "POST", body: JSON.stringify(req) });
}

export async function uploadDocument(
  appId: string,
  docType: string,
  file: File,
): Promise<{ document_id: string; doc_type: string; sha256: string; extracted: Record<string, unknown>; source: string; confidence: number }> {
  const fd = new FormData();
  fd.append("doc_type", docType);
  fd.append("file", file);
  const res = await fetch(`${BASE}/applications/${appId}/documents`, { method: "POST", body: fd });
  if (!res.ok) {
    let detail: any;
    try { detail = await res.json(); } catch { detail = { error: { message: res.statusText } }; }
    throw new Error(detail?.detail?.error?.message || res.statusText);
  }
  return res.json();
}

export async function submitApplication(appId: string): Promise<any> {
  return call(`/applications/${appId}/submit`, { method: "POST" });
}

export async function getApplication(appId: string): Promise<any> {
  return call(`/applications/${appId}`);
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
