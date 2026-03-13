"""Tests for image preprocessing (padding to square)."""

import io

import numpy as np
from PIL import Image

from image_processing import pad_image_to_square


class TestPadImageToSquare:
    def test_landscape_image_becomes_square(self):
        """A wider-than-tall image should be padded vertically."""
        img = Image.new("RGB", (400, 200))  # 400w x 200h
        result = pad_image_to_square(img)
        assert result.width == result.height == 400

    def test_portrait_image_becomes_square(self):
        """A taller-than-wide image should be padded horizontally."""
        img = Image.new("RGB", (200, 400))  # 200w x 400h
        result = pad_image_to_square(img)
        assert result.width == result.height == 400

    def test_square_image_unchanged(self):
        """An already-square image should stay the same size."""
        img = Image.new("RGB", (300, 300))
        result = pad_image_to_square(img)
        assert result.width == result.height == 300

    def test_grayscale_converted_to_rgb(self):
        """A grayscale image should be converted to 3-channel RGB."""
        img = Image.new("L", (100, 100), color=128)
        result = pad_image_to_square(img)
        arr = np.array(result)
        assert len(arr.shape) == 3
        assert arr.shape[2] == 3

    def test_rgba_converted_to_rgb(self):
        """An RGBA image should be converted to 3-channel RGB."""
        img = Image.new("RGBA", (100, 100), color=(128, 128, 128, 255))
        result = pad_image_to_square(img)
        arr = np.array(result)
        assert len(arr.shape) == 3
        assert arr.shape[2] == 3

    def test_output_is_pil_image(self):
        img = Image.new("RGB", (200, 300))
        result = pad_image_to_square(img)
        assert isinstance(result, Image.Image)

    def test_padding_is_centered(self):
        """Padding should be roughly equal on both sides."""
        img = Image.new("RGB", (400, 200))  # needs 200px vertical padding
        result = pad_image_to_square(img)
        arr = np.array(result)
        # Top padding: 100px, bottom padding: 100px
        # Top-left corner should be padding (black = 0)
        assert arr[0, 0, 0] == 0  # top padding row
        assert arr[399, 0, 0] == 0  # bottom padding row
