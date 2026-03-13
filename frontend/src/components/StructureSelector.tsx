import type { AnatomyStructure } from "../types";

interface Props {
  structures: AnatomyStructure[];
  selected: string[];
  onToggle: (name: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
}

const STRUCTURE_GROUPS: Record<string, string[]> = {
  "Lungs & Airways": [
    "right lung",
    "left lung",
    "trachea",
  ],
  "Heart & Vessels": [
    "heart",
    "aortic arch",
  ],
  Bones: [
    "right clavicle",
    "left clavicle",
    "spine",
  ],
  "Hilum & Mediastinum": [
    "right hilar structures",
    "left hilar structures",
    "upper mediastinum",
  ],
  "Diaphragm & Angles": [
    "right hemidiaphragm",
    "left hemidiaphragm",
    "right costophrenic angle",
    "left costophrenic angle",
  ],
};

const ALL_STRUCTURES = Object.values(STRUCTURE_GROUPS).flat();

export default function StructureSelector({
  structures,
  selected,
  onToggle,
  onSelectAll,
  onClearSelection,
}: Props) {
  const structureMap = new Map(structures.map((s) => [s.name, s]));
  const allSelected = selected.length === ALL_STRUCTURES.length;

  return (
    <div className="selector-section">
      <div className="selector-header">
        <h2>2. Select Anatomy</h2>
        <div className="selector-actions">
          <button
            className="selector-action-btn"
            onClick={allSelected ? onClearSelection : onSelectAll}
          >
            {allSelected ? "Clear" : "Select All"}
          </button>
          {selected.length > 0 && (
            <span className="selector-count">{selected.length} selected</span>
          )}
        </div>
      </div>
      <div className="structure-groups">
        {Object.entries(STRUCTURE_GROUPS).map(([group, names]) => (
          <div key={group} className="structure-group">
            <h3 className="group-title">{group}</h3>
            <div className="structure-buttons">
              {names.map((name) => {
                const info = structureMap.get(name);
                return (
                  <button
                    key={name}
                    className={`structure-btn ${
                      selected.includes(name) ? "structure-btn--selected" : ""
                    }`}
                    onClick={() => onToggle(name)}
                    title={info?.description}
                  >
                    {name}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export { ALL_STRUCTURES };
