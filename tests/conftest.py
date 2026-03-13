"""Shared fixtures for MedGemma Explica tests."""

import io
import os
import sys

import pytest
from PIL import Image

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


@pytest.fixture
def sample_image_bytes() -> bytes:
    """Create a minimal test image in memory."""
    img = Image.new("RGB", (200, 300), color=(128, 128, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_image_rgba_bytes() -> bytes:
    """Create a minimal RGBA test image."""
    img = Image.new("RGBA", (150, 150), color=(128, 128, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def sample_image_grayscale_bytes() -> bytes:
    """Create a minimal grayscale test image."""
    img = Image.new("L", (100, 250), color=128)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
