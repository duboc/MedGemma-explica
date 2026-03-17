export const API_BASE = import.meta.env.VITE_API_URL || "";

/**
 * Resolve a backend-relative image URL to an absolute URL.
 */
export function resolveImageUrl(url: string): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("blob:")) {
    return url;
  }
  return `${API_BASE}${url}`;
}

export async function fetchStructures() {
  const res = await fetch(`${API_BASE}/api/structures`);
  if (!res.ok) throw new Error("Failed to fetch structures");
  return res.json();
}

export async function fetchSamples() {
  const res = await fetch(`${API_BASE}/api/samples`);
  if (!res.ok) throw new Error("Failed to fetch samples");
  return res.json();
}

export async function analyzeImage(
  objectName: string,
  mock: boolean,
  file?: File,
  sampleId?: string
) {
  const formData = new FormData();
  formData.append("object_name", objectName);
  formData.append("mock", String(mock));
  if (file) {
    formData.append("file", file);
  } else if (sampleId) {
    formData.append("sample_id", sampleId);
  }

  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(error.detail || "Analysis failed");
  }
  return res.json();
}

export async function fetchAnalyses(limit = 20, mock = false) {
  const res = await fetch(`${API_BASE}/api/analyses?limit=${limit}&mock=${mock}`);
  if (!res.ok) throw new Error("Failed to fetch analyses");
  return res.json();
}

export async function fetchAnalysis(id: string, mock = false) {
  const res = await fetch(`${API_BASE}/api/analyses/${id}?mock=${mock}`);
  if (!res.ok) throw new Error("Analysis not found");
  return res.json();
}

export async function deleteAnalysis(id: string, mock = false) {
  const res = await fetch(`${API_BASE}/api/analyses/${id}?mock=${mock}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete analysis");
  return res.json();
}

export async function clearAllAnalyses(mock = false) {
  const res = await fetch(`${API_BASE}/api/analyses?mock=${mock}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to clear analyses");
  return res.json();
}

export async function updateAnalysis(
  id: string,
  fields: Record<string, unknown>,
  mock = false
) {
  const res = await fetch(`${API_BASE}/api/analyses/${id}?mock=${mock}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error("Failed to save");
  return res.json();
}

export function sampleImageUrl(filename: string) {
  return `${API_BASE}/sample-xrays/${filename}`;
}

export async function explainAnalysis(
  structureNames: string[],
  educationalInfos: object[],
  level: string,
  mock = false,
  imageUrl = ""
) {
  const res = await fetch(`${API_BASE}/api/explain`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      structure_names: structureNames,
      educational_infos: educationalInfos,
      level,
      mock,
      image_url: imageUrl,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Explain failed" }));
    throw new Error(error.detail || "Explain failed");
  }
  return res.json();
}

export async function chatWithGemini(
  messages: { role: string; content: string }[],
  structureNames: string[],
  educationalInfos: object[],
  mock = false,
  imageUrl = ""
) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      structure_names: structureNames,
      educational_infos: educationalInfos,
      mock,
      image_url: imageUrl,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Chat failed" }));
    throw new Error(error.detail || "Chat failed");
  }
  return res.json();
}

export async function generateFindingsReport(
  structureNames: string[],
  mock = false,
  imageUrl = ""
) {
  const res = await fetch(`${API_BASE}/api/findings-report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      structure_names: structureNames,
      mock,
      image_url: imageUrl,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Report failed" }));
    throw new Error(error.detail || "Failed to generate report");
  }
  return res.json();
}

export async function fetchStructureFindings(
  responseText: string,
  structureNames: string[],
  mock = false,
) {
  const res = await fetch(`${API_BASE}/api/structure-findings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      response_text: responseText,
      structure_names: structureNames,
      mock,
    }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Failed to extract findings" }));
    throw new Error(error.detail || "Failed to extract findings");
  }
  return res.json();
}

export async function suggestQuestions(
  structureNames: string[],
  educationalInfos: object[],
  mock = false,
  imageUrl = ""
) {
  const res = await fetch(`${API_BASE}/api/suggest-questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      structure_names: structureNames,
      educational_infos: educationalInfos,
      mock,
      image_url: imageUrl,
    }),
  });
  if (!res.ok) return null;
  return res.json();
}
