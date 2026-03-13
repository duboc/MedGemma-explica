import type { AnalysisResult } from "../types";
import { resolveImageUrl } from "../hooks/useApi";

interface Props {
  analyses: AnalysisResult[];
  onSelect: (analysis: AnalysisResult) => void;
  onDelete: (id: string) => void;
  onClearAll: () => void;
  activeId?: string;
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
        <h2>Analysis History</h2>
        <button className="history-clear-btn" onClick={onClearAll}>
          Clear All
        </button>
      </div>
      <div className="history-scroll">
        {analyses.map((a) => (
          <div
            key={a.id}
            className={`history-card ${activeId === a.id ? "history-card--active" : ""}`}
          >
            <button
              className="history-card-body"
              onClick={() => onSelect(a)}
            >
              <div className="history-card-thumb">
                <img
                  src={resolveImageUrl(a.image_url)}
                  alt={`X-ray: ${a.object_name}`}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              </div>
              <span className="history-card-label">{a.object_name}</span>
              <span className="history-card-date">
                {a.created_at
                  ? new Date(a.created_at).toLocaleString(undefined, {
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
              title="Delete this analysis"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
