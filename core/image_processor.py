"""
Image Processor — Handles visual redaction of document images.
Supports multi-region redaction with black fill or blur.
"""
import cv2
import numpy as np


class ImageProcessor:
    """Draws redaction boxes (black or blurred) on document images."""

    def draw_redaction_box(self, image_path, x, y, w, h):
        """
        Draw a single black redaction box on the image.
        Backward-compatible with the original API.

        Returns:
            numpy.ndarray: The modified image.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        self._validate_bounds(img, x, y, w, h)
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), -1)
        return img

    def draw_redaction_boxes(self, image_path, regions, mode="black"):
        """
        Draw multiple redaction boxes on the image.

        Args:
            image_path: Path to the source image.
            regions: List of dicts with keys: x, y, w, h.
            mode: "black" for solid fill, "blur" for Gaussian blur.

        Returns:
            numpy.ndarray: The modified image.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        for region in regions:
            x, y, w, h = region["x"], region["y"], region["w"], region["h"]

            # Clamp to image bounds
            img_h, img_w = img.shape[:2]
            x = max(0, x)
            y = max(0, y)
            w = min(w, img_w - x)
            h = min(h, img_h - y)

            if w <= 0 or h <= 0:
                continue

            if mode == "blur":
                roi = img[y:y + h, x:x + w]
                # Heavy blur to make text unreadable
                kernel_size = max(51, (min(w, h) // 2) | 1)  # Ensure odd
                blurred = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
                img[y:y + h, x:x + w] = blurred
            else:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 0), -1)

        return img

    def draw_highlight_boxes(self, image_path, regions, color=(0, 255, 0), thickness=2):
        """
        Draw colored outline boxes (for preview, not redaction).

        Args:
            image_path: Path to the source image.
            regions: List of dicts with keys: x, y, w, h.
            color: BGR color tuple.
            thickness: Line thickness in pixels.

        Returns:
            numpy.ndarray: The modified image with outlines.
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")

        for region in regions:
            x, y, w, h = region["x"], region["y"], region["w"], region["h"]
            cv2.rectangle(img, (x, y), (x + w, y + h), color, thickness)

        return img

    def save_image(self, img_object, output_path):
        """Save an image to disk."""
        cv2.imwrite(output_path, img_object)

    def _validate_bounds(self, img, x, y, w, h):
        """Validate that the box fits within the image."""
        img_h, img_w = img.shape[:2]
        if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
            raise ValueError(
                f"Redaction box ({x},{y},{w},{h}) exceeds image bounds ({img_w}×{img_h})."
            )