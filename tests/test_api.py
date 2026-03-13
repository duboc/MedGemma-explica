"""Tests for the FastAPI endpoints (mock mode only -- no GCP needed)."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def png_bytes():
    """Minimal PNG image for upload."""
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


class TestHealthAndMetadata:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_list_samples(self, client):
        r = client.get("/api/samples")
        assert r.status_code == 200
        samples = r.json()
        assert len(samples) >= 1
        assert "id" in samples[0]
        assert "url" in samples[0]

    def test_list_structures(self, client):
        r = client.get("/api/structures")
        assert r.status_code == 200
        structures = r.json()
        assert len(structures) >= 10
        for s in structures:
            assert "name" in s
            assert "description" in s
            assert "clinical_relevance" in s


class TestAnalyzeMock:
    def test_analyze_with_file(self, client, png_bytes):
        r = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["id"]
        assert data["object_name"] == "heart"
        assert len(data["bounding_boxes"]) >= 1
        assert data["image_url"].startswith("/uploads/")

    def test_analyze_with_sample(self, client):
        r = client.post(
            "/api/analyze",
            data={"object_name": "right lung", "mock": "true", "sample_id": "normal_pa"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["object_name"] == "right lung"

    def test_analyze_multi_structure(self, client, png_bytes):
        r = client.post(
            "/api/analyze",
            data={"object_name": "heart, right lung, trachea", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["bounding_boxes"]) >= 3
        assert len(data["structure_names"]) == 3
        assert len(data["educational_infos"]) == 3

    def test_analyze_no_image_fails(self, client):
        r = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
        )
        assert r.status_code == 400

    def test_analyze_no_structure_fails(self, client, png_bytes):
        r = client.post(
            "/api/analyze",
            data={"object_name": "", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert r.status_code in (400, 422)

    def test_analyze_too_many_structures(self, client, png_bytes):
        names = ", ".join([f"struct{i}" for i in range(9)])
        r = client.post(
            "/api/analyze",
            data={"object_name": names, "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        assert r.status_code == 400


class TestHistoryMock:
    def test_list_empty_initially(self, client):
        # Clear first
        client.delete("/api/analyses?mock=true")
        r = client.get("/api/analyses?mock=true")
        assert r.status_code == 200
        assert r.json() == []

    def test_analysis_appears_in_history(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        # Create an analysis
        client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        r = client.get("/api/analyses?mock=true")
        analyses = r.json()
        assert len(analyses) == 1
        assert analyses[0]["object_name"] == "heart"

    def test_get_single_analysis(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        r = client.get(f"/api/analyses/{doc_id}?mock=true")
        assert r.status_code == 200
        assert r.json()["id"] == doc_id

    def test_get_nonexistent_returns_404(self, client):
        r = client.get("/api/analyses/nonexistent123?mock=true")
        assert r.status_code == 404

    def test_delete_single(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        r = client.delete(f"/api/analyses/{doc_id}?mock=true")
        assert r.status_code == 200
        # Verify gone
        r = client.get("/api/analyses?mock=true")
        assert len(r.json()) == 0

    def test_clear_all(self, client, png_bytes):
        # Create two analyses
        for _ in range(2):
            client.post(
                "/api/analyze",
                data={"object_name": "heart", "mock": "true"},
                files={"file": ("test.png", png_bytes, "image/png")},
            )
        r = client.delete("/api/analyses?mock=true")
        assert r.status_code == 200
        r = client.get("/api/analyses?mock=true")
        assert len(r.json()) == 0


class TestPatchMock:
    def test_patch_deep_dive(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]

        r = client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"deep_dive": {"level": "medical_student", "explanation": "test"}},
        )
        assert r.status_code == 200
        assert "deep_dive" in r.json()["fields"]

        # Verify persisted
        r = client.get(f"/api/analyses/{doc_id}?mock=true")
        assert r.json()["deep_dive"]["level"] == "medical_student"

    def test_patch_adds_updated_at(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        # Initially no updated_at
        assert "updated_at" not in create.json()

        client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"chat_messages": [{"role": "user", "content": "hello"}]},
        )
        r = client.get(f"/api/analyses/{doc_id}?mock=true")
        assert "updated_at" in r.json()

    def test_patch_chat_messages(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        messages = [
            {"role": "user", "content": "What is the CTR?"},
            {"role": "assistant", "content": "The cardiothoracic ratio is..."},
        ]
        r = client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"chat_messages": messages},
        )
        assert r.status_code == 200

        r = client.get(f"/api/analyses/{doc_id}?mock=true")
        assert len(r.json()["chat_messages"]) == 2

    def test_patch_findings_report(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        r = client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"findings_report": {"overall_assessment": {"summary": "test"}}},
        )
        assert r.status_code == 200

        r = client.get(f"/api/analyses/{doc_id}?mock=true")
        assert r.json()["findings_report"]["overall_assessment"]["summary"] == "test"

    def test_patch_structure_findings(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        findings = [{"name": "heart", "status": "normal", "appearance": "ok", "notable": "", "clinical_note": ""}]
        r = client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"structure_findings": findings},
        )
        assert r.status_code == 200

        r = client.get(f"/api/analyses/{doc_id}?mock=true")
        assert len(r.json()["structure_findings"]) == 1

    def test_patch_invalid_field_rejected(self, client, png_bytes):
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        r = client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"object_name": "hacked"},
        )
        assert r.status_code == 400

    def test_patch_nonexistent_returns_404(self, client):
        r = client.patch(
            "/api/analyses/nonexistent123?mock=true",
            json={"deep_dive": {"level": "test"}},
        )
        assert r.status_code == 404

    def test_patched_fields_appear_in_list(self, client, png_bytes):
        """Verify PATCH'd fields show up when listing all analyses."""
        client.delete("/api/analyses?mock=true")
        create = client.post(
            "/api/analyze",
            data={"object_name": "heart", "mock": "true"},
            files={"file": ("test.png", png_bytes, "image/png")},
        )
        doc_id = create.json()["id"]
        client.patch(
            f"/api/analyses/{doc_id}?mock=true",
            json={"deep_dive": {"level": "resident", "explanation": "saved"}},
        )
        r = client.get("/api/analyses?mock=true")
        analyses = r.json()
        match = next(a for a in analyses if a["id"] == doc_id)
        assert match["deep_dive"]["level"] == "resident"


class TestMockEndpoints:
    def test_explain_mock(self, client):
        r = client.post(
            "/api/explain",
            json={
                "structure_names": ["heart"],
                "educational_infos": [{"description": "test", "clinical_relevance": "test"}],
                "level": "medical_student",
                "mock": True,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "explanation" in data
        assert "sections" in data["explanation"]

    def test_chat_mock(self, client):
        r = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "What is the CTR?"}],
                "structure_names": ["heart"],
                "educational_infos": [],
                "mock": True,
            },
        )
        assert r.status_code == 200
        assert "response" in r.json()

    def test_suggest_questions_mock(self, client):
        r = client.post(
            "/api/suggest-questions",
            json={
                "structure_names": ["heart"],
                "educational_infos": [],
                "mock": True,
            },
        )
        assert r.status_code == 200
        questions = r.json()["questions"]
        assert len(questions) >= 4

    def test_structure_findings_mock(self, client):
        r = client.post(
            "/api/structure-findings",
            json={
                "response_text": "test",
                "structure_names": ["right lung", "heart"],
                "mock": True,
            },
        )
        assert r.status_code == 200
        findings = r.json()["findings"]
        assert len(findings) == 2

    def test_findings_report_mock(self, client):
        r = client.post(
            "/api/findings-report",
            json={
                "structure_names": ["heart", "right lung"],
                "mock": True,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "overall_assessment" in data
        assert "systematic_approach" in data
