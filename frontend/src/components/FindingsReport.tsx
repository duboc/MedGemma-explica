import { useState } from "react";
import type { AnalysisResult } from "../types";
import { getStructureNames } from "../types";
import { generateFindingsReport } from "../hooks/useApi";

interface Props {
  result: AnalysisResult;
  mockMode: boolean;
  onSave?: (report: Report) => void;
}

interface Finding {
  structure: string;
  status: "normal" | "abnormal" | "borderline";
  finding: string;
  detail: string;
}

interface SystematicStep {
  step: string;
  checks: string[];
  observation: string;
}

interface PathologyScenario {
  condition: string;
  icon: string;
  current_status: string;
  what_would_change: string;
  key_signs: string[];
  teaching_point: string;
}

interface PearlCategory {
  category: string;
  icon: string;
  items: { title: string; detail: string }[];
}

interface Report {
  overall_assessment: {
    summary: string;
    findings: Finding[];
  };
  systematic_approach: SystematicStep[];
  pathology_scenarios: PathologyScenario[];
  clinical_pearls: PearlCategory[];
  disclaimer: string;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  normal: { label: "Normal", className: "fr-status--normal" },
  abnormal: { label: "Abnormal", className: "fr-status--abnormal" },
  borderline: { label: "Borderline", className: "fr-status--borderline" },
};

export default function FindingsReport({ result, mockMode, onSave }: Props) {
  const [report, setReport] = useState<Report | null>(
    (result.findings_report as Report | undefined) ?? null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["overall", "systematic", "pathology", "pearls"])
  );

  const structureNames = getStructureNames(result);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateFindingsReport(structureNames, mockMode, result.image_url);
      setReport(data);
      onSave?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const allKeys = ["overall", "systematic", "pathology", "pearls"];
  const expandAll = () => setExpandedSections(new Set(allKeys));
  const collapseAll = () => setExpandedSections(new Set());

  return (
    <div className="fr-panel">
      <div className="fr-header">
        <div>
          <h3>Comprehensive Findings Report</h3>
          <p className="fr-subtitle">
            MedGemma analyzes the X-ray, Gemini structures the findings
          </p>
        </div>
        <span className="rv-badge">MedGemma + Gemini</span>
      </div>

      {!report && !loading && (
        <div className="fr-intro">
          <div className="fr-intro-grid">
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1FA7A}"}</span>
              <span>Overall Assessment</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1F4CB}"}</span>
              <span>ABCDE Systematic Reading</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1F9EB}"}</span>
              <span>Pathology Scenarios</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1F4A1}"}</span>
              <span>Clinical Pearls</span>
            </div>
          </div>
          <button
            className="fr-generate-btn"
            onClick={handleGenerate}
            disabled={loading}
          >
            Generate Full Report
          </button>
        </div>
      )}

      {loading && !report && (
        <div className="fr-loading">
          <span className="spinner" />
          <p>Generating comprehensive report...</p>
          <p className="fr-loading-sub">MedGemma is analyzing the image, then Gemini structures the findings. This may take a minute.</p>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {report && (
        <div className="fr-report">
          <div className="fr-toolbar">
            <button className="fr-toolbar-btn" onClick={expandAll}>Expand All</button>
            <button className="fr-toolbar-btn" onClick={collapseAll}>Collapse All</button>
            <button
              className="fr-toolbar-btn fr-toolbar-btn--regen"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? "Regenerating..." : "Regenerate"}
            </button>
          </div>

          {/* Overall Assessment */}
          <SectionWrapper
            sectionKey="overall"
            icon={"\u{1FA7A}"}
            title="Overall Assessment"
            expanded={expandedSections.has("overall")}
            onToggle={toggleSection}
          >
            <p className="fr-summary">{report.overall_assessment.summary}</p>
            <div className="fr-findings-grid">
              {report.overall_assessment.findings.map((f, i) => {
                const cfg = STATUS_CONFIG[f.status] || STATUS_CONFIG.normal;
                return (
                  <div key={i} className="fr-finding-card">
                    <div className="fr-finding-header">
                      <span className="fr-finding-structure">{f.structure}</span>
                      <span className={`fr-status-badge ${cfg.className}`}>{cfg.label}</span>
                    </div>
                    <div className="fr-finding-text">{f.finding}</div>
                    <div className="fr-finding-detail">{f.detail}</div>
                  </div>
                );
              })}
            </div>
          </SectionWrapper>

          {/* Systematic Approach */}
          <SectionWrapper
            sectionKey="systematic"
            icon={"\u{1F4CB}"}
            title="Systematic Reading (ABCDE)"
            expanded={expandedSections.has("systematic")}
            onToggle={toggleSection}
          >
            <div className="fr-steps">
              {report.systematic_approach.map((step, i) => (
                <div key={i} className="fr-step-card">
                  <div className="fr-step-label">{step.step}</div>
                  <div className="fr-step-checks">
                    {step.checks.map((c, j) => (
                      <span key={j} className="fr-check-tag">{c}</span>
                    ))}
                  </div>
                  <div className="fr-step-observation">{step.observation}</div>
                </div>
              ))}
            </div>
          </SectionWrapper>

          {/* Pathology Scenarios */}
          <SectionWrapper
            sectionKey="pathology"
            icon={"\u{1F9EB}"}
            title="Pathology Scenarios"
            expanded={expandedSections.has("pathology")}
            onToggle={toggleSection}
          >
            <div className="fr-pathology-grid">
              {report.pathology_scenarios.map((p, i) => (
                <div key={i} className="fr-pathology-card">
                  <div className="fr-pathology-header">
                    <span className="fr-pathology-icon">{p.icon}</span>
                    <span className="fr-pathology-condition">{p.condition}</span>
                  </div>
                  <div className="fr-pathology-section">
                    <div className="fr-pathology-label">Current Status</div>
                    <p>{p.current_status}</p>
                  </div>
                  <div className="fr-pathology-section">
                    <div className="fr-pathology-label">What Would Change</div>
                    <p>{p.what_would_change}</p>
                  </div>
                  <div className="fr-pathology-section">
                    <div className="fr-pathology-label">Key Signs</div>
                    <ul className="fr-key-signs">
                      {p.key_signs.map((s, j) => (
                        <li key={j}>{s}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="fr-teaching-point">
                    <strong>Teaching Point:</strong> {p.teaching_point}
                  </div>
                </div>
              ))}
            </div>
          </SectionWrapper>

          {/* Clinical Pearls */}
          <SectionWrapper
            sectionKey="pearls"
            icon={"\u{1F4A1}"}
            title="Clinical Pearls & Pitfalls"
            expanded={expandedSections.has("pearls")}
            onToggle={toggleSection}
          >
            <div className="fr-pearls-grid">
              {report.clinical_pearls.map((cat, i) => (
                <div key={i} className="fr-pearl-category">
                  <div className="fr-pearl-cat-header">
                    <span>{cat.icon}</span>
                    <span>{cat.category}</span>
                  </div>
                  <div className="fr-pearl-items">
                    {cat.items.map((item, j) => (
                      <div key={j} className="fr-pearl-item">
                        <div className="fr-pearl-title">{item.title}</div>
                        <div className="fr-pearl-detail">{item.detail}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </SectionWrapper>

          <div className="dd-disclaimer">{report.disclaimer}</div>
        </div>
      )}
    </div>
  );
}

function SectionWrapper({
  sectionKey,
  icon,
  title,
  expanded,
  onToggle,
  children,
}: {
  sectionKey: string;
  icon: string;
  title: string;
  expanded: boolean;
  onToggle: (key: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className={`fr-section ${expanded ? "fr-section--expanded" : ""}`}>
      <button className="fr-section-header" onClick={() => onToggle(sectionKey)}>
        <span className="fr-section-icon">{icon}</span>
        <span className="fr-section-title">{title}</span>
        <span className="fr-section-chevron">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>
      {expanded && <div className="fr-section-body">{children}</div>}
    </div>
  );
}
