import { useState } from "react";
import type { CTAnalysisResult, CTReport, CTAchado, CTImpressao, CTRecomendacao } from "../types";
import { parseCtReport } from "../hooks/useCtApi";

interface Props {
  result: CTAnalysisResult;
  mockMode: boolean;
  onSave?: (report: CTReport) => void;
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  normal: { label: "Normal", className: "fr-status--normal" },
  alterado: { label: "Alterado", className: "fr-status--abnormal" },
  inconclusivo: { label: "Inconclusivo", className: "fr-status--borderline" },
};

const GRAVIDADE_CONFIG: Record<string, { label: string; className: string }> = {
  critico: { label: "Critico", className: "ct-grav--critico" },
  importante: { label: "Importante", className: "ct-grav--importante" },
  menor: { label: "Menor", className: "ct-grav--menor" },
  normal: { label: "Normal", className: "ct-grav--normal" },
};

const URGENCIA_CONFIG: Record<string, { label: string; className: string }> = {
  imediata: { label: "Imediata", className: "ct-urg--imediata" },
  breve: { label: "Breve", className: "ct-urg--breve" },
  eletiva: { label: "Eletiva", className: "ct-urg--eletiva" },
};

const TIPO_ICONS: Record<string, string> = {
  exame: "\u{1FA7A}",
  acompanhamento: "\u{1F4CB}",
  encaminhamento: "\u{1F3E5}",
  laboratorio: "\u{1F9EA}",
};

const RELEVANCIA_DOTS: Record<string, string> = {
  alta: "\u{1F534}",
  media: "\u{1F7E1}",
  baixa: "\u{1F7E2}",
};

export default function CTFindingsReport({ result, mockMode, onSave }: Props) {
  const savedReport = (result as CTAnalysisResult & { ct_report?: CTReport }).ct_report;
  const [report, setReport] = useState<CTReport | null>(savedReport ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["tecnica", "achados", "impressao", "diferenciais", "recomendacoes"])
  );

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await parseCtReport(result.response_text, result.body_part, mockMode);
      setReport(data);
      onSave?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao gerar laudo estruturado");
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

  const allKeys = ["tecnica", "achados", "impressao", "diferenciais", "recomendacoes"];
  const expandAll = () => setExpandedSections(new Set(allKeys));
  const collapseAll = () => setExpandedSections(new Set());

  return (
    <div className="fr-panel">
      <div className="fr-header">
        <div>
          <h3>Laudo Estruturado</h3>
          <p className="fr-subtitle">
            MedGemma analisa a TC, Gemini estrutura o laudo
          </p>
        </div>
        <span className="rv-badge">MedGemma + Gemini</span>
      </div>

      {!report && !loading && (
        <div className="fr-intro">
          <div className="fr-intro-grid">
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{2699}"}</span>
              <span>Tecnica</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1FA7A}"}</span>
              <span>Achados por Regiao</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1F4CB}"}</span>
              <span>Impressao Diagnostica</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1F9EB}"}</span>
              <span>Diferenciais</span>
            </div>
            <div className="fr-intro-item">
              <span className="fr-intro-icon">{"\u{1F4A1}"}</span>
              <span>Recomendacoes</span>
            </div>
          </div>
          <button className="fr-generate-btn" onClick={handleGenerate} disabled={loading}>
            Gerar Laudo Estruturado
          </button>
        </div>
      )}

      {loading && !report && (
        <div className="fr-loading">
          <span className="spinner" />
          <p>Gerando laudo estruturado...</p>
          <p className="fr-loading-sub">
            Gemini esta estruturando a analise do MedGemma em formato de laudo. Isso pode levar alguns segundos.
          </p>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {report && (
        <div className="fr-report">
          <div className="fr-toolbar">
            <button className="fr-toolbar-btn" onClick={expandAll}>Expandir Tudo</button>
            <button className="fr-toolbar-btn" onClick={collapseAll}>Recolher Tudo</button>
            <button
              className="fr-toolbar-btn fr-toolbar-btn--regen"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? "Regenerando..." : "Regenerar"}
            </button>
          </div>

          {/* Tecnica */}
          <SectionWrapper
            sectionKey="tecnica"
            icon={"\u{2699}"}
            title="Tecnica"
            expanded={expandedSections.has("tecnica")}
            onToggle={toggleSection}
          >
            <div className="ct-tecnica-grid">
              <TecnicaField label="Tipo de Exame" value={report.tecnica.tipo_exame} />
              <TecnicaField label="Plano" value={report.tecnica.plano} />
              <TecnicaField label="Espessura" value={report.tecnica.espessura} />
              <TecnicaField label="Contraste" value={report.tecnica.contraste} />
              {report.tecnica.observacoes && (
                <TecnicaField label="Observacoes" value={report.tecnica.observacoes} />
              )}
            </div>
          </SectionWrapper>

          {/* Achados */}
          <SectionWrapper
            sectionKey="achados"
            icon={"\u{1FA7A}"}
            title="Achados por Regiao"
            expanded={expandedSections.has("achados")}
            onToggle={toggleSection}
            badge={`${report.achados.length} regioes`}
          >
            <div className="ct-achados-list">
              {report.achados.map((achado, i) => (
                <AchadoCard key={i} achado={achado} />
              ))}
            </div>
          </SectionWrapper>

          {/* Impressao */}
          <SectionWrapper
            sectionKey="impressao"
            icon={"\u{1F4CB}"}
            title="Impressao Diagnostica"
            expanded={expandedSections.has("impressao")}
            onToggle={toggleSection}
          >
            <div className="ct-impressao-list">
              {report.impressao.map((imp, i) => (
                <ImpressaoItem key={i} impressao={imp} />
              ))}
            </div>
          </SectionWrapper>

          {/* Diferenciais */}
          {report.diferenciais.length > 0 && (
            <SectionWrapper
              sectionKey="diferenciais"
              icon={"\u{1F9EB}"}
              title="Diagnosticos Diferenciais"
              expanded={expandedSections.has("diferenciais")}
              onToggle={toggleSection}
            >
              <div className="ct-diferenciais-grid">
                {report.diferenciais.map((dif, i) => (
                  <div key={i} className="ct-diferencial-card">
                    <div className="ct-diferencial-achado">{dif.achado}</div>
                    <ul className="ct-diferencial-opcoes">
                      {dif.opcoes.map((op, j) => (
                        <li key={j}>{op}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </SectionWrapper>
          )}

          {/* Recomendacoes */}
          <SectionWrapper
            sectionKey="recomendacoes"
            icon={"\u{1F4A1}"}
            title="Recomendacoes"
            expanded={expandedSections.has("recomendacoes")}
            onToggle={toggleSection}
          >
            <div className="ct-recomendacoes-list">
              {report.recomendacoes.map((rec, i) => (
                <RecomendacaoItem key={i} rec={rec} />
              ))}
            </div>
          </SectionWrapper>

          <div className="dd-disclaimer">{report.disclaimer}</div>
        </div>
      )}
    </div>
  );
}

// === Sub-components ===

function TecnicaField({ label, value }: { label: string; value: string }) {
  if (!value || value === "N/A") return null;
  return (
    <div className="ct-tecnica-field">
      <span className="ct-tecnica-label">{label}</span>
      <span className="ct-tecnica-value">{value}</span>
    </div>
  );
}

function AchadoCard({ achado }: { achado: CTAchado }) {
  const cfg = STATUS_CONFIG[achado.status] || STATUS_CONFIG.normal;
  return (
    <div className={`ct-achado-card ${achado.status === "alterado" ? "ct-achado-card--alterado" : ""}`}>
      <div className="ct-achado-header">
        <span className="ct-achado-regiao">{achado.regiao}</span>
        <span className={`fr-status-badge ${cfg.className}`}>{cfg.label}</span>
      </div>
      <p className="ct-achado-desc">{achado.descricao}</p>
      {achado.subitens.length > 0 && (
        <div className="ct-subitens">
          {achado.subitens.map((sub, i) => (
            <div key={i} className="ct-subitem">
              <div className="ct-subitem-header">
                <span className="ct-subitem-dot">{RELEVANCIA_DOTS[sub.relevancia] || "\u{26AA}"}</span>
                <span className="ct-subitem-estrutura">{sub.estrutura}</span>
                {sub.medidas && <span className="ct-subitem-medidas">{sub.medidas}</span>}
              </div>
              <p className="ct-subitem-achado">{sub.achado}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ImpressaoItem({ impressao }: { impressao: CTImpressao }) {
  const cfg = GRAVIDADE_CONFIG[impressao.gravidade] || GRAVIDADE_CONFIG.normal;
  return (
    <div className={`ct-impressao-item ${cfg.className}`}>
      <span className="ct-impressao-num">{impressao.numero}</span>
      <span className="ct-impressao-text">{impressao.descricao}</span>
      <span className={`ct-impressao-badge ${cfg.className}`}>{cfg.label}</span>
    </div>
  );
}

function RecomendacaoItem({ rec }: { rec: CTRecomendacao }) {
  const urgCfg = URGENCIA_CONFIG[rec.urgencia] || URGENCIA_CONFIG.eletiva;
  const icon = TIPO_ICONS[rec.tipo] || "\u{1F4CB}";
  return (
    <div className="ct-rec-item">
      <span className="ct-rec-icon">{icon}</span>
      <div className="ct-rec-content">
        <span className="ct-rec-desc">{rec.descricao}</span>
        <span className={`ct-rec-urgencia ${urgCfg.className}`}>{urgCfg.label}</span>
      </div>
    </div>
  );
}

function SectionWrapper({
  sectionKey,
  icon,
  title,
  expanded,
  onToggle,
  badge,
  children,
}: {
  sectionKey: string;
  icon: string;
  title: string;
  expanded: boolean;
  onToggle: (key: string) => void;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`fr-section ${expanded ? "fr-section--expanded" : ""}`}>
      <button className="fr-section-header" onClick={() => onToggle(sectionKey)}>
        <span className="fr-section-icon">{icon}</span>
        <span className="fr-section-title">{title}</span>
        {badge && <span className="ct-section-badge">{badge}</span>}
        <span className="fr-section-chevron">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>
      {expanded && <div className="fr-section-body">{children}</div>}
    </div>
  );
}
