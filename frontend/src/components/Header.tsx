interface Props {
  mockMode: boolean;
  onToggleMock: () => void;
  title?: string;
  subtitle?: string;
  badge?: string;
}

export default function Header({
  mockMode,
  onToggleMock,
  title = "MedGemma Explica",
  subtitle = "Localizacao Anatomica Educacional em Radiografias de Torax",
  badge = "MedGemma 1.5 + Gemini Flash no Vertex AI",
}: Props) {
  return (
    <header className="header">
      <div className="header-content">
        <h1 className="header-title">{title}</h1>
        <p className="header-subtitle">{subtitle}</p>
      </div>
      <div className="header-right">
        <label className="mock-toggle">
          <span className="mock-label">
            {mockMode ? "Modo Demo" : "Modo Real"}
          </span>
          <button
            className={`toggle-switch ${mockMode ? "toggle-switch--on" : ""}`}
            onClick={onToggleMock}
            aria-label="Alternar modo demo"
          >
            <span className="toggle-knob" />
          </button>
        </label>
        <div className="header-badge">{badge}</div>
      </div>
    </header>
  );
}
