# Plan: Firestore Persistence & Brazilian Portuguese Translation

## Overview

Two parallel workstreams:

1. **Firestore Persistence** -- save all generated content (findings, reports, deep dives, chat) to Firestore and improve history reloading so users can resume exactly where they left off
2. **Brazilian Portuguese** -- translate the entire UI and AI prompts to pt-BR, validated by the experiment in `experiments/pt_br_medgemma_test.py`

---

## Part 1: Firestore Persistence & History

### Current State

**What's saved to Firestore today:**
- `id`, `image_blob_path`, `object_name`, `response_text`, `bounding_boxes`, `image_width`, `image_height`, `created_at`, `structure_names`, `educational_infos`

**What's saved via PATCH (after initial analysis):**
- `deep_dive`, `findings_report`, `chat_messages`, `structure_findings`

**What's broken or missing:**
- History panel loads the list from `/api/analyses` but only gets the base fields -- sub-results (`deep_dive`, `findings_report`, etc.) are only loaded if the user generated them in the current session
- When clicking a history card, `App.tsx` sets the result from the history list item, but that item doesn't include the PATCH'd fields -- so previously generated reports/chats/findings are lost on reload
- No `updated_at` timestamp -- can't tell when content was last modified
- Mock mode uses in-memory store that doesn't persist across restarts
- The `GET /api/analyses` list endpoint doesn't return PATCH'd fields (they exist in Firestore but aren't included in the list response)

### Plan

#### Step 1: Backend -- Include all fields in list/detail endpoints

**File: `backend/firestore_db.py`**
- No changes needed -- Firestore already stores and returns all fields on a document. The `list_analyses()` and `get_analysis()` functions return the full document.

**File: `backend/main.py`**
- `GET /api/analyses` (list): Already returns full documents from Firestore. Verify that PATCH'd fields (`deep_dive`, `findings_report`, `chat_messages`, `structure_findings`) are included in the response. They should be since `list_analyses()` returns `doc.to_dict()`.
- `GET /api/analyses/{id}` (detail): Same verification.
- The mock in-memory store (`_mock_analyses`) needs the same treatment -- when PATCH updates `_mock_analyses[i]`, the list endpoint should return those fields too. Verify mock PATCH actually mutates the in-memory entry.
- Add `updated_at` timestamp on every PATCH operation.

#### Step 2: Frontend -- Reload full analysis on history select

**File: `frontend/src/App.tsx`**
- `handleHistorySelect()` currently sets `result` from the list item. Change it to fetch the full analysis via `fetchAnalysis(id, mockMode)` to get all PATCH'd fields.
- This ensures that clicking a history card loads deep_dive, findings_report, chat_messages, and structure_findings.

**File: `frontend/src/components/HistoryPanel.tsx`**
- Add visual indicators for what content exists on each history card:
  - Small icons/dots showing which tabs have saved content (findings, report, deep dive, chat)
  - Show `updated_at` if available, otherwise `created_at`

#### Step 3: Frontend -- Restore tab state from saved data

**File: `frontend/src/components/ResultViewer.tsx`**
- `FindingsTab`: Already checks `result.structure_findings` and skips the API call if data exists. No change needed.
- The tab dot indicators (`savedMap`) already work from the result object. Just need the full result to be loaded.

**File: `frontend/src/components/ExplainPanel.tsx`**
- Already initializes from `result.deep_dive` via `isStructuredResult()`. No change needed.

**File: `frontend/src/components/FindingsReport.tsx`**
- Already initializes from `result.findings_report`. No change needed.

**File: `frontend/src/components/ChatPanel.tsx`**
- Already initializes from `result.chat_messages`. No change needed.

#### Step 4: Auto-save on every generation

Currently, `onSave` callbacks in ResultViewer trigger `updateAnalysis()` PATCH calls. Verify these work correctly:

- `FindingsTab` -> saves `structure_findings` -- working
- `FindingsReport` -> saves `findings_report` -- working
- `ExplainPanel` -> saves `deep_dive` -- working
- `ChatPanel` -> saves `chat_messages` -- working

No changes needed here, just verification.

#### Step 5: History UX improvements

**File: `frontend/src/components/HistoryPanel.tsx`**
- Show structure count and names on each card (currently only shows `object_name`)
- Add a "has content" indicator per tab type (small colored dots)
- Format dates in pt-BR locale (ties into Part 2)

**File: `frontend/src/App.css`**
- Style the content indicators on history cards

### Summary of changes (Part 1)

| File | Change |
|------|--------|
| `backend/main.py` | Verify list/detail return all PATCH'd fields; add `updated_at` to PATCH; verify mock store mutation |
| `frontend/src/App.tsx` | `handleHistorySelect` fetches full analysis via API instead of using list item |
| `frontend/src/components/HistoryPanel.tsx` | Add content indicators, show structure names, improve date display |
| `frontend/src/App.css` | Style history card content indicators |

---

## Part 2: Brazilian Portuguese Translation

### Current State

- Zero i18n infrastructure -- all strings hardcoded in English across components
- Backend prompts (MedGemma, Gemini Flash) all in English
- `ANATOMY_INFO` dictionary in `vertex_ai.py` has English names and descriptions
- Experiment (`experiments/pt_br_medgemma_test.py`) confirmed MedGemma handles pt-BR well:
  - Educational explanations: fluent pt-BR with all sections
  - Q&A chat: correct medical terminology in Portuguese
  - Bounding box labels: returned in Portuguese when prompted in Portuguese

### Approach: Hardcoded pt-BR (no i18n library)

Since the app targets a single audience (Brazilian Portuguese speakers), we'll do a direct translation rather than introducing an i18n framework. This keeps things simple -- no `react-i18next`, no JSON translation files, no language switcher. Just replace English strings with Portuguese.

If multi-language support is needed later, we can refactor to an i18n library at that point.

### Plan

#### Step 1: Frontend UI strings

Translate all user-visible strings in each component:

**`frontend/src/components/Header.tsx`**
- "MedGemma Explica" -> keep as-is (brand name)
- Subtitle and any UI labels -> Portuguese

**`frontend/src/components/StructureSelector.tsx`**
- Group names: "Lungs & Airways" -> "Pulmoes e Vias Aereas", etc.
- Structure names: "right lung" -> "pulmao direito", etc.
- Button labels: "Analyze Selected Structures" -> "Analisar Estruturas Selecionadas"
- Note: Structure names sent to MedGemma must stay in English (the model expects English anatomy terms for localization). Display in Portuguese, send in English.

**`frontend/src/components/ImageUploader.tsx`**
- All upload labels, drag-and-drop text, error messages

**`frontend/src/components/SamplePicker.tsx`**
- Sample image names and descriptions

**`frontend/src/components/ResultViewer.tsx`**
- Tab labels: "Findings" -> "Achados", "Full Report" -> "Relatorio Completo", "Deep Dive" -> "Aprofundamento", "Q&A Chat" -> "Perguntas e Respostas"
- Status badges: "Normal", "Abnormal" -> "Anormal", "Borderline" -> "Limítrofe"
- All section headers and labels

**`frontend/src/components/ExplainPanel.tsx`**
- Level labels: "Pre-Med" -> "Pre-Medicina", "Medical Student" -> "Estudante de Medicina", "Resident" -> "Residente", "Attending" -> "Medico Assistente"
- Button text, section headers

**`frontend/src/components/FindingsReport.tsx`**
- All section titles, intro text, button labels
- Status labels

**`frontend/src/components/ChatPanel.tsx`**
- Header, placeholder text, suggestion cards, send button
- Fallback questions in Portuguese

**`frontend/src/components/HistoryPanel.tsx`**
- "Analysis History" -> "Historico de Analises"
- "Clear All" -> "Limpar Tudo"
- Date formatting with pt-BR locale

**`frontend/src/components/Disclaimer.tsx`**
- Educational disclaimer text

**`frontend/src/App.tsx`**
- Error messages, loading states, button labels

#### Step 2: Backend prompts -- MedGemma

**`backend/vertex_ai.py`**
- `build_prompt()`: Keep in English -- MedGemma's localization works best with English prompts for bounding box generation. The labels will be mapped to Portuguese on the frontend.
- `explain_with_medgemma()`: Add "Responda em portugues brasileiro." to the prompt. The experiment showed this works perfectly.
- `chat_with_medgemma()`: Add "Responda em portugues brasileiro." to the system prompt.
- `suggest_questions_with_medgemma()`: Add "Gere as perguntas em portugues brasileiro." to the prompt.
- `ANATOMY_INFO`: Add `name_pt` and `description_pt` fields to each entry for display, keep English names as dictionary keys for MedGemma.

**`backend/findings_report.py`**
- `MEDGEMMA_PROMPT`: Add "Respond in Brazilian Portuguese." -- MedGemma generates raw analysis text.
- `GEMINI_STRUCTURE_PROMPT`: Add "All text values must be in Brazilian Portuguese." -- Gemini structures into JSON.
- `STRUCTURE_FINDINGS_PROMPT`: Same Portuguese instruction.

**`backend/deep_dive.py`**
- `GEMINI_STRUCTURE_PROMPT`: Add "All text values in the JSON must be in Brazilian Portuguese."

**`backend/gemini_flash.py`**
- `SYSTEM_INSTRUCTION`: Add Portuguese instruction.
- `explain_analysis()`: Add Portuguese to prompt.
- `chat_about_analysis()`: Add Portuguese to system prompt.

#### Step 3: Backend -- Anatomy display names

**`backend/vertex_ai.py`**
- Add `name_pt` to each `ANATOMY_INFO` entry:
  ```python
  "right lung": {
      "name_pt": "Pulmao Direito",
      "description": "...",          # keep English for MedGemma
      "description_pt": "...",       # Portuguese for UI display
      "clinical_relevance": "...",   # keep English for MedGemma
      "clinical_relevance_pt": "..." # Portuguese for UI display
  }
  ```

**`backend/main.py`**
- `GET /api/structures`: Return both English key and Portuguese display name
- Analysis response: Include Portuguese names alongside English for frontend display

**`frontend/src/types/index.ts`**
- Add `name_pt?` and `description_pt?` fields to `EducationalInfo`

#### Step 4: Structure name mapping

The critical design decision: **MedGemma localization prompts must use English anatomy names** (e.g., "right lung") because the model was trained on English medical text. But the UI should show Portuguese.

Create a mapping layer:
- Backend sends both `name` (English, for MedGemma) and `name_pt` (Portuguese, for display)
- Frontend always displays `name_pt` when available
- Bounding box labels from MedGemma come in English -- map them to Portuguese using the same dictionary

#### Step 5: Mock mode responses

**`backend/vertex_ai.py`**
- `mock_predict()`: Keep English labels (matches real MedGemma behavior)

**`backend/findings_report.py`**
- `mock_findings_report()`: Translate to Portuguese
- `mock_structure_findings()`: Translate to Portuguese

**`backend/deep_dive.py`**
- `mock_deep_dive()`: Translate to Portuguese

**`backend/gemini_flash.py`**
- `mock_explain()`: Translate to Portuguese
- `mock_chat()`: Translate to Portuguese

### Summary of changes (Part 2)

| File | Change |
|------|--------|
| `frontend/src/components/*.tsx` (all) | Replace English strings with Portuguese |
| `frontend/src/App.tsx` | Translate error messages, labels |
| `backend/vertex_ai.py` | Add `name_pt`, `description_pt`, `clinical_relevance_pt` to ANATOMY_INFO; add pt-BR to explain/chat/suggest prompts |
| `backend/findings_report.py` | Add pt-BR instruction to all prompts; translate mock data |
| `backend/deep_dive.py` | Add pt-BR instruction to Gemini prompt; translate mock data |
| `backend/gemini_flash.py` | Add pt-BR to system instructions; translate mock responses |
| `backend/main.py` | Return Portuguese names in API responses |
| `frontend/src/types/index.ts` | Add `name_pt`, `description_pt` optional fields |

---

## Implementation Order

| Phase | Work | Dependencies |
|-------|------|-------------|
| **1a** | Backend: verify Firestore returns all PATCH'd fields, add `updated_at` | None |
| **1b** | Frontend: fetch full analysis on history select | 1a |
| **1c** | Frontend: history card content indicators | 1b |
| **2a** | Backend: add pt-BR fields to ANATOMY_INFO | None |
| **2b** | Backend: add pt-BR instructions to all prompts | None |
| **2c** | Backend: translate mock responses | None |
| **2d** | Frontend: translate all component strings | 2a (needs pt names) |
| **2e** | Backend: return pt-BR names in API responses | 2a |

Phases 1 and 2 are independent and can be worked in parallel. Within each phase, steps are sequential.

---

## Risks & Decisions

1. **MedGemma localization accuracy in pt-BR**: The experiment showed bounding box localization works best with English prompts. We keep English for localization, Portuguese for everything else.

2. **No i18n library**: Hardcoding Portuguese is simpler but makes adding other languages harder later. Acceptable tradeoff for now since the target audience is Brazilian.

3. **Bounding box label mapping**: MedGemma returns English labels ("right lung"). We need a consistent mapping to Portuguese ("Pulmao Direito") on the frontend. The `ANATOMY_INFO` dictionary is the source of truth.

4. **Firestore migration**: Existing documents won't have `updated_at` or Portuguese fields. The frontend must handle missing fields gracefully (already does with optional types).

5. **Mock mode consistency**: Mock responses should match the language of real responses (Portuguese) to avoid confusion during testing.
