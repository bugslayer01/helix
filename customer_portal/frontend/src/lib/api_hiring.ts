const BASE = "/api/v1/hiring";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let body: any;
    try { body = await res.json(); } catch { body = {}; }
    throw new Error(body?.detail?.error?.message || res.statusText);
  }
  return res.json() as Promise<T>;
}

export interface Posting { id: string; title: string; created_at: number; jd_text?: string }

export async function listPostings(): Promise<{ postings: Posting[] }> { return call("/postings"); }

export async function createPosting(title: string, jd_text: string): Promise<{ posting_id: string; title: string }> {
  return call("/postings", { method: "POST", body: JSON.stringify({ title, jd_text }) });
}

export async function submitCandidate(postingId: string, params: { full_name: string; dob: string; email: string }, resume: File): Promise<any> {
  const fd = new FormData();
  fd.append("full_name", params.full_name);
  fd.append("dob", params.dob);
  fd.append("email", params.email);
  fd.append("resume", resume);
  const res = await fetch(`${BASE}/postings/${postingId}/candidates`, { method: "POST", body: fd });
  if (!res.ok) {
    let body: any;
    try { body = await res.json(); } catch { body = {}; }
    throw new Error(body?.detail?.error?.message || res.statusText);
  }
  return res.json();
}

export async function getHiringApplication(appId: string): Promise<any> {
  return call(`/applications/${appId}`);
}

export async function requestContestLink(appId: string): Promise<{ contest_url: string }> {
  return call(`/applications/${appId}/request-contest-link`, { method: "POST" });
}
