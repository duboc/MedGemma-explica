import { useCallback, useState } from "react";

interface Props {
  onFileSelected: (file: File) => void;
  previewUrl: string | null;
}

export default function ImageUploader({ onFileSelected, previewUrl }: Props) {
  const [dragActive, setDragActive] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith("image/")) {
        onFileSelected(file);
      }
    },
    [onFileSelected]
  );

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  };

  return (
    <div className="uploader-section">
      <h2>1. Upload Chest X-ray</h2>
      <div
        className={`drop-zone ${dragActive ? "drop-zone--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="X-ray preview" className="preview-image" />
        ) : (
          <div className="drop-zone-content">
            <div className="drop-zone-icon">+</div>
            <p>Drag & drop a chest X-ray image here</p>
            <p className="drop-zone-hint">or click to browse (PNG, JPEG)</p>
          </div>
        )}
      </div>
      <input
        id="file-input"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={handleChange}
        hidden
      />
    </div>
  );
}
