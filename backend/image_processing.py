import numpy as np
from PIL import Image
import skimage.util
import skimage.color


def pad_image_to_square(image: Image.Image) -> Image.Image:
    """Pad image to square format for MedGemma preprocessing."""
    image_array = np.array(image)
    image_array = skimage.util.img_as_ubyte(image_array)

    if len(image_array.shape) < 3:
        image_array = skimage.color.gray2rgb(image_array)
    if image_array.shape[2] == 4:
        image_array = skimage.color.rgba2rgb(image_array)
        image_array = skimage.util.img_as_ubyte(image_array)

    h, w = image_array.shape[:2]
    max_dim = max(h, w)

    if h < w:
        dh = w - h
        image_array = np.pad(
            image_array, ((dh // 2, dh - dh // 2), (0, 0), (0, 0))
        )
    elif w < h:
        dw = h - w
        image_array = np.pad(
            image_array, ((0, 0), (dw // 2, dw - dw // 2), (0, 0))
        )

    return Image.fromarray(image_array)
