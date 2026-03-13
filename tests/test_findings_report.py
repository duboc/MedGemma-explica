"""Tests for findings_report module (mocks, fallback, JSON parsing)."""

import json

from findings_report import (
    _build_fallback_report,
    mock_findings_report,
    mock_structure_findings,
)


class TestMockFindingsReport:
    def test_has_required_sections(self):
        report = mock_findings_report(["heart", "right lung"])
        assert "overall_assessment" in report
        assert "systematic_approach" in report
        assert "pathology_scenarios" in report
        assert "clinical_pearls" in report
        assert "disclaimer" in report

    def test_overall_assessment_has_findings(self):
        report = mock_findings_report(["heart"])
        findings = report["overall_assessment"]["findings"]
        assert len(findings) >= 4
        for f in findings:
            assert "structure" in f
            assert "status" in f
            assert f["status"] in ("normal", "abnormal", "borderline")
            assert "finding" in f
            assert "detail" in f

    def test_systematic_approach_has_abcde(self):
        report = mock_findings_report(["heart"])
        steps = report["systematic_approach"]
        assert len(steps) == 5
        step_letters = [s["step"][0] for s in steps]
        assert step_letters == ["A", "B", "C", "D", "E"]

    def test_pathology_scenarios_has_entries(self):
        report = mock_findings_report(["heart"])
        scenarios = report["pathology_scenarios"]
        assert len(scenarios) >= 4
        for s in scenarios:
            assert "condition" in s
            assert "key_signs" in s
            assert len(s["key_signs"]) >= 2

    def test_clinical_pearls_has_categories(self):
        report = mock_findings_report(["heart"])
        pearls = report["clinical_pearls"]
        assert len(pearls) >= 3
        for p in pearls:
            assert "category" in p
            assert "items" in p
            assert len(p["items"]) >= 1

    def test_summary_includes_structure_names(self):
        report = mock_findings_report(["heart", "trachea"])
        summary = report["overall_assessment"]["summary"]
        assert "heart" in summary.lower() or "trachea" in summary.lower()

    def test_is_valid_json(self):
        report = mock_findings_report(["heart"])
        # Should be JSON-serializable
        serialized = json.dumps(report)
        assert len(serialized) > 100


class TestMockStructureFindings:
    def test_returns_one_per_structure(self):
        names = ["right lung", "heart", "trachea"]
        findings = mock_structure_findings(names)
        assert len(findings) == 3

    def test_known_structure_has_details(self):
        findings = mock_structure_findings(["heart"])
        f = findings[0]
        assert f["name"] == "heart"
        assert f["status"] in ("normal", "abnormal", "borderline")
        assert len(f["appearance"]) > 10
        assert len(f["clinical_note"]) > 10

    def test_unknown_structure_gets_fallback(self):
        findings = mock_structure_findings(["xyzzy"])
        f = findings[0]
        assert f["name"] == "xyzzy"
        assert f["status"] == "normal"

    def test_required_fields_present(self):
        findings = mock_structure_findings(["right lung", "left lung"])
        for f in findings:
            assert "name" in f
            assert "appearance" in f
            assert "status" in f
            assert "notable" in f
            assert "clinical_note" in f


class TestBuildFallbackReport:
    def test_has_required_structure(self):
        report = _build_fallback_report("Heart appears normal. Lungs are clear.")
        assert "overall_assessment" in report
        assert "systematic_approach" in report
        assert "disclaimer" in report

    def test_extracts_heart_mention(self):
        raw = "Heart: The cardiac silhouette is within normal limits with CTR of 0.45."
        report = _build_fallback_report(raw)
        findings = report["overall_assessment"]["findings"]
        heart_finding = next((f for f in findings if f["structure"] == "Heart"), None)
        assert heart_finding is not None
        assert "cardiac" in heart_finding["detail"].lower() or "normal" in heart_finding["detail"].lower()

    def test_summary_uses_first_paragraph(self):
        raw = "First paragraph here.\n\nSecond paragraph here."
        report = _build_fallback_report(raw)
        assert "First paragraph" in report["overall_assessment"]["summary"]

    def test_handles_empty_text(self):
        report = _build_fallback_report("")
        assert report["overall_assessment"]["summary"]
        assert report["disclaimer"]

    def test_raw_text_preserved(self):
        raw = "Full analysis text here."
        report = _build_fallback_report(raw)
        assert report.get("raw_text") == raw
