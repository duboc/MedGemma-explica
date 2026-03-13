# UI Restructuring Plan: Structured JSON Everywhere

## Problem

The current UI has inconsistent data quality across tabs:

| Tab | Data Source | Rendering | Quality |
|-----|-----------|-----------|---------|
| **Findings** | Static `ANATOMY_INFO` dict | Simple edu-cards | Very basic, no image-specific info |
| **Full Report** | MedGemma -> Gemini Flash JSON | Structured cards, grids, badges | Good |
| **Deep Dive** | MedGemma raw markdown | Client-side regex parsing | Broken - empty sections, lost content |
| **Q&A Chat** | MedGemma raw markdown | Client-side markdown->HTML | Acceptable but plain |

The **Full Report** tab already proves the pattern works: MedGemma analyzes the image (raw text), then Gemini Flash structures it into JSON with a strict schema. The UI renders structured JSON into rich cards, badges, grids, and collapsible sections.

The problem is that **Deep Dive** and **Findings** don't use this pattern. They either parse flaky markdown or show static info.

## Solution: Apply the Two-Step Pipeline Everywhere

```
MedGemma (vision) --> raw text --> Gemini Flash (JSON structuring) --> structured JSON --> Rich UI
```

### What Changes

1. **Deep Dive**: Replace client-side markdown parsing with a backend Gemini Flash JSON structuring step (same pattern as Findings Report)
2. **Findings tab**: Enrich with image-specific observations from the initial analysis (already have `response_text` from MedGemma)
3. **Chat**: Keep markdown rendering (appropriate for conversational UI) but render MedGemma artifacts more cleanly

---

## Phase 1: Deep Dive - Structured JSON

### Backend: New endpoint behavior for `/api/explain`

**Current flow:**
```
MedGemma prompt -> raw markdown text -> return { explanation: "markdown string" }
```

**New flow:**
```
MedGemma prompt -> raw text -> Gemini Flash structures -> return { explanation: { structured JSON } }
```

### JSON Schema for Deep Dive

```json
{
  "title": "Educational Deep Dive: Right Lung, Heart",
  "level": "medical_student",
  "sections": [
    {
      "id": "identification",
      "title": "What You're Seeing",
      "icon": "eye",
      "content": "paragraph of explanation",
      "key_points": [
        { "term": "Right lung", "detail": "Three lobes visible..." },
        { "term": "Heart shadow", "detail": "Normal CTR..." }
      ]
    },
    {
      "id": "normal_vs_abnormal",
      "title": "Normal vs. Abnormal",
      "icon": "balance",
      "comparisons": [
        {
          "structure": "Right Lung",
          "normal": "Clear lung fields, sharp costophrenic angle",
          "abnormal_signs": ["Consolidation", "Effusion", "Mass"],
          "this_image": "Appears normal with clear fields"
        }
      ]
    },
    {
      "id": "clinical_connections",
      "title": "Clinical Connections",
      "icon": "stethoscope",
      "connections": [
        {
          "condition": "Pneumonia",
          "relevance": "Right lung is common site for aspiration pneumonia",
          "what_to_look_for": "Consolidation, air bronchograms"
        }
      ]
    },
    {
      "id": "study_tips",
      "title": "Study Tips",
      "icon": "lightbulb",
      "tips": [
        { "tip": "Always compare left and right", "why": "Asymmetry reveals pathology" }
      ]
    }
  ],
  "disclaimer": "For educational purposes only."
}
```

### Frontend: Replace ExplainPanel

- Remove `parseMarkdownSections()` usage
- Remove `dangerouslySetInnerHTML`
- Render structured JSON into typed React components (like FindingsReport already does)
- Reuse the `SectionWrapper` collapsible pattern from FindingsReport

### Type changes

```typescript
// Old
deep_dive?: { level: string; explanation: string };

// New
deep_dive?: { level: string; explanation: DeepDiveResult };
```

---

## Phase 2: Enriched Findings Tab

### Problem
The Findings tab currently shows only static `ANATOMY_INFO` text (hardcoded descriptions). It doesn't reflect what MedGemma actually observed on THIS specific image.

### Solution
After MedGemma localizes structures (bounding boxes), use Gemini Flash to extract image-specific observations into structured JSON. This happens during the `/api/analyze` call itself.

### New field in analysis result

```json
{
  "structure_findings": [
    {
      "name": "right lung",
      "location_description": "Occupies the right hemithorax from apex to base",
      "appearance": "Clear lung fields with normal vascular markings",
      "status": "normal",
      "notable": "Sharp right costophrenic angle, no masses or consolidation",
      "clinical_note": "Common site for aspiration pneumonia due to wider right main bronchus"
    }
  ]
}
```

### Backend approach

Use the existing `response_text` from MedGemma (which contains the localization reasoning) and pass it through Gemini Flash to extract per-structure observations.

### Frontend: Rich Findings cards

Replace the current static edu-cards with richer cards that show:
- Structure name + status badge (normal/abnormal/borderline)
- What MedGemma observed on THIS image
- Anatomy description (from ANATOMY_INFO)
- Clinical relevance
- Clickable to highlight the bounding box on the image

---

## Phase 3: Chat Improvements

### Keep markdown for chat (it's natural for conversation)

But improve the rendering:
- Strip `<thought>` blocks more reliably (already done in `cleanMedGemmaOutput`)
- For the **first assistant message** in a conversation, consider asking Gemini Flash to structure the response if it's long (optional enhancement)
- Better empty state with image-specific suggested questions (already implemented)

### No schema change needed for chat

Chat stays as `ChatMessage[]` with string content. The markdown renderer (`renderMarkdownToHtml`) handles display.

---

## Implementation Order

### Step 1: Deep Dive backend (highest impact)
1. Add `DEEP_DIVE_STRUCTURE_PROMPT` to `findings_report.py` (or new `deep_dive.py`)
2. Add `_structure_deep_dive()` function using `_call_gemini`
3. Update `/api/explain` endpoint to return structured JSON instead of raw markdown
4. Update mock to return structured JSON

### Step 2: Deep Dive frontend
1. Define `DeepDiveResult` TypeScript interface
2. Rewrite `ExplainPanel.tsx` to render structured JSON (similar to FindingsReport)
3. Update `AnalysisResult.deep_dive` type
4. Add CSS for new deep dive cards

### Step 3: Enriched Findings
1. Add Gemini Flash structuring step to `/api/analyze` (after bounding boxes)
2. Define `StructureFinding` interface
3. Rewrite Findings tab in ResultViewer to show rich cards
4. Add CSS for finding cards with status badges

### Step 4: Cleanup
1. Remove `utils/markdown.ts` `parseMarkdownSections()` (no longer needed)
2. Remove `SECTION_ICONS` from ExplainPanel
3. Remove unused CSS classes (`.dd-card-*` if fully replaced)
4. Keep `renderMarkdownToHtml` for chat messages only

---

## Files to Modify

### Backend
- `backend/findings_report.py` (or new `backend/deep_dive.py`) - Add deep dive JSON schema + structuring
- `backend/main.py` - Update `/api/explain` to return structured JSON; optionally enrich `/api/analyze`
- `backend/gemini_flash.py` - Update `mock_explain` to return structured JSON

### Frontend
- `frontend/src/types/index.ts` - Add `DeepDiveResult`, `StructureFinding` interfaces
- `frontend/src/components/ExplainPanel.tsx` - Full rewrite for structured JSON
- `frontend/src/components/ResultViewer.tsx` - Enrich Findings tab
- `frontend/src/App.css` - New styles for deep dive structured cards
- `frontend/src/utils/markdown.ts` - Remove `parseMarkdownSections`, keep `renderMarkdownToHtml`
- `frontend/src/hooks/useApi.ts` - Update return types

---

## Key Design Decisions

1. **Gemini Flash for structuring, not generation** - MedGemma sees the image and generates the medical content. Gemini Flash only reformats text into JSON. This keeps medical accuracy from the vision model.

2. **Strict JSON schemas** - Each endpoint has a well-defined schema. If Gemini fails to parse, fall back to a simple structure with the raw text (like FindingsReport already does).

3. **No dangerouslySetInnerHTML for structured content** - Structured JSON renders through React components. Only chat messages (which are conversational text) use the markdown renderer.

4. **Backward compatibility** - Old analyses stored with `deep_dive.explanation` as a string still load. The frontend checks the type and falls back to plain text display.
