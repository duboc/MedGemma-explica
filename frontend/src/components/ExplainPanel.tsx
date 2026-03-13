import { useState } from "react";
import type { AnalysisResult, DeepDiveResult, DeepDiveSection } from "../types";
import { getStructureNames, getEducationalInfos } from "../types";
import { explainAnalysis } from "../hooks/useApi";

interface Props {
  result: AnalysisResult;
  mockMode: boolean;
  onSave?: (data: { level: string; explanation: DeepDiveResult }) => void;
}

const LEVELS = [
  { value: "pre_med", label: "Pre-Med" },
  { value: "medical_student", label: "Medical Student" },
  { value: "resident", label: "Resident" },
  { value: "attending", label: "Attending" },
];

const SECTION_ICONS: Record<string, string> = {
  eye: "\u{1F441}",
  balance: "\u{2696}",
  stethoscope: "\u{1FA7A}",
  lightbulb: "\u{1F4A1}",
  clipboard: "\u{1F4CB}",
};

function resolveSectionIcon(icon: string): string {
  return SECTION_ICONS[icon] || "\u{1F4CB}";
}

function isStructuredResult(val: unknown): val is DeepDiveResult {
  return typeof val === "object" && val !== null && "sections" in val;
}

export default function ExplainPanel({ result, mockMode, onSave }: Props) {
  const cached = result.deep_dive;
  const cachedExplanation = cached?.explanation;
  const initialResult = isStructuredResult(cachedExplanation) ? cachedExplanation : null;

  const [level, setLevel] = useState(cached?.level ?? "medical_student");
  const [deepDive, setDeepDive] = useState<DeepDiveResult | null>(initialResult);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["identification", "normal_vs_abnormal", "clinical_connections", "study_tips", "content"])
  );

  const structureNames = getStructureNames(result);
  const eduInfos = getEducationalInfos(result);

  const handleExplain = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await explainAnalysis(
        structureNames,
        eduInfos,
        level,
        mockMode,
        result.image_url
      );
      const data: DeepDiveResult = res.explanation;
      setDeepDive(data);
      onSave?.({ level, explanation: data });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate explanation");
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (id: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const expandAll = () => {
    if (deepDive) {
      setExpandedSections(new Set(deepDive.sections.map((s) => s.id)));
    }
  };
  const collapseAll = () => setExpandedSections(new Set());

  return (
    <div className="explain-panel">
      <div className="explain-header">
        <h3>MedGemma Deep Dive</h3>
        <span className="rv-badge">MedGemma + Gemini</span>
      </div>

      <div className="explain-controls">
        <label className="explain-level-label">Explanation level:</label>
        <div className="explain-level-buttons">
          {LEVELS.map((l) => (
            <button
              key={l.value}
              className={`explain-level-btn ${level === l.value ? "explain-level-btn--active" : ""}`}
              onClick={() => {
                setLevel(l.value);
                setDeepDive(null);
              }}
            >
              {l.label}
            </button>
          ))}
        </div>
        <button
          className="explain-generate-btn"
          onClick={handleExplain}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner" /> Analyzing with MedGemma...
            </>
          ) : deepDive ? (
            "Regenerate"
          ) : (
            "Generate Deep Dive"
          )}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {deepDive && (
        <div className="fr-report">
          {deepDive.title && (
            <div className="dd-title">{deepDive.title}</div>
          )}

          <div className="fr-toolbar">
            <button className="fr-toolbar-btn" onClick={expandAll}>Expand All</button>
            <button className="fr-toolbar-btn" onClick={collapseAll}>Collapse All</button>
          </div>

          {deepDive.sections.map((section) => (
            <SectionRenderer
              key={section.id}
              section={section}
              expanded={expandedSections.has(section.id)}
              onToggle={toggleSection}
            />
          ))}

          {deepDive.disclaimer && (
            <div className="dd-disclaimer">{deepDive.disclaimer}</div>
          )}
        </div>
      )}
    </div>
  );
}

function SectionRenderer({
  section,
  expanded,
  onToggle,
}: {
  section: DeepDiveSection;
  expanded: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <div className={`fr-section ${expanded ? "fr-section--expanded" : ""}`}>
      <button className="fr-section-header" onClick={() => onToggle(section.id)}>
        <span className="fr-section-icon">{resolveSectionIcon(section.icon)}</span>
        <span className="fr-section-title">{section.title}</span>
        <span className="fr-section-chevron">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>
      {expanded && (
        <div className="fr-section-body">
          {/* Content paragraph */}
          {section.content && (
            <p className="dd-section-content">{section.content}</p>
          )}

          {/* Key Points (identification section) */}
          {section.key_points && section.key_points.length > 0 && (
            <div className="dd-keypoints">
              {section.key_points.map((kp, i) => (
                <div key={i} className="dd-keypoint">
                  <div className="dd-keypoint-term">{kp.term}</div>
                  <div className="dd-keypoint-detail">{kp.detail}</div>
                </div>
              ))}
            </div>
          )}

          {/* Comparisons (normal vs abnormal section) */}
          {section.comparisons && section.comparisons.length > 0 && (
            <div className="dd-comparisons">
              {section.comparisons.map((comp, i) => (
                <div key={i} className="dd-comparison-card">
                  <div className="dd-comparison-header">{comp.structure}</div>
                  <div className="dd-comparison-row">
                    <div className="dd-comparison-col dd-comparison-col--normal">
                      <div className="dd-comparison-label">Normal</div>
                      <p>{comp.normal}</p>
                    </div>
                    <div className="dd-comparison-col dd-comparison-col--abnormal">
                      <div className="dd-comparison-label">Abnormal Signs</div>
                      <ul>
                        {comp.abnormal_signs.map((sign, j) => (
                          <li key={j}>{sign}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <div className="dd-comparison-this-image">
                    <strong>This Image:</strong> {comp.this_image}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Clinical Connections */}
          {section.connections && section.connections.length > 0 && (
            <div className="dd-connections">
              {section.connections.map((conn, i) => (
                <div key={i} className="dd-connection-card">
                  <div className="dd-connection-condition">{conn.condition}</div>
                  <p className="dd-connection-relevance">{conn.relevance}</p>
                  <div className="dd-connection-look-for">
                    <span className="dd-connection-look-label">Look for:</span>{" "}
                    {conn.what_to_look_for}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Study Tips */}
          {section.tips && section.tips.length > 0 && (
            <div className="dd-tips">
              {section.tips.map((t, i) => (
                <div key={i} className="dd-tip-card">
                  <div className="dd-tip-text">{t.tip}</div>
                  <div className="dd-tip-why">{t.why}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
