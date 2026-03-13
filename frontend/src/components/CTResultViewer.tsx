import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { CTAnalysisResult, ChatMessage, DeepDiveResult, DeepDiveSection } from "../types";
import {
  explainCtAnalysis,
  chatCtAnalysis,
  suggestCtQuestions,
  updateCtAnalysis,
} from "../hooks/useCtApi";
import { renderMarkdownToHtml } from "../utils/markdown";

type TabKey = "analise" | "explain" | "chat";

const TAB_CONFIG: { key: TabKey; label: string; icon: string; desc: string }[] = [
  { key: "analise", label: "Laudo", icon: "\u{1F4CB}", desc: "Resultado da analise" },
  { key: "explain", label: "Deep Dive", icon: "\u{1F393}", desc: "Aprofundamento educacional" },
  { key: "chat", label: "Perguntas", icon: "\u{1F4AC}", desc: "Tire duvidas" },
];

interface Props {
  result: CTAnalysisResult;
  mockMode: boolean;
  onResultUpdated?: (result: CTAnalysisResult) => void;
}

export default function CTResultViewer({ result, mockMode, onResultUpdated }: Props) {
  const [activeTab, setActiveTab] = useState<TabKey>("analise");

  useEffect(() => {
    setActiveTab("analise");
  }, [result.id]);

  const saveField = useCallback(
    (field: string, value: unknown) => {
      const updated = { ...result, [field]: value };
      onResultUpdated?.(updated);
      updateCtAnalysis(result.id, { [field]: value }).catch(() => {});
    },
    [result, onResultUpdated]
  );

  const hasSavedDive = !!result.deep_dive;
  const hasSavedChat = result.chat_messages && result.chat_messages.length > 0;

  const savedMap: Record<TabKey, boolean> = {
    analise: true,
    explain: hasSavedDive,
    chat: !!hasSavedChat,
  };

  return (
    <div className="rv">
      {/* Series info strip */}
      <div className="ct-result-header">
        <div className="ct-result-top-row">
          <div className="ct-result-series">{result.series_name}</div>
          <div className="ct-result-meta">
            <span className="ct-series-tag">{result.body_part}</span>
            <span className="ct-series-slices">{result.num_slices} fatias analisadas</span>
            {result.mock ? (
              <span className="rv-badge">Demo</span>
            ) : (
              <span className="rv-badge rv-badge--live">MedGemma</span>
            )}
          </div>
        </div>
        <div className="ct-result-query">
          <span className="ct-result-query-label">Consulta:</span> {result.query}
        </div>
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

      {/* Tab content */}
      <div className="rv-content">
        {activeTab === "analise" && (
          <div className="ct-analysis-content">
            <div
              className="ct-analysis-text"
              dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(result.response_text) }}
            />
          </div>
        )}

        {activeTab === "explain" && (
          <CTExplainPanel
            result={result}
            mockMode={mockMode}
            onSave={(dive) => saveField("deep_dive", dive)}
          />
        )}

        {activeTab === "chat" && (
          <CTChatPanel
            result={result}
            mockMode={mockMode}
            onSave={(msgs) => saveField("chat_messages", msgs)}
          />
        )}
      </div>
    </div>
  );
}

// ===== CT Explain Panel =====

const LEVELS = [
  { value: "pre_med", label: "Pre-Medicina" },
  { value: "medical_student", label: "Estudante de Medicina" },
  { value: "resident", label: "Residente" },
  { value: "attending", label: "Medico Assistente" },
];

const SECTION_ICONS: Record<string, string> = {
  eye: "\u{1F441}",
  balance: "\u{2696}",
  stethoscope: "\u{1FA7A}",
  lightbulb: "\u{1F4A1}",
  clipboard: "\u{1F4CB}",
  microscope: "\u{1F52C}",
  brain: "\u{1F9E0}",
  book: "\u{1F4D6}",
};

function isStructuredResult(val: unknown): val is DeepDiveResult {
  return typeof val === "object" && val !== null && "sections" in val;
}

function CTExplainPanel({
  result,
  mockMode,
  onSave,
}: {
  result: CTAnalysisResult;
  mockMode: boolean;
  onSave?: (data: { level: string; explanation: DeepDiveResult }) => void;
}) {
  const cached = result.deep_dive;
  const cachedExplanation = cached?.explanation;
  const initialResult = isStructuredResult(cachedExplanation) ? cachedExplanation : null;

  const [level, setLevel] = useState(cached?.level ?? "medical_student");
  const [deepDive, setDeepDive] = useState<DeepDiveResult | null>(initialResult);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["tecnica", "anatomia", "achados_normal_anormal", "correlacao_clinica", "dicas_interpretacao",
             "identification", "normal_vs_abnormal", "clinical_connections", "study_tips", "content"])
  );

  const handleExplain = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await explainCtAnalysis(
        result.series_name,
        result.body_part,
        result.response_text,
        level,
        mockMode
      );
      const data: DeepDiveResult = res.explanation;
      setDeepDive(data);
      onSave?.({ level, explanation: data });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao gerar explicacao");
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
    if (deepDive) setExpandedSections(new Set(deepDive.sections.map((s) => s.id)));
  };
  const collapseAll = () => setExpandedSections(new Set());

  return (
    <div className="explain-panel">
      <div className="explain-header">
        <h3>Aprofundamento Educacional</h3>
        <span className="rv-badge">Gemini Flash</span>
      </div>

      <div className="explain-controls">
        <label className="explain-level-label">Nivel de explicacao:</label>
        <div className="explain-level-buttons">
          {LEVELS.map((l) => (
            <button
              key={l.value}
              className={`explain-level-btn ${level === l.value ? "explain-level-btn--active" : ""}`}
              onClick={() => { setLevel(l.value); setDeepDive(null); }}
            >
              {l.label}
            </button>
          ))}
        </div>
        <button className="explain-generate-btn" onClick={handleExplain} disabled={loading}>
          {loading ? (
            <><span className="spinner" /> Gerando material educacional...</>
          ) : deepDive ? "Regenerar Aprofundamento" : "Gerar Aprofundamento Educacional"}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {deepDive && (
        <div className="fr-report">
          {deepDive.title && <div className="dd-title">{deepDive.title}</div>}
          <div className="fr-toolbar">
            <button className="fr-toolbar-btn" onClick={expandAll}>Expandir Tudo</button>
            <button className="fr-toolbar-btn" onClick={collapseAll}>Recolher Tudo</button>
          </div>
          {deepDive.sections.map((section) => (
            <CTSectionRenderer
              key={section.id}
              section={section}
              expanded={expandedSections.has(section.id)}
              onToggle={toggleSection}
            />
          ))}
          {deepDive.disclaimer && <div className="dd-disclaimer">{deepDive.disclaimer}</div>}
        </div>
      )}
    </div>
  );
}

function CTSectionRenderer({
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
        <span className="fr-section-icon">{SECTION_ICONS[section.icon] || "\u{1F4CB}"}</span>
        <span className="fr-section-title">{section.title}</span>
        <span className="fr-section-chevron">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>
      {expanded && (
        <div className="fr-section-body">
          {section.content && <p className="dd-section-content">{section.content}</p>}
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
                      <div className="dd-comparison-label">Sinais Anormais</div>
                      <ul>{comp.abnormal_signs.map((sign, j) => <li key={j}>{sign}</li>)}</ul>
                    </div>
                  </div>
                  <div className="dd-comparison-this-image">
                    <strong>Neste Exame:</strong> {comp.this_image}
                  </div>
                </div>
              ))}
            </div>
          )}
          {section.connections && section.connections.length > 0 && (
            <div className="dd-connections">
              {section.connections.map((conn, i) => (
                <div key={i} className="dd-connection-card">
                  <div className="dd-connection-condition">{conn.condition}</div>
                  <p className="dd-connection-relevance">{conn.relevance}</p>
                  <div className="dd-connection-look-for">
                    <span className="dd-connection-look-label">Procurar:</span> {conn.what_to_look_for}
                  </div>
                </div>
              ))}
            </div>
          )}
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

// ===== CT Chat Panel =====

const FALLBACK_CT_QUESTIONS = [
  "Quais sao os achados mais importantes nesta TC?",
  "Como interpretar sistematicamente esta tomografia?",
  "Quais patologias devem ser investigadas?",
  "Quais sao os diagnosticos diferenciais?",
  "Que exames complementares seriam uteis?",
];

const SUGGESTION_ICONS = [
  "\u{1F9EB}", "\u{1F4CB}", "\u{1FA7A}", "\u{1F9E0}", "\u{1F4CF}", "\u{1F4A1}",
];

const CTChatBubble = memo(function CTChatBubble({
  role,
  content,
}: {
  role: "user" | "assistant";
  content: string;
}) {
  return (
    <div className={`chat-message chat-message--${role}`}>
      <div className="chat-message-label">
        {role === "user" ? "Voce" : "MedGemma"}
      </div>
      {role === "assistant" ? (
        <div
          className="chat-message-content"
          dangerouslySetInnerHTML={{ __html: renderMarkdownToHtml(content) }}
        />
      ) : (
        <div className="chat-message-content">{content}</div>
      )}
    </div>
  );
});

function CTChatPanel({
  result,
  mockMode,
  onSave,
}: {
  result: CTAnalysisResult;
  mockMode: boolean;
  onSave?: (messages: ChatMessage[]) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(result.chat_messages ?? []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(FALLBACK_CT_QUESTIONS);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingSuggestions(true);
    suggestCtQuestions(result.body_part, mockMode)
      .then((data) => {
        if (!cancelled && data?.questions?.length > 0) {
          setSuggestions(data.questions);
        }
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingSuggestions(false); });
    return () => { cancelled = true; };
  }, [result.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = { role: "user", content: text.trim() };
    const updated = [...messages, userMsg];
    setMessages(updated);
    setInput("");
    setLoading(true);

    try {
      const res = await chatCtAnalysis(
        updated,
        result.series_name,
        result.body_part,
        result.response_text,
        mockMode
      );
      const withResponse = [...updated, { role: "assistant" as const, content: res.response }];
      setMessages(withResponse);
      onSave?.(withResponse);
    } catch {
      const withError = [
        ...updated,
        { role: "assistant" as const, content: "Desculpe, nao consegui processar essa pergunta. Por favor, tente novamente." },
      ];
      setMessages(withError);
      onSave?.(withError);
    } finally {
      setLoading(false);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h3>Pergunte Sobre Esta TC</h3>
        <span className="rv-badge">Q&A</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Faca perguntas sobre os achados, patologias ou anatomia deste exame de TC.</p>
            {loadingSuggestions ? (
              <div className="chat-suggestions-loading">
                <span className="spinner" /> Gerando perguntas...
              </div>
            ) : (
              <div className="chat-suggestions-grid">
                {suggestions.slice(0, 6).map((q, i) => (
                  <button
                    key={i}
                    className="chat-suggestion-card"
                    onClick={() => sendMessage(q)}
                  >
                    <span className="chat-suggestion-icon">{SUGGESTION_ICONS[i % SUGGESTION_ICONS.length]}</span>
                    <span className="chat-suggestion-text">{q}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <CTChatBubble key={i} role={msg.role} content={msg.content} />
        ))}

        {loading && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message-label">MedGemma</div>
            <div className="chat-message-content chat-typing">
              <span className="spinner" /> Pensando...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Pergunte sobre os achados da TC..."
          disabled={loading}
        />
        <button type="submit" className="chat-send-btn" disabled={!input.trim() || loading}>
          Enviar
        </button>
      </form>
    </div>
  );
}
