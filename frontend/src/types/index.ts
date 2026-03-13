export interface BoundingBox {
  box_2d: [number, number, number, number]; // [y0, x0, y1, x1] normalized 0-1000
  label: string;
}

export interface EducationalInfo {
  description: string;
  clinical_relevance: string;
}

export interface AnatomyStructure {
  name: string;
  description: string;
  clinical_relevance: string;
}

export interface SampleImage {
  id: string;
  name: string;
  filename: string;
  source: string;
  description: string;
  url: string;
}

export interface AnalysisResult {
  id: string;
  object_name: string;
  structure_names?: string[];
  response_text: string;
  bounding_boxes: BoundingBox[];
  image_url: string;
  image_width: number;
  image_height: number;
  educational_info: EducationalInfo;
  educational_infos?: EducationalInfo[];
  created_at?: string;
  mock?: boolean;
  // Persisted sub-results
  deep_dive?: { level: string; explanation: DeepDiveResult | string };
  findings_report?: Record<string, unknown>;
  structure_findings?: StructureFinding[];
  chat_messages?: ChatMessage[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// Deep Dive structured result
export interface DeepDiveKeyPoint {
  term: string;
  detail: string;
}

export interface DeepDiveComparison {
  structure: string;
  normal: string;
  abnormal_signs: string[];
  this_image: string;
}

export interface DeepDiveConnection {
  condition: string;
  relevance: string;
  what_to_look_for: string;
}

export interface DeepDiveTip {
  tip: string;
  why: string;
}

export interface DeepDiveSection {
  id: string;
  title: string;
  icon: string;
  content?: string;
  key_points?: DeepDiveKeyPoint[];
  comparisons?: DeepDiveComparison[];
  connections?: DeepDiveConnection[];
  tips?: DeepDiveTip[];
}

export interface DeepDiveResult {
  title: string;
  level: string;
  sections: DeepDiveSection[];
  disclaimer: string;
}

// Per-structure findings from Gemini Flash
export interface StructureFinding {
  name: string;
  appearance: string;
  status: "normal" | "abnormal" | "borderline";
  notable: string;
  clinical_note: string;
}

export function getStructureNames(result: AnalysisResult): string[] {
  return result.structure_names ?? [result.object_name];
}

export function getEducationalInfos(result: AnalysisResult): EducationalInfo[] {
  return result.educational_infos ?? [result.educational_info];
}
