export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8080";

export async function fetchCtSamples() {
  const res = await fetch(`${API_BASE}/api/ct/samples`);
  if (!res.ok) throw new Error("Failed to fetch CT samples");
  return res.json();
}

export async function fetchCtFrames(
  seriesId: string,
  maxSlices = 30
): Promise<{ frames: string[]; total_instances: number; num_frames: number }> {
  const res = await fetch(
    `${API_BASE}/api/ct/frames/${seriesId}?max_slices=${maxSlices}`
  );
  if (!res.ok) throw new Error("Failed to fetch CT frames");
  return res.json();
}

export async function analyzeCtSeries(
  seriesId: string,
  query: string,
  mock: boolean
) {
  const res = await fetch(`${API_BASE}/api/ct/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ series_id: seriesId, query, mock }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "CT analysis failed" }));
    throw new Error(error.detail || "CT analysis failed");
  }
  return res.json();
}

export async function fetchCtAnalyses(limit = 20) {
  const res = await fetch(`${API_BASE}/api/ct/analyses?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch CT analyses");
  return res.json();
}

export async function fetchCtAnalysis(id: string) {
  const res = await fetch(`${API_BASE}/api/ct/analyses/${id}`);
  if (!res.ok) throw new Error("CT analysis not found");
  return res.json();
}

export async function deleteCtAnalysis(id: string) {
  const res = await fetch(`${API_BASE}/api/ct/analyses/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete CT analysis");
  return res.json();
}

export async function clearAllCtAnalyses() {
  const res = await fetch(`${API_BASE}/api/ct/analyses`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to clear CT analyses");
  return res.json();
}

export async function updateCtAnalysis(
  id: string,
  fields: Record<string, unknown>
) {
  const res = await fetch(`${API_BASE}/api/ct/analyses/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error("Failed to save");
  return res.json();
}

export async function explainCtAnalysis(
  seriesName: string,
  bodyPart: string,
  responseText: string,
  level: string,
  mock = false
) {
  const res = await fetch(`${API_BASE}/api/ct/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      series_name: seriesName,
      body_part: bodyPart,
      response_text: responseText,
      level,
      mock,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Explain failed" }));
    throw new Error(error.detail || "Explain failed");
  }
  return res.json();
}

export async function chatCtAnalysis(
  messages: { role: string; content: string }[],
  seriesName: string,
  bodyPart: string,
  responseText: string,
  mock = false
) {
  const res = await fetch(`${API_BASE}/api/ct/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      series_name: seriesName,
      body_part: bodyPart,
      response_text: responseText,
      mock,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Chat failed" }));
    throw new Error(error.detail || "Chat failed");
  }
  return res.json();
}

export async function suggestCtQuestions(bodyPart: string, mock = false) {
  const res = await fetch(`${API_BASE}/api/ct/suggest-questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body_part: bodyPart, mock }),
  });
  if (!res.ok) return null;
  return res.json();
}
