import { useCallback, useEffect, useState } from "react";
import "./App.css";
import Disclaimer from "./components/Disclaimer";
import Header from "./components/Header";
import HistoryPanel from "./components/HistoryPanel";
import CTSeriesPicker from "./components/CTSeriesPicker";
import CTResultViewer from "./components/CTResultViewer";
import CTSliceViewer from "./components/CTSliceViewer";
import SolutionTab from "./components/SolutionTab";
import {
  analyzeCtSeries,
  clearAllCtAnalyses,
  deleteCtAnalysis,
  fetchCtAnalyses,
  fetchCtAnalysis,
  fetchCtFrames,
  fetchCtSamples,
} from "./hooks/useCtApi";
import type { CTAnalysisResult, CTSampleSeries } from "./types";

export default function CTApp() {
  const [mockMode, setMockMode] = useState(false);
  const [samples, setSamples] = useState<CTSampleSeries[]>([]);
  const [selectedSeriesId, setSelectedSeriesId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CTAnalysisResult | null>(null);
  const [history, setHistory] = useState<CTAnalysisResult[]>([]);
  const [frames, setFrames] = useState<string[]>([]);
  const [framesTotalInstances, setFramesTotalInstances] = useState(0);
  const [framesLoading, setFramesLoading] = useState(false);

  const refreshHistory = useCallback(() => {
    fetchCtAnalyses(20)
      .then(setHistory)
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchCtSamples()
      .then(setSamples)
      .catch(() => setError("Falha ao carregar series de TC"));
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const handleSeriesSelected = useCallback((sample: CTSampleSeries) => {
    setSelectedSeriesId(sample.id);
    setResult(null);
    setError(null);
    // Pre-fill the query with the sample's default
    if (sample.default_query) {
      setQuery(sample.default_query);
    }
    // Load frames for the viewer
    setFrames([]);
    setFramesLoading(true);
    fetchCtFrames(sample.id, 30)
      .then((data) => {
        setFrames(data.frames);
        setFramesTotalInstances(data.total_instances);
      })
      .catch(() => {
        // Frames are optional — viewer just won't show
        setFrames([]);
      })
      .finally(() => setFramesLoading(false));
  }, []);

  const handleAnalyze = async () => {
    if (!selectedSeriesId || !query.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await analyzeCtSeries(selectedSeriesId, query, mockMode);
      setResult(res);
      refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha na analise de TC");
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = async (analysis: CTAnalysisResult) => {
    try {
      const full = await fetchCtAnalysis(analysis.id);
      setResult(full);
    } catch {
      setResult(analysis);
    }
    setSelectedSeriesId(analysis.series_id);
    setQuery(analysis.query);
  };

  const handleDeleteOne = async (id: string) => {
    await deleteCtAnalysis(id);
    if (result?.id === id) setResult(null);
    refreshHistory();
  };

  const handleClearAll = async () => {
    await clearAllCtAnalyses();
    setResult(null);
    setHistory([]);
  };

  // Adapt CT history items to the shape HistoryPanel expects
  const historyForPanel = history.map((h) => ({
    id: h.id,
    object_name: h.series_name,
    response_text: h.response_text,
    bounding_boxes: [],
    image_url: "",
    image_width: 0,
    image_height: 0,
    educational_info: { description: h.query, clinical_relevance: "" },
    created_at: h.created_at,
    mock: h.mock,
  }));

  return (
    <div className="app">
      <Header
        mockMode={mockMode}
        onToggleMock={() => setMockMode((m) => !m)}
        title="MedGemma Explica - CT"
        subtitle="Analise Educacional de Tomografia Computadorizada"
        badge="MedGemma 1.5 CT + Gemini Flash"
      />
      <Disclaimer />

      <div className="workspace">
        {/* Left: Controls */}
        <div className="controls-panel">
          <CTSeriesPicker
            samples={samples}
            selected={selectedSeriesId}
            onSelect={handleSeriesSelected}
          />

          {(frames.length > 0 || framesLoading) && (
            <CTSliceViewer
              frames={frames}
              totalInstances={framesTotalInstances}
              loading={framesLoading}
            />
          )}

          <div className="ct-query-section">
            <label className="ct-query-label" htmlFor="ct-query">
              Sua consulta sobre o exame:
            </label>
            <textarea
              id="ct-query"
              className="ct-query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ex: Descreva os achados principais e a impressao diagnostica..."
              rows={3}
            />
          </div>

          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={!selectedSeriesId || !query.trim() || loading}
          >
            {loading ? (
              <>
                <span className="spinner" /> Analisando TC...
              </>
            ) : mockMode ? (
              "Analisar TC (Demo)"
            ) : (
              "Analisar TC com MedGemma"
            )}
          </button>

          {error && <div className="error-message">{error}</div>}
        </div>

        {/* Center: Results */}
        <div className="results-panel">
          {result ? (
            <CTResultViewer
              result={result}
              mockMode={mockMode}
              onResultUpdated={setResult}
            />
          ) : (
            <div className="results-empty">
              <div className="results-empty-icon">{"\u{1FA7B}"}</div>
              <h3>Nenhuma analise de TC ainda</h3>
              <p>
                Selecione uma serie de TC, escreva sua consulta e clique em
                Analisar para ver os resultados aqui.
              </p>
            </div>
          )}
        </div>

        {/* Right: Solution */}
        <div className="solution-panel">
          <SolutionTab mode="ct" />
        </div>
      </div>

      {/* Bottom: History */}
      <HistoryPanel
        analyses={historyForPanel}
        onSelect={(_item) => {
          const ct = history.find((h) => h.id === _item.id);
          if (ct) handleHistorySelect(ct);
        }}
        onDelete={handleDeleteOne}
        onClearAll={handleClearAll}
        activeId={result?.id}
      />
    </div>
  );
}
