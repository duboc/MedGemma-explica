"""Tests for deep_dive module (mock responses)."""

import json

from deep_dive import mock_deep_dive


class TestMockDeepDive:
    def test_has_required_top_level_fields(self):
        result = mock_deep_dive(["heart", "right lung"])
        assert "title" in result
        assert "level" in result
        assert "sections" in result
        assert "disclaimer" in result

    def test_default_level_is_medical_student(self):
        result = mock_deep_dive(["heart"])
        assert result["level"] == "medical_student"

    def test_custom_level(self):
        result = mock_deep_dive(["heart"], level="resident")
        assert result["level"] == "resident"

    def test_has_four_sections(self):
        result = mock_deep_dive(["heart"])
        sections = result["sections"]
        assert len(sections) == 4
        ids = [s["id"] for s in sections]
        assert "identification" in ids
        assert "normal_vs_abnormal" in ids
        assert "clinical_connections" in ids
        assert "study_tips" in ids

    def test_identification_section_has_key_points(self):
        result = mock_deep_dive(["heart"])
        section = next(s for s in result["sections"] if s["id"] == "identification")
        assert "key_points" in section
        assert len(section["key_points"]) >= 2
        for kp in section["key_points"]:
            assert "term" in kp
            assert "detail" in kp

    def test_normal_vs_abnormal_has_comparisons(self):
        result = mock_deep_dive(["right lung"])
        section = next(s for s in result["sections"] if s["id"] == "normal_vs_abnormal")
        assert "comparisons" in section
        assert len(section["comparisons"]) >= 1
        for comp in section["comparisons"]:
            assert "structure" in comp
            assert "normal" in comp
            assert "abnormal_signs" in comp
            assert "this_image" in comp

    def test_clinical_connections_has_connections(self):
        result = mock_deep_dive(["heart"])
        section = next(s for s in result["sections"] if s["id"] == "clinical_connections")
        assert "connections" in section
        assert len(section["connections"]) >= 3
        for conn in section["connections"]:
            assert "condition" in conn
            assert "relevance" in conn
            assert "what_to_look_for" in conn

    def test_study_tips_has_tips(self):
        result = mock_deep_dive(["heart"])
        section = next(s for s in result["sections"] if s["id"] == "study_tips")
        assert "tips" in section
        assert len(section["tips"]) >= 3
        for tip in section["tips"]:
            assert "tip" in tip
            assert "why" in tip

    def test_title_includes_structure_names(self):
        result = mock_deep_dive(["heart", "trachea"])
        assert "heart" in result["title"].lower()
        assert "trachea" in result["title"].lower()

    def test_each_section_has_icon(self):
        result = mock_deep_dive(["heart"])
        for section in result["sections"]:
            assert "icon" in section
            assert section["icon"]  # non-empty

    def test_is_json_serializable(self):
        result = mock_deep_dive(["heart", "right lung", "left lung"])
        serialized = json.dumps(result)
        assert len(serialized) > 100
