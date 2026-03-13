# CT Slice Viewer - Options & Implementation

## Context

The CT demo needs a way for users to browse CT slices visually before/after
analysis. Our backend already fetches rendered PNG frames from the Healthcare
API's DICOMweb `/rendered` endpoint. The viewer should let users scroll through
these slices to understand the CT volume.

## Option A: Custom PNG Slider (Implemented)

Uses the existing rendered PNG pipeline. Backend proxies frames, frontend
displays them with a scroll/slider control.

### Architecture

```
Healthcare API DICOM Store
    |
    | GET .../instances/{sop_uid}/rendered (Accept: image/png)
    v
Backend endpoint: GET /api/ct/frames/{series_id}
    |
    | JSON: { frames: ["base64...", ...], total_instances: N }
    v
Frontend: CTSliceViewer component
    - <img> displaying current slice
    - Range slider for navigation
    - Mouse wheel scrolling
    - Keyboard arrows
    - Slice counter (e.g. "15 / 50")
```

### Pros

- Zero new dependencies
- ~50 lines of React code
- No auth complexity (backend proxies all DICOMweb calls)
- Works with any browser (no WebGL/WASM requirements)
- Loads fast (PNGs are ~120 KB each, pre-rendered)
- Consistent with existing architecture

### Cons

- Fixed window/level (server default rendering)
- No zoom, pan, or measure tools
- No Hounsfield Unit values on hover
- Not a "real" DICOM viewer

### When this is enough

- Educational demos where users want to see what the AI analyzed
- Quick visual confirmation of CT content
- Mobile-friendly viewing

---

## Option B: Cornerstone3D (Future Upgrade)

Full DICOM rendering library with GPU-accelerated viewing and radiologist-grade
tools. This is the rendering engine behind OHIF Viewer.

### Packages Required

```bash
npm install @cornerstonejs/core @cornerstonejs/tools \
  @cornerstonejs/dicom-image-loader @cornerstonejs/streaming-image-volume-loader \
  dicomweb-client
```

Total added: ~1.5 MB (+ WASM codecs)

### Architecture

```
Healthcare API DICOM Store
    |
    | DICOMweb WADO-RS (raw DICOM, not rendered PNG)
    v
Browser (dicomweb-client with Bearer token)
    |
    | Raw DICOM pixel data
    v
Cornerstone3D (WebGL GPU rendering)
    - Window/level adjustment
    - Zoom, pan, scroll
    - Measurement tools (ruler, ellipse)
    - MPR (multiplanar reconstruction)
    - HU values on hover
```

### Integration Requirements

1. **Vite config changes** for web workers and WASM:
   ```typescript
   // vite.config.ts
   export default defineConfig({
     worker: { format: 'es' },
     optimizeDeps: {
       exclude: ['@cornerstonejs/dicom-image-loader'],
     },
   })
   ```

2. **Initialization boilerplate** (~50 lines):
   ```typescript
   import { init as csInit } from '@cornerstonejs/core'
   import { init as csToolsInit } from '@cornerstonejs/tools'
   import { init as dicomLoaderInit } from '@cornerstonejs/dicom-image-loader'

   await csInit()
   await csToolsInit()
   await dicomLoaderInit()
   ```

3. **Auth token management**: The browser calls the Healthcare API directly,
   so it needs a valid Bearer token. Options:
   - Backend endpoint that returns a short-lived token
   - Google Identity Services (OAuth2 in browser)
   - Backend proxy (negates the benefit of client-side rendering)

4. **Rendering setup** (~100 lines):
   ```typescript
   const renderingEngine = new RenderingEngine('ctViewer')
   const viewport = renderingEngine.enableElement({
     viewportId: 'CT_STACK',
     type: ViewportType.STACK,
     element: containerRef.current,
   })
   // Load image IDs from DICOMweb, set viewport, add tools...
   ```

### Pros

- Professional radiology-grade viewer
- Window/level control (critical for CT reading)
- Measurement and annotation tools
- GPU-accelerated rendering
- Proper DICOM metadata access

### Cons

- ~1.5 MB additional bundle size + WASM codecs
- Complex Vite configuration (workers, WASM)
- Auth token must reach the browser
- CORS configuration on Healthcare API may be needed
- Debugging WebGL/WASM issues is difficult
- Significant development effort (hours, not minutes)

### When to upgrade

- Users need to adjust window/level (e.g. lung vs mediastinal window)
- Measurement tools are required
- The app evolves toward a clinical training tool
- Users upload their own DICOM files

---

## Other Options Considered

### OHIF Viewer

- Full radiology workstation (~12.5 MB)
- Designed as standalone app, not embeddable component
- React version conflicts reported when embedding
- Overkill for an educational demo

### DWV (dwv / react-dwv)

- Medium weight (~7 MB)
- Primarily designed for local DICOM files
- DICOMweb auth support is poorly documented
- Fewer features than Cornerstone3D

### react-simple-image-viewer

- Lightweight (38 KB) image gallery
- Designed for photo galleries, not medical imaging
- No mouse wheel scrolling (critical for CT)
- Custom slider gives better UX with same effort

---

## Decision

Start with **Option A (Custom PNG Slider)** for the MVP. It leverages the
existing rendered-frame pipeline, requires zero new dependencies, and provides
a good educational experience. Document the Cornerstone3D upgrade path for
when advanced viewing features are needed.
