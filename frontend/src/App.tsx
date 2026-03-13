import { useCallback, useEffect, useState } from "react";
import "./App.css";
import Disclaimer from "./components/Disclaimer";
import Header from "./components/Header";
import HistoryPanel from "./components/HistoryPanel";
import ImageUploader from "./components/ImageUploader";
import ResultViewer from "./components/ResultViewer";
import SamplePicker from "./components/SamplePicker";
import StructureSelector, { ALL_STRUCTURES } from "./components/StructureSelector";
import {
  analyzeImage,
  clearAllAnalyses,
  deleteAnalysis,
  fetchAnalyses,
  fetchSamples,
  fetchStructures,
  resolveImageUrl,
  sampleImageUrl,
} from "./hooks/useApi";
import type { AnalysisResult, AnatomyStructure, SampleImage } from "./types";

export default function App() {
  const [mockMode, setMockMode] = useState(false);
  const [structures, setStructures] = useState<AnatomyStructure[]>([]);
  const [samples, setSamples] = useState<SampleImage[]>([]);
  const [selectedStructures, setSelectedStructures] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [history, setHistory] = useState<AnalysisResult[]>([]);

  const refreshHistory = useCallback(() => {
    fetchAnalyses(20, mockMode)
      .then(setHistory)
      .catch(() => {});
  }, [mockMode]);

  useEffect(() => {
    fetchStructures()
      .then(setStructures)
      .catch(() => setError("Failed to load anatomical structures"));
    fetchSamples()
      .then(setSamples)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  const handleFileSelected = useCallback((f: File) => {
    setFile(f);
    setSelectedSampleId(null);
    setPreviewUrl(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  }, []);

  const handleSampleSelected = useCallback((sample: SampleImage) => {
    setSelectedSampleId(sample.id);
    setFile(null);
    setPreviewUrl(sampleImageUrl(sample.filename));
    setResult(null);
    setError(null);
  }, []);

  const handleToggleStructure = useCallback((name: string) => {
    setSelectedStructures((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]
    );
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedStructures([...ALL_STRUCTURES]);
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedStructures([]);
  }, []);

  const handleAnalyze = async () => {
    if ((!file && !selectedSampleId) || selectedStructures.length === 0) return;

    setLoading(true);
    setError(null);
    try {
      const objectName = selectedStructures.join(", ");
      const res = await analyzeImage(
        objectName,
        mockMode,
        file ?? undefined,
        selectedSampleId ?? undefined
      );
      setResult(res);
      refreshHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = (analysis: AnalysisResult) => {
    setResult(analysis);
    setPreviewUrl(resolveImageUrl(analysis.image_url));
    const names = analysis.structure_names ?? [analysis.object_name];
    setSelectedStructures(names);
    setFile(null);
    setSelectedSampleId(null);
  };

  const handleDeleteOne = async (id: string) => {
    await deleteAnalysis(id, mockMode);
    if (result?.id === id) setResult(null);
    refreshHistory();
  };

  const handleClearAll = async () => {
    await clearAllAnalyses(mockMode);
    setResult(null);
    setHistory([]);
  };

  const hasImage = !!file || !!selectedSampleId;
  const structureCount = selectedStructures.length;

  return (
    <div className="app">
      <Header
        mockMode={mockMode}
        onToggleMock={() => setMockMode((m) => !m)}
      />
      <Disclaimer />

      <div className="workspace">
        {/* Left: Controls */}
        <div className="controls-panel">
          <ImageUploader
            onFileSelected={handleFileSelected}
            previewUrl={previewUrl}
          />

          <SamplePicker
            samples={samples}
            selected={selectedSampleId}
            onSelect={handleSampleSelected}
          />

          <StructureSelector
            structures={structures}
            selected={selectedStructures}
            onToggle={handleToggleStructure}
            onSelectAll={handleSelectAll}
            onClearSelection={handleClearSelection}
          />

          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={!hasImage || structureCount === 0 || loading}
          >
            {loading ? (
              <>
                <span className="spinner" /> Analyzing {structureCount} structure{structureCount !== 1 ? "s" : ""}...
              </>
            ) : mockMode ? (
              `Analyze${structureCount > 0 ? ` (${structureCount})` : ""} (Mock)`
            ) : (
              `Analyze${structureCount > 0 ? ` ${structureCount} structure${structureCount !== 1 ? "s" : ""}` : ""} with MedGemma`
            )}
          </button>

          {error && <div className="error-message">{error}</div>}
        </div>

        {/* Right: Results */}
        <div className="results-panel">
          {result ? (
            <ResultViewer
              result={result}
              mockMode={mockMode}
              onResultUpdated={setResult}
            />
          ) : (
            <div className="results-empty">
              <div className="results-empty-icon">&#x1F50D;</div>
              <h3>No analysis yet</h3>
              <p>
                Upload or select a chest X-ray, choose one or more anatomical
                structures, and click Analyze to see results here.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Bottom: History */}
      <HistoryPanel
        analyses={history}
        onSelect={handleHistorySelect}
        onDelete={handleDeleteOne}
        onClearAll={handleClearAll}
        activeId={result?.id}
      />
    </div>
  );
}
