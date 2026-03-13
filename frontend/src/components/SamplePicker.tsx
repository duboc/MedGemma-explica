import type { SampleImage } from "../types";
import { sampleImageUrl } from "../hooks/useApi";

interface Props {
  samples: SampleImage[];
  selected: string | null;
  onSelect: (sample: SampleImage) => void;
}

export default function SamplePicker({ samples, selected, onSelect }: Props) {
  if (samples.length === 0) return null;

  return (
    <div className="sample-picker">
      <h3 className="sample-picker-title">Ou escolha uma radiografia de exemplo</h3>
      <div className="sample-grid">
        {samples.map((s) => (
          <button
            key={s.id}
            className={`sample-card ${selected === s.id ? "sample-card--selected" : ""}`}
            onClick={() => onSelect(s)}
          >
            <img
              src={sampleImageUrl(s.filename)}
              alt={s.name}
              className="sample-thumb"
            />
            <div className="sample-info">
              <span className="sample-name">{s.name}</span>
              <span className="sample-source">{s.source}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
