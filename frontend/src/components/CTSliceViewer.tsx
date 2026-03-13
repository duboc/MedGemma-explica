import { useCallback, useEffect, useRef, useState } from "react";

interface CTSliceViewerProps {
  frames: string[];
  totalInstances: number;
  loading?: boolean;
}

export default function CTSliceViewer({
  frames,
  totalInstances,
  loading,
}: CTSliceViewerProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const dragStartY = useRef(0);
  const dragStartIndex = useRef(0);

  // Reset index when frames change
  useEffect(() => {
    setCurrentIndex(0);
  }, [frames]);

  const goTo = useCallback(
    (idx: number) => {
      setCurrentIndex(Math.max(0, Math.min(frames.length - 1, idx)));
    },
    [frames.length]
  );

  // Keyboard navigation
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
        e.preventDefault();
        goTo(currentIndex - 1);
      } else if (e.key === "ArrowDown" || e.key === "ArrowRight") {
        e.preventDefault();
        goTo(currentIndex + 1);
      } else if (e.key === "Home") {
        e.preventDefault();
        goTo(0);
      } else if (e.key === "End") {
        e.preventDefault();
        goTo(frames.length - 1);
      }
    };

    el.addEventListener("keydown", handler);
    return () => el.removeEventListener("keydown", handler);
  }, [currentIndex, frames.length, goTo]);

  // Mouse wheel scrolling
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      if (e.deltaY > 0) {
        goTo(currentIndex + 1);
      } else if (e.deltaY < 0) {
        goTo(currentIndex - 1);
      }
    },
    [currentIndex, goTo]
  );

  // Click-drag scrolling (like radiologists do)
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      setIsDragging(true);
      dragStartY.current = e.clientY;
      dragStartIndex.current = currentIndex;
    },
    [currentIndex]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDragging) return;
      const dy = e.clientY - dragStartY.current;
      const sensitivity = 3; // pixels per slice
      const delta = Math.round(dy / sensitivity);
      goTo(dragStartIndex.current + delta);
    },
    [isDragging, goTo]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  if (loading) {
    return (
      <div className="ct-viewer">
        <div className="ct-viewer-loading">
          <span className="spinner" /> Carregando fatias...
        </div>
      </div>
    );
  }

  if (frames.length === 0) {
    return null;
  }

  // Map the viewer index to approximate original slice number
  const approxSlice = Math.round(
    (currentIndex / Math.max(1, frames.length - 1)) * (totalInstances - 1) + 1
  );

  return (
    <div
      className="ct-viewer"
      ref={containerRef}
      tabIndex={0}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ cursor: isDragging ? "grabbing" : "grab" }}
    >
      <div className="ct-viewer-header">
        <span className="ct-viewer-title">Visualizador de Fatias</span>
        <span className="ct-viewer-counter">
          {currentIndex + 1} / {frames.length} (fatia ~{approxSlice} de{" "}
          {totalInstances})
        </span>
      </div>

      <div className="ct-viewer-image-container">
        <img
          src={`data:image/png;base64,${frames[currentIndex]}`}
          alt={`TC fatia ${currentIndex + 1}`}
          className="ct-viewer-image"
          draggable={false}
        />
      </div>

      <input
        type="range"
        className="ct-viewer-slider"
        min={0}
        max={frames.length - 1}
        value={currentIndex}
        onChange={(e) => goTo(Number(e.target.value))}
      />

      <div className="ct-viewer-hint">
        Scroll do mouse, arraste ou use as setas para navegar
      </div>
    </div>
  );
}
