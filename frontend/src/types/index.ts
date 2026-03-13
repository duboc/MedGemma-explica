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
  updated_at?: string;
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

// CT Scan types
export interface CTSampleSeries {
  id: string;
  name: string;
  description: string;
  body_part: string;
  num_slices: number;
  default_query?: string;
}

export interface CTAnalysisResult {
  id: string;
  series_id: string;
  series_name: string;
  body_part: string;
  query: string;
  response_text: string;
  num_slices: number;
  created_at?: string;
  updated_at?: string;
  mock?: boolean;
  deep_dive?: { level: string; explanation: DeepDiveResult | string };
  ct_report?: CTReport;
  chat_messages?: ChatMessage[];
}

// CT structured report types
export interface CTTecnica {
  tipo_exame: string;
  plano: string;
  espessura: string;
  contraste: string;
  observacoes: string;
}

export interface CTSubitem {
  estrutura: string;
  achado: string;
  medidas: string;
  relevancia: "alta" | "media" | "baixa";
}

export interface CTAchado {
  regiao: string;
  status: "normal" | "alterado" | "inconclusivo";
  descricao: string;
  subitens: CTSubitem[];
}

export interface CTImpressao {
  numero: number;
  descricao: string;
  gravidade: "critico" | "importante" | "menor" | "normal";
}

export interface CTDiferencial {
  achado: string;
  opcoes: string[];
}

export interface CTRecomendacao {
  tipo: "exame" | "acompanhamento" | "encaminhamento" | "laboratorio";
  descricao: string;
  urgencia: "imediata" | "breve" | "eletiva";
}

export interface CTReport {
  tecnica: CTTecnica;
  achados: CTAchado[];
  impressao: CTImpressao[];
  diferenciais: CTDiferencial[];
  recomendacoes: CTRecomendacao[];
  disclaimer: string;
}

export function getStructureNames(result: AnalysisResult): string[] {
  return result.structure_names ?? [result.object_name];
}

export function getEducationalInfos(result: AnalysisResult): EducationalInfo[] {
  return result.educational_infos ?? [result.educational_info];
}
