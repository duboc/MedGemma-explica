import type { CTSampleSeries } from "../types";

interface Props {
  samples: CTSampleSeries[];
  selected: string | null;
  onSelect: (sample: CTSampleSeries) => void;
}

const BODY_PART_ICONS: Record<string, string> = {
  Abdome: "\u{1F9E0}",
  Torax: "\u{1FAC1}",
  Cranio: "\u{1F9E0}",
};

export default function CTSeriesPicker({ samples, selected, onSelect }: Props) {
  return (
    <div className="ct-series-picker">
      <h3 className="ct-series-title">Series de TC Disponiveis</h3>
      <div className="ct-series-grid">
        {samples.map((s) => (
          <button
            key={s.id}
            className={`ct-series-card ${selected === s.id ? "ct-series-card--selected" : ""}`}
            onClick={() => onSelect(s)}
          >
            <div className="ct-series-icon">
              {BODY_PART_ICONS[s.body_part] || "\u{1FA7B}"}
            </div>
            <div className="ct-series-info">
              <div className="ct-series-name">{s.name}</div>
              <div className="ct-series-desc">{s.description}</div>
              <div className="ct-series-meta">
                <span className="ct-series-tag">{s.body_part}</span>
                <span className="ct-series-slices">{s.num_slices} fatias</span>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
