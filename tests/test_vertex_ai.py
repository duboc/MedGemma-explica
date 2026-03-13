"""Tests for vertex_ai module (prompt building, parsing, mocks)."""

import json

from vertex_ai import (
    ANATOMY_INFO,
    MOCK_BOUNDING_BOXES,
    build_prompt,
    get_educational_info,
    mock_predict,
    parse_bounding_boxes,
)


class TestBuildPrompt:
    def test_includes_object_name(self):
        prompt = build_prompt("right lung")
        assert "right lung" in prompt

    def test_includes_json_format_instructions(self):
        prompt = build_prompt("heart")
        assert "box_2d" in prompt
        assert "label" in prompt
        assert "Final Answer" in prompt

    def test_includes_patient_left_reminder(self):
        prompt = build_prompt("heart")
        assert "left" in prompt.lower()
        assert "patient" in prompt.lower()


class TestParseBoundingBoxes:
    def test_parses_valid_json_block(self):
        response = 'Some text\n```json[{"box_2d": [100, 200, 300, 400], "label": "heart"}]```\nMore text'
        boxes = parse_bounding_boxes(response)
        assert len(boxes) == 1
        assert boxes[0]["label"] == "heart"
        assert boxes[0]["box_2d"] == [100, 200, 300, 400]

    def test_uses_last_json_block(self):
        """When multiple json blocks exist (thinking + final answer), use the last one."""
        response = (
            '```json[{"box_2d": [0, 0, 10, 10], "label": "draft"}]```\n'
            'Final Answer:\n'
            '```json[{"box_2d": [100, 200, 300, 400], "label": "final"}]```'
        )
        boxes = parse_bounding_boxes(response)
        assert len(boxes) == 1
        assert boxes[0]["label"] == "final"

    def test_returns_empty_for_no_json(self):
        boxes = parse_bounding_boxes("No bounding boxes here.")
        assert boxes == []

    def test_returns_empty_for_invalid_json(self):
        boxes = parse_bounding_boxes("```json{not valid json}```")
        assert boxes == []

    def test_parses_multiple_boxes(self):
        data = [
            {"box_2d": [100, 100, 200, 200], "label": "heart"},
            {"box_2d": [50, 50, 300, 300], "label": "right lung"},
        ]
        response = f"```json{json.dumps(data)}```"
        boxes = parse_bounding_boxes(response)
        assert len(boxes) == 2


class TestMockPredict:
    def test_returns_known_structure(self):
        response_text, boxes = mock_predict("right lung")
        assert len(boxes) > 0
        assert boxes[0]["label"] == "right lung"
        assert "right lung" in response_text.lower()

    def test_returns_fallback_for_unknown_structure(self):
        response_text, boxes = mock_predict("some unknown structure")
        assert len(boxes) == 1
        assert boxes[0]["label"] == "some unknown structure"

    def test_all_known_structures_have_mocks(self):
        for name in ANATOMY_INFO:
            assert name in MOCK_BOUNDING_BOXES, f"Missing mock for {name}"

    def test_bounding_box_format(self):
        for name, boxes in MOCK_BOUNDING_BOXES.items():
            for box in boxes:
                coords = box["box_2d"]
                assert len(coords) == 4, f"Bad coords for {name}"
                y0, x0, y1, x1 = coords
                assert y0 < y1, f"y0 >= y1 for {name}"
                assert x0 < x1, f"x0 >= x1 for {name}"
                assert all(0 <= c <= 1000 for c in coords), f"Out of range for {name}"


class TestGetEducationalInfo:
    def test_exact_match(self):
        info = get_educational_info("heart")
        assert "cardíaca" in info["description"].lower() or "cardiac" in info["description"].lower()
        assert info["clinical_relevance"]

    def test_case_insensitive(self):
        info = get_educational_info("Right Lung")
        assert "lobos" in info["description"].lower() or "three lobes" in info["description"].lower()

    def test_partial_match(self):
        info = get_educational_info("lung")
        assert info["description"]  # should match one of the lung entries

    def test_unknown_structure_returns_fallback(self):
        info = get_educational_info("xyzzy")
        assert "xyzzy" in info["description"]
        assert info["clinical_relevance"]

    def test_all_anatomy_info_has_required_fields(self):
        for name, info in ANATOMY_INFO.items():
            assert "description" in info, f"Missing description for {name}"
            assert "clinical_relevance" in info, f"Missing clinical_relevance for {name}"
            assert len(info["description"]) > 10, f"Description too short for {name}"
