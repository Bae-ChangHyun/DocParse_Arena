const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface OcrModel {
  id: string;
  name: string;
  display_name: string;
  icon: string;
  provider: string;
  elo: number;
  wins: number;
  losses: number;
  total_battles: number;
  avg_latency_ms: number;
  is_active: boolean;
}

export interface BattleStartResponse {
  battle_id: string;
  document_url: string;
  model_a_label: string;
  model_b_label: string;
}

export interface VoteResponse {
  battle_id: string;
  winner: string;
  model_a: OcrModel;
  model_b: OcrModel;
  model_a_elo_change: number;
  model_b_elo_change: number;
}

export interface LeaderboardEntry {
  rank: number;
  id: string;
  name: string;
  display_name: string;
  icon: string;
  provider: string;
  elo: number;
  wins: number;
  losses: number;
  total_battles: number;
  win_rate: number;
  avg_latency_ms: number;
}

export interface HeadToHeadEntry {
  model_a_id: string;
  model_a_name: string;
  model_b_id: string;
  model_b_name: string;
  a_wins: number;
  b_wins: number;
  ties: number;
  total: number;
}

export interface DocumentInfo {
  name: string;
  path: string;
  extension: string;
}

export interface PlaygroundResponse {
  model_id: string;
  model_name: string;
  result: string;
  latency_ms: number;
}

export async function startBattle(file?: File, documentName?: string): Promise<BattleStartResponse> {
  const formData = new FormData();
  if (file) {
    formData.append("file", file);
  }
  if (documentName) {
    formData.append("document_name", documentName);
  }

  const params = new URLSearchParams();
  if (documentName && !file) {
    params.set("document_name", documentName);
  }

  const res = await fetch(`${API_BASE}/api/battle/start${!file && documentName ? `?document_name=${encodeURIComponent(documentName)}` : ""}`, {
    method: "POST",
    body: file ? formData : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function streamBattle(battleId: string, onEvent: (event: string, data: unknown) => void): EventSource {
  const es = new EventSource(`${API_BASE}/api/battle/${battleId}/stream`);

  es.addEventListener("model_a_result", (e) => {
    onEvent("model_a_result", JSON.parse(e.data));
  });
  es.addEventListener("model_b_result", (e) => {
    onEvent("model_b_result", JSON.parse(e.data));
  });
  es.addEventListener("done", () => {
    onEvent("done", {});
    es.close();
  });
  es.onerror = () => {
    onEvent("error", { error: "Connection lost" });
    es.close();
  };

  return es;
}

export async function voteBattle(battleId: string, winner: string): Promise<VoteResponse> {
  const res = await fetch(`${API_BASE}/api/battle/${battleId}/vote`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ winner }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  const res = await fetch(`${API_BASE}/api/leaderboard`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getHeadToHead(): Promise<HeadToHeadEntry[]> {
  const res = await fetch(`${API_BASE}/api/leaderboard/head-to-head`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getRandomDocument(): Promise<{ url: string; name: string }> {
  const res = await fetch(`${API_BASE}/api/documents/random`);
  if (!res.ok) throw new Error(await res.text());
  const name = res.headers.get("X-Document-Name") || "random";
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  return { url, name };
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_BASE}/api/documents/list`);
  if (!res.ok) throw new Error(await res.text());
  const data = await res.json();
  return data.documents;
}

export async function getModels(): Promise<OcrModel[]> {
  const res = await fetch(`${API_BASE}/api/playground/models`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function runPlaygroundOcr(modelId: string, file?: File, documentName?: string): Promise<PlaygroundResponse> {
  const formData = new FormData();
  formData.append("model_id", modelId);
  if (file) {
    formData.append("file", file);
  }
  if (documentName) {
    formData.append("document_name", documentName);
  }
  const res = await fetch(`${API_BASE}/api/playground/ocr`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getDocumentUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export function getApiBase(): string {
  return API_BASE;
}
