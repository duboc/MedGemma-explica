import type { AnalysisResult } from "../types";
import { resolveImageUrl } from "../hooks/useApi";

interface Props {
  analyses: AnalysisResult[];
  onSelect: (analysis: AnalysisResult) => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
  activeId?: string;
}

const CONTENT_INDICATORS: {
  key: keyof AnalysisResult;
  label: string;
  icon: string;
}[] = [
  { key: "structure_findings", label: "Achados", icon: "\u{1F4CB}" },
  { key: "findings_report", label: "Relatório", icon: "\u{1F9EB}" },
  { key: "deep_dive", label: "Deep Dive", icon: "\u{1F393}" },
  { key: "chat_messages", label: "Chat", icon: "\u{1F4AC}" },
];

function hasContent(analysis: AnalysisResult, key: keyof AnalysisResult): boolean {
  const val = analysis[key];
  if (!val) return false;
  if (Array.isArray(val)) return val.length > 0;
  return true;
}

export default function HistoryPanel({
  analyses,
  onSelect,
  onDelete,
  onClearAll,
  activeId,
}: Props) {
  if (analyses.length === 0) return null;

  return (
    <div className="history-bar">
      <div className="history-header">
        <h2>Histórico de Análises</h2>
        <button className="history-clear-btn" onClick={onClearAll}>
          Limpar Tudo
        </button>
      </div>
      <div className="history-scroll">
        {analyses.map((a) => {
          const savedCount = CONTENT_INDICATORS.filter((ci) =>
            hasContent(a, ci.key)
          ).length;
          return (
            <div
              key={a.id}
              className={`history-card ${activeId === a.id ? "history-card--active" : ""}`}
            >
              <button
                className="history-card-body"
                onClick={() => onSelect(a)}
              >
                <div className="history-card-thumb">
                  {a.image_url ? (
                    <img
                      src={resolveImageUrl(a.image_url)}
                      alt={a.object_name}
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : (
                    <span className="history-card-thumb-icon">{"\u{1FA7B}"}</span>
                  )}
                </div>
                <span className="history-card-label">{a.object_name}</span>
                {savedCount > 0 && (
                  <span className="history-card-indicators">
                    {CONTENT_INDICATORS.map(
                      (ci) =>
                        hasContent(a, ci.key) && (
                          <span
                            key={ci.key}
                            className="history-card-indicator"
                            title={ci.label}
                          >
                            {ci.icon}
                          </span>
                        )
                    )}
                  </span>
                )}
                <span className="history-card-date">
                  {(a.updated_at || a.created_at)
                    ? new Date(a.updated_at || a.created_at!).toLocaleString("pt-BR", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : ""}
                </span>
              </button>
              <button
                className="history-card-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(a.id);
                }}
                title="Excluir esta análise"
              >
                &times;
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
