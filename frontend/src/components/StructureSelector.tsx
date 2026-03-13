import type { AnatomyStructure } from "../types";

interface Props {
  structures: AnatomyStructure[];
  selected: string[];
  onToggle: (name: string) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;
}

const STRUCTURE_GROUPS: Record<string, string[]> = {
  "Pulmões e Vias Aéreas": [
    "right lung",
    "left lung",
    "trachea",
  ],
  "Coração e Vasos": [
    "heart",
    "aortic arch",
  ],
  Ossos: [
    "right clavicle",
    "left clavicle",
    "spine",
  ],
  "Hilo e Mediastino": [
    "right hilar structures",
    "left hilar structures",
    "upper mediastinum",
  ],
  "Diafragma e Ângulos": [
    "right hemidiaphragm",
    "left hemidiaphragm",
    "right costophrenic angle",
    "left costophrenic angle",
  ],
};

/** Display names in Portuguese for structure buttons. Keys stay English for MedGemma API. */
const STRUCTURE_NAMES_PT: Record<string, string> = {
  "right lung": "Pulmão Direito",
  "left lung": "Pulmão Esquerdo",
  "trachea": "Traqueia",
  "heart": "Coração",
  "aortic arch": "Arco Aórtico",
  "right clavicle": "Clavícula Direita",
  "left clavicle": "Clavícula Esquerda",
  "spine": "Coluna Vertebral",
  "right hilar structures": "Estruturas Hilares Direitas",
  "left hilar structures": "Estruturas Hilares Esquerdas",
  "upper mediastinum": "Mediastino Superior",
  "right hemidiaphragm": "Hemidiafragma Direito",
  "left hemidiaphragm": "Hemidiafragma Esquerdo",
  "right costophrenic angle": "Ângulo Costofrênico Direito",
  "left costophrenic angle": "Ângulo Costofrênico Esquerdo",
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
        <h2>2. Selecionar Anatomia</h2>
        <div className="selector-actions">
          <button
            className="selector-action-btn"
            onClick={allSelected ? onClearSelection : onSelectAll}
          >
            {allSelected ? "Limpar" : "Selecionar Tudo"}
          </button>
          {selected.length > 0 && (
            <span className="selector-count">{selected.length} selecionado{selected.length !== 1 ? "s" : ""}</span>
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
                    {STRUCTURE_NAMES_PT[name] ?? name}
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
