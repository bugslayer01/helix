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

// Multipart helper: do NOT set Content-Type — the browser needs to pick the boundary.
async function callMultipart<T>(path: string, fd: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: fd });
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

export interface StartApplicationBody {
  full_name: string;
  dob: string;
  email: string;
  phone?: string;
  amount: number;
  purpose?: string;
}

export async function startApplication(body: StartApplicationBody): Promise<{ application_id: string; applicant_id: string; status: string }> {
  return call("/applications", { method: "POST", body: JSON.stringify(body) });
}

export async function uploadIntakeDoc(
  appId: string,
  docType: string,
  file: File,
): Promise<{ document_id: string; doc_type: string; sha256: string; extracted: any; source?: string; confidence?: number }> {
  const fd = new FormData();
  fd.append("doc_type", docType);
  fd.append("file", file);
  return callMultipart(`/applications/${appId}/documents`, fd);
}

export async function submitApplication(appId: string): Promise<any> {
  return call(`/applications/${appId}/submit`, { method: "POST" });
}
