interface Props {
  mockMode: boolean;
  onToggleMock: () => void;
}

export default function Header({ mockMode, onToggleMock }: Props) {
  return (
    <header className="header">
      <div className="header-content">
        <h1 className="header-title">MedGemma Explica</h1>
        <p className="header-subtitle">
          Localização Anatômica Educacional em Radiografias de Tórax
        </p>
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
        <div className="header-badge">
          MedGemma 1.5 + Gemini Flash no Vertex AI
        </div>
      </div>
    </header>
  );
}
