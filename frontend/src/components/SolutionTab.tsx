interface Props {
  mode: "xray" | "ct";
}

function ArchDiagram({ mode }: { mode: "xray" | "ct" }) {
  return (
    <svg viewBox="0 0 260 440" className="sol-arch-svg">
      <defs>
        <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="#bdc1c6" />
        </marker>
        <filter id="s">
          <feDropShadow dx="0" dy="1" stdDeviation="2" floodOpacity="0.07" />
        </filter>
      </defs>

      {/* ── 1. User Input ── */}
      <rect x="50" y="10" width="160" height="40" rx="8" fill="#e8f0fe" stroke="#c5d9f7" strokeWidth="1" filter="url(#s)" />
      <svg x="58" y="16" width="28" height="28" viewBox="0 0 28 28">
        <rect x="2" y="2" width="24" height="24" rx="5" fill="#4285F4" />
        <path d="M14 18v-7m0 0l-3 3m3-3l3 3" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <text x="92" y="34" fontSize="11" fontWeight="600" fill="#1a73e8">
        {mode === "xray" ? "Raio-X + Estruturas" : "DICOM + Consulta"}
      </text>

      {/* ↓ */}
      <line x1="130" y1="50" x2="130" y2="72" stroke="#bdc1c6" strokeWidth="1.5" markerEnd="url(#ar)" />

      {/* ── 2. React Frontend ── */}
      <rect x="50" y="74" width="160" height="40" rx="8" fill="#e6f4ea" stroke="#b7e1cd" strokeWidth="1" filter="url(#s)" />
      <svg x="58" y="80" width="28" height="28" viewBox="0 0 28 28">
        <rect x="2" y="2" width="24" height="24" rx="5" fill="#34A853" />
        <rect x="7" y="7" width="14" height="10" rx="2" stroke="#fff" strokeWidth="1.4" fill="none" />
        <line x1="14" y1="17" x2="14" y2="20" stroke="#fff" strokeWidth="1.4" />
        <line x1="10.5" y1="20" x2="17.5" y2="20" stroke="#fff" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
      <text x="92" y="92" fontSize="11" fontWeight="600" fill="#137333">React + TypeScript</text>
      <text x="92" y="104" fontSize="8" fill="#5f6368">Vite</text>

      {/* ↓ */}
      <line x1="130" y1="114" x2="130" y2="136" stroke="#bdc1c6" strokeWidth="1.5" markerEnd="url(#ar)" />

      {/* ── 3. FastAPI Backend ── */}
      <rect x="50" y="138" width="160" height="40" rx="8" fill="#fef7e0" stroke="#fdd663" strokeWidth="1" filter="url(#s)" />
      <svg x="58" y="144" width="28" height="28" viewBox="0 0 28 28">
        <rect x="2" y="2" width="24" height="24" rx="5" fill="#FBBC04" />
        <rect x="7" y="6" width="14" height="5.5" rx="1.5" stroke="#fff" strokeWidth="1.2" fill="none" />
        <rect x="7" y="16.5" width="14" height="5.5" rx="1.5" stroke="#fff" strokeWidth="1.2" fill="none" />
        <circle cx="10.5" cy="8.75" r="1" fill="#fff" />
        <circle cx="10.5" cy="19.25" r="1" fill="#fff" />
      </svg>
      <text x="92" y="156" fontSize="11" fontWeight="600" fill="#b06000">FastAPI</text>
      <text x="92" y="168" fontSize="8" fill="#5f6368">Cloud Run</text>

      {/* ── Side boxes ── */}
      {/* GCS (left) */}
      <rect x="0" y="141" width="40" height="34" rx="6" fill="#e8f0fe" stroke="#c5d9f7" strokeWidth="1" filter="url(#s)" />
      <text x="20" y="156" fontSize="7.5" fill="#1a73e8" textAnchor="middle" fontWeight="600">GCS</text>
      <text x="20" y="167" fontSize="6.5" fill="#5f6368" textAnchor="middle">{mode === "ct" ? "DICOM" : "Imagens"}</text>
      <line x1="40" y1="158" x2="50" y2="158" stroke="#c5d9f7" strokeWidth="1" strokeDasharray="3 2" />

      {/* Firestore (right) */}
      <rect x="220" y="141" width="40" height="34" rx="6" fill="#fef7e0" stroke="#fdd663" strokeWidth="1" filter="url(#s)" />
      <text x="240" y="156" fontSize="7" fill="#b06000" textAnchor="middle" fontWeight="600">Firestore</text>
      <text x="240" y="167" fontSize="6.5" fill="#5f6368" textAnchor="middle">Historico</text>
      <line x1="210" y1="158" x2="220" y2="158" stroke="#fdd663" strokeWidth="1" strokeDasharray="3 2" />

      {/* ↓ */}
      <line x1="130" y1="178" x2="130" y2="196" stroke="#bdc1c6" strokeWidth="1.5" markerEnd="url(#ar)" />

      {/* ── Vertex AI group ── */}
      <text x="34" y="206" fontSize="8" fill="#9aa0a6" fontWeight="500">Vertex AI</text>
      <rect x="30" y="198" width="200" height="140" rx="10" fill="none" stroke="#e0e0e0" strokeWidth="1" strokeDasharray="4 3" />

      {/* ── 4. MedGemma ── */}
      <rect x="40" y="210" width="180" height="48" rx="8" fill="#fce8e6" stroke="#f5c6c2" strokeWidth="1" filter="url(#s)" />
      <svg x="48" y="218" width="32" height="32" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="6" fill="#EA4335" />
        <circle cx="16" cy="16" r="7" stroke="#fff" strokeWidth="1.5" fill="none" />
        <path d="M12 16c0-2.2 1.8-4 4-4" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M16 12c2.2 0 4 1.8 4 4" stroke="#FBBC04" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M20 16c0 2.2-1.8 4-4 4" stroke="#34A853" strokeWidth="1.5" strokeLinecap="round" />
        <path d="M16 20c-2.2 0-4-1.8-4-4" stroke="#4285F4" strokeWidth="1.5" strokeLinecap="round" />
        <circle cx="16" cy="16" r="1.8" fill="#fff" opacity="0.5" />
      </svg>
      <text x="88" y="234" fontSize="11.5" fontWeight="700" fill="#c5221f">MedGemma 4B</text>
      <text x="88" y="248" fontSize="8" fill="#5f6368">
        {mode === "xray" ? "Bounding boxes + Achados" : "Analise de fatias CT"}
      </text>

      {/* ↓ */}
      <line x1="130" y1="258" x2="130" y2="274" stroke="#bdc1c6" strokeWidth="1.5" markerEnd="url(#ar)" />

      {/* ── 5. Gemini Flash ── */}
      <rect x="40" y="276" width="180" height="48" rx="8" fill="#e8f0fe" stroke="#c5d9f7" strokeWidth="1" filter="url(#s)" />
      <svg x="48" y="284" width="32" height="32" viewBox="0 0 32 32">
        <rect width="32" height="32" rx="6" fill="#4285F4" />
        <path d="M11 16.5l3.5 3.5 7.5-8" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>
      <text x="88" y="300" fontSize="11.5" fontWeight="700" fill="#1a73e8">Gemini Flash</text>
      <text x="88" y="314" fontSize="8" fill="#5f6368">Parsing, educacao e chat</text>

      {/* ── Fan-out ── */}
      <path d="M90 324 Q90 348 48 358" stroke="#bdc1c6" strokeWidth="1.2" fill="none" markerEnd="url(#ar)" />
      <line x1="130" y1="324" x2="130" y2="358" stroke="#bdc1c6" strokeWidth="1.2" markerEnd="url(#ar)" />
      <path d="M170 324 Q170 348 212 358" stroke="#bdc1c6" strokeWidth="1.2" fill="none" markerEnd="url(#ar)" />

      {/* ── 6. Outputs ── */}
      {/* Report */}
      <rect x="4" y="360" width="78" height="40" rx="8" fill="#fef7e0" stroke="#fdd663" strokeWidth="1" filter="url(#s)" />
      <svg x="10" y="366" width="18" height="18" viewBox="0 0 18 18">
        <rect x="2" y="1" width="14" height="16" rx="2.5" fill="#FBBC04" />
        <line x1="5.5" y1="6" x2="12.5" y2="6" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="5.5" y1="9" x2="11" y2="9" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" opacity="0.7" />
        <line x1="5.5" y1="12" x2="10" y2="12" stroke="#fff" strokeWidth="1.2" strokeLinecap="round" opacity="0.5" />
      </svg>
      <text x="31" y="376" fontSize="9" fontWeight="600" fill="#b06000">{mode === "xray" ? "Relatorio" : "Laudo"}</text>
      <text x="31" y="390" fontSize="7.5" fill="#5f6368">Estruturado</text>

      {/* Deep Dive */}
      <rect x="91" y="360" width="78" height="40" rx="8" fill="#e6f4ea" stroke="#b7e1cd" strokeWidth="1" filter="url(#s)" />
      <svg x="97" y="366" width="18" height="18" viewBox="0 0 18 18">
        <rect x="2" y="1" width="14" height="16" rx="2.5" fill="#34A853" />
        <path d="M9 5.5l-5 2.8 5 2.8 5-2.8L9 5.5z" stroke="#fff" strokeWidth="1" fill="none" strokeLinejoin="round" />
        <path d="M6 10v2.5c0 .5 1.3 1.5 3 1.5s3-1 3-1.5V10" stroke="#fff" strokeWidth="1" fill="none" />
      </svg>
      <text x="118" y="376" fontSize="9" fontWeight="600" fill="#137333">Deep Dive</text>
      <text x="118" y="390" fontSize="7.5" fill="#5f6368">Educacional</text>

      {/* Chat */}
      <rect x="178" y="360" width="78" height="40" rx="8" fill="#f3e8fd" stroke="#d7b2f0" strokeWidth="1" filter="url(#s)" />
      <svg x="184" y="366" width="18" height="18" viewBox="0 0 18 18">
        <rect x="2" y="1" width="14" height="16" rx="2.5" fill="#8E24AA" />
        <rect x="4.5" y="4.5" width="9" height="6" rx="2" stroke="#fff" strokeWidth="1" fill="none" />
        <path d="M7 10.5v2l2-2" stroke="#fff" strokeWidth="0.9" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <text x="205" y="376" fontSize="9" fontWeight="600" fill="#6a1b9a">Chat</text>
      <text x="205" y="390" fontSize="7.5" fill="#5f6368">Interativo</text>

      {/* ── Bottom label ── */}
      <line x1="43" y1="400" x2="43" y2="416" stroke="#e0e0e0" strokeWidth="1" />
      <line x1="130" y1="400" x2="130" y2="416" stroke="#e0e0e0" strokeWidth="1" />
      <line x1="217" y1="400" x2="217" y2="416" stroke="#e0e0e0" strokeWidth="1" />
      <line x1="43" y1="416" x2="217" y2="416" stroke="#e0e0e0" strokeWidth="1" />
      <line x1="130" y1="416" x2="130" y2="426" stroke="#bdc1c6" strokeWidth="1.5" markerEnd="url(#ar)" />
      <rect x="85" y="428" width="90" height="12" rx="4" fill="#f1f3f4" />
      <text x="130" y="437" fontSize="7.5" fill="#5f6368" textAnchor="middle" fontWeight="500">Estudante / Medico</text>
    </svg>
  );
}

export default function SolutionTab({ mode }: Props) {
  return (
    <div className="solution-tab">
      <div className="sol-header">
        <h3 className="sol-title">Arquitetura</h3>
        <span className="sol-subtitle">{mode === "xray" ? "Raio-X" : "CT"}</span>
      </div>
      <ArchDiagram mode={mode} />
    </div>
  );
}
