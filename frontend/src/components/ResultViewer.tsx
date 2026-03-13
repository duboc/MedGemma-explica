import { useCallback, useEffect, useRef, useState } from "react";
import type { AnalysisResult, StructureFinding } from "../types";
import { getStructureNames, getEducationalInfos } from "../types";
import { resolveImageUrl, updateAnalysis, fetchStructureFindings } from "../hooks/useApi";
import ChatPanel from "./ChatPanel";
import ExplainPanel from "./ExplainPanel";
import FindingsReport from "./FindingsReport";

type TabKey = "findings" | "report" | "explain" | "chat";

const TAB_CONFIG: { key: TabKey; label: string; icon: string; desc: string }[] = [
  { key: "findings", label: "Achados", icon: "\u{1F4CB}", desc: "Observações por estrutura" },
  { key: "report", label: "Relatório", icon: "\u{1F9EB}", desc: "Análise completa" },
  { key: "explain", label: "Deep Dive", icon: "\u{1F393}", desc: "Aprofundamento educacional" },
  { key: "chat", label: "Perguntas", icon: "\u{1F4AC}", desc: "Tire dúvidas" },
];

interface Props {
  result: AnalysisResult;
  mockMode: boolean;
  onResultUpdated?: (result: AnalysisResult) => void;
}

const BBOX_COLORS = [
  "#FF4444", "#44AAFF", "#44FF44", "#FFAA44",
  "#FF44FF", "#44FFFF", "#FFD700", "#FF6B9D",
];

export default function ResultViewer({ result, mockMode, onResultUpdated }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imageError, setImageError] = useState(false);
  const [activeTab, setActiveTab] = useState<TabKey>("findings");
  const [imageCollapsed, setImageCollapsed] = useState(false);

  useEffect(() => {
    setActiveTab("findings");
    setImageCollapsed(false);
  }, [result.id]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    setImageError(false);
    const img = new Image();
    img.crossOrigin = "anonymous";

    img.onerror = () => setImageError(true);
    img.onload = () => {
      const displayWidth = Math.min(500, img.naturalWidth);
      const scale = displayWidth / img.naturalWidth;
      const displayHeight = img.naturalHeight * scale;

      canvas.width = displayWidth;
      canvas.height = displayHeight;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(img, 0, 0, displayWidth, displayHeight);

      result.bounding_boxes.forEach((bbox, i) => {
        const [y0, x0, y1, x1] = bbox.box_2d;
        const color = BBOX_COLORS[i % BBOX_COLORS.length];

        const px0 = (x0 / 1000) * displayWidth;
        const py0 = (y0 / 1000) * displayHeight;
        const px1 = (x1 / 1000) * displayWidth;
        const py1 = (y1 / 1000) * displayHeight;

        ctx.fillStyle = color + "20";
        ctx.fillRect(px0, py0, px1 - px0, py1 - py0);

        ctx.strokeStyle = color;
        ctx.lineWidth = 3;
        ctx.strokeRect(px0, py0, px1 - px0, py1 - py0);

        const label = bbox.label;
        ctx.font = "bold 13px sans-serif";
        const textWidth = ctx.measureText(label).width;
        const labelY = py0 > 25 ? py0 - 6 : py0 + 18;
        const bgY = py0 > 25 ? py0 - 24 : py0 + 2;
        ctx.fillStyle = color;
        ctx.fillRect(px0, bgY, textWidth + 10, 22);
        ctx.fillStyle = "#fff";
        ctx.fillText(label, px0 + 5, labelY);
      });
    };

    img.src = resolveImageUrl(result.image_url);
  }, [result]);

  const eduInfos = getEducationalInfos(result);
  const structureNames = getStructureNames(result);

  const saveField = useCallback(
    (field: string, value: unknown) => {
      const updated = { ...result, [field]: value };
      onResultUpdated?.(updated);
      updateAnalysis(result.id, { [field]: value }, mockMode).catch(() => {});
    },
    [result, mockMode, onResultUpdated]
  );

  const hasSavedReport = !!result.findings_report;
  const hasSavedDive = !!result.deep_dive;
  const hasSavedChat = result.chat_messages && result.chat_messages.length > 0;
  const hasSavedFindings = result.structure_findings && result.structure_findings.length > 0;

  const savedMap: Record<TabKey, boolean> = {
    findings: !!hasSavedFindings,
    report: hasSavedReport,
    explain: hasSavedDive,
    chat: !!hasSavedChat,
  };

  return (
    <div className="rv">
      {/* Image reference strip */}
      <div className={`rv-image-strip ${imageCollapsed ? "rv-image-strip--collapsed" : ""}`}>
        <button
          className="rv-image-toggle"
          onClick={() => setImageCollapsed((c) => !c)}
          title={imageCollapsed ? "Mostrar Raio-X" : "Minimizar Raio-X"}
        >
          {imageCollapsed ? "\u{1F4F7} Mostrar Raio-X" : "\u25B2 Minimizar"}
        </button>

        {!imageCollapsed && (
          <div className="rv-image-area">
            {imageError ? (
              <div className="rv-image-error">Não foi possível carregar a imagem analisada.</div>
            ) : (
              <canvas ref={canvasRef} />
            )}
            {result.bounding_boxes.length > 0 && (
              <div className="rv-bbox-legend">
                {result.bounding_boxes.map((bbox, i) => (
                  <span key={i} className="rv-bbox-tag">
                    <span
                      className="rv-bbox-dot"
                      style={{ backgroundColor: BBOX_COLORS[i % BBOX_COLORS.length] }}
                    />
                    {bbox.label}
                  </span>
                ))}
              </div>
            )}
            {result.bounding_boxes.length === 0 && !imageError && (
              <p className="rv-warning">Nenhuma caixa delimitadora detectada.</p>
            )}
          </div>
        )}
      </div>

      {/* Tab navigation */}
      <div className="rv-tabs">
        {TAB_CONFIG.map((tab) => (
          <button
            key={tab.key}
            className={`rv-tab ${activeTab === tab.key ? "rv-tab--active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            <span className="rv-tab-icon">{tab.icon}</span>
            <span className="rv-tab-label">{tab.label}</span>
            {savedMap[tab.key] && <span className="rv-tab-dot" />}
          </button>
        ))}
      </div>

      {/* Tab content — full width, no height constraints */}
      <div className="rv-content">
        {activeTab === "findings" && (
          <FindingsTab
            result={result}
            mockMode={mockMode}
            structureNames={structureNames}
            eduInfos={eduInfos}
            onFindingsLoaded={(findings) => saveField("structure_findings", findings)}
          />
        )}

        {activeTab === "report" && (
          <FindingsReport
            result={result}
            mockMode={mockMode}
            onSave={(report) => saveField("findings_report", report)}
          />
        )}

        {activeTab === "explain" && (
          <ExplainPanel
            result={result}
            mockMode={mockMode}
            onSave={(dive) => saveField("deep_dive", dive)}
          />
        )}

        {activeTab === "chat" && (
          <ChatPanel
            result={result}
            mockMode={mockMode}
            onSave={(msgs) => saveField("chat_messages", msgs)}
          />
        )}
      </div>
    </div>
  );
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  normal: { label: "Normal", className: "sf-status--normal" },
  abnormal: { label: "Anormal", className: "sf-status--abnormal" },
  borderline: { label: "Limítrofe", className: "sf-status--borderline" },
};

function FindingsTab({
  result,
  mockMode,
  structureNames,
  eduInfos,
  onFindingsLoaded,
}: {
  result: AnalysisResult;
  mockMode: boolean;
  structureNames: string[];
  eduInfos: { description: string; clinical_relevance: string }[];
  onFindingsLoaded: (findings: StructureFinding[]) => void;
}) {
  const [findings, setFindings] = useState<StructureFinding[]>(
    result.structure_findings ?? []
  );
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (findings.length > 0) return;
    setLoading(true);
    fetchStructureFindings(result.response_text, structureNames, mockMode)
      .then((data) => {
        if (data?.findings?.length > 0) {
          setFindings(data.findings);
          onFindingsLoaded(data.findings);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [result.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="sf-panel">
      <div className="sf-header">
        <h3>Achados por Estrutura</h3>
        <span className="rv-badge">MedGemma + Gemini</span>
      </div>

      {loading && findings.length === 0 && (
        <div className="sf-loading">
          <span className="spinner" /> Extraindo achados da análise...
        </div>
      )}

      <div className="sf-grid">
        {findings.length > 0
          ? findings.map((f, i) => {
              const edu = eduInfos[i];
              const cfg = STATUS_CONFIG[f.status] || STATUS_CONFIG.normal;
              return (
                <div key={i} className="sf-card">
                  <div className="sf-card-header">
                    <span className="sf-card-name">{f.name}</span>
                    <span className={`rv-status-badge ${cfg.className}`}>{cfg.label}</span>
                  </div>
                  <div className="sf-card-body">
                    <p className="sf-appearance">{f.appearance}</p>
                    {f.notable && (
                      <div className="sf-notable">
                        <strong>Destaque:</strong> {f.notable}
                      </div>
                    )}
                    {edu && (
                      <div className="sf-edu">
                        <div className="sf-edu-col">
                          <span className="sf-edu-label">Anatomia</span>
                          <p>{edu.description}</p>
                        </div>
                        <div className="sf-edu-col">
                          <span className="sf-edu-label">Relevância Clínica</span>
                          <p>{f.clinical_note || edu.clinical_relevance}</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          : !loading &&
            eduInfos.map((info, i) => (
              <div key={i} className="sf-card">
                <div className="sf-card-header">
                  <span className="sf-card-name">{structureNames[i] ?? result.object_name}</span>
                </div>
                <div className="sf-card-body">
                  <div className="sf-edu">
                    <div className="sf-edu-col">
                      <span className="sf-edu-label">Anatomia</span>
                      <p>{info.description}</p>
                    </div>
                    <div className="sf-edu-col">
                      <span className="sf-edu-label">Relevância Clínica</span>
                      <p>{info.clinical_relevance}</p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
      </div>

      <details className="model-response">
        <summary>Raciocínio do Modelo</summary>
        <pre className="response-text">{result.response_text}</pre>
      </details>
    </div>
  );
}
