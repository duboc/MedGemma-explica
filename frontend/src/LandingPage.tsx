import { Link } from "react-router-dom";
import "./App.css";

export default function LandingPage() {
  return (
    <div className="landing">
      <div className="landing-header">
        <h1 className="landing-title">MedGemma Explica</h1>
        <p className="landing-subtitle">
          Plataforma educacional de imagens medicas com IA
        </p>
      </div>

      <div className="landing-cards">
        <Link to="/xray" className="landing-card">
          <div className="landing-card-icon">{"\u{1FA7B}"}</div>
          <h2 className="landing-card-title">Raio-X de Torax</h2>
          <p className="landing-card-desc">
            Localizacao anatomica educacional em radiografias de torax. Envie ou
            selecione uma imagem, escolha estruturas anatomicas e veja a analise
            com bounding boxes.
          </p>
          <div className="landing-card-features">
            <span className="landing-feature">Upload de imagem</span>
            <span className="landing-feature">Bounding boxes</span>
            <span className="landing-feature">15 estruturas</span>
          </div>
          <div className="landing-card-badge">MedGemma 1.5 + Gemini Flash</div>
        </Link>

        <Link to="/ct" className="landing-card">
          <div className="landing-card-icon">{"\u{1F9EC}"}</div>
          <h2 className="landing-card-title">Tomografia Computadorizada</h2>
          <p className="landing-card-desc">
            Analise educacional de series de TC a partir de dados publicos do
            IDC. Selecione uma serie DICOM, faca uma consulta e receba a analise
            textual detalhada.
          </p>
          <div className="landing-card-features">
            <span className="landing-feature">Series DICOM</span>
            <span className="landing-feature">Analise textual</span>
            <span className="landing-feature">~85 fatias</span>
          </div>
          <div className="landing-card-badge">MedGemma 1.5 CT + Gemini Flash</div>
        </Link>
      </div>

      <div className="landing-disclaimer">
        <strong>Uso Exclusivamente Educacional:</strong> Esta demonstracao e
        apenas para fins educacionais, mostrando a funcionalidade basica do
        MedGemma 1.5. Nao representa um produto finalizado ou aprovado, nao se
        destina a diagnosticar ou sugerir tratamento para qualquer doenca ou
        condicao, e nao deve ser utilizada para aconselhamento medico.
      </div>
    </div>
  );
}
