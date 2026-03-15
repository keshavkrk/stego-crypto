"""
OCR Engine — Extracts text with bounding boxes from document images.
Uses Tesseract via pytesseract with auto-detection on Windows.
"""
import os
import sys
import shutil

# Try to auto-detect and configure Tesseract before importing pytesseract
if sys.platform.startswith("win"):
    _common_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    ]
    for _p in _common_paths:
        if os.path.exists(_p):
            os.environ["PATH"] = os.path.dirname(_p) + ";" + os.environ.get("PATH", "")
            break

try:
    import pytesseract
    # Verify tesseract is actually available
    _tess_cmd = shutil.which("tesseract")
    if _tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = _tess_cmd
    elif sys.platform.startswith("win"):
        for _p in _common_paths:
            if os.path.exists(_p):
                pytesseract.pytesseract.tesseract_cmd = _p
                break
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

from PIL import Image


class TesseractNotInstalledError(Exception):
    """Raised when Tesseract OCR binary is not found on the system."""
    def __init__(self):
        super().__init__(
            "Tesseract OCR is not installed on your system.\n\n"
            "To install:\n"
            "1. Download from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Run the installer (choose 'Add to PATH' during setup)\n"
            "3. Restart this application\n\n"
            "The Manual Redact and Decrypt tabs work without Tesseract."
        )


class OCREngine:
    """Wraps Tesseract OCR to extract words with their pixel positions."""

    def __init__(self, lang="eng", min_confidence=40):
        self.lang = lang
        self.min_confidence = min_confidence

    def _check_tesseract(self):
        """Verify Tesseract is available before attempting OCR."""
        if not TESSERACT_AVAILABLE:
            raise TesseractNotInstalledError()
        # Double-check by trying to get the version
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            raise TesseractNotInstalledError()

    def extract_text_with_boxes(self, image_path):
        """
        Run OCR on an image and return every detected word with its bounding box.

        Returns:
            list of dicts: [
                {"text": "John", "x": 100, "y": 50, "w": 80, "h": 20, "confidence": 95},
                ...
            ]
        """
        self._check_tesseract()
        img = Image.open(image_path)
        data = pytesseract.image_to_data(img, lang=self.lang, output_type=pytesseract.Output.DICT)

        results = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])

            if not text or conf < self.min_confidence:
                continue

            results.append({
                "text": text,
                "x": data["left"][i],
                "y": data["top"][i],
                "w": data["width"][i],
                "h": data["height"][i],
                "confidence": conf
            })

        return results

    def extract_full_text(self, image_path):
        """Simple full-text OCR extraction (no bounding boxes)."""
        self._check_tesseract()
        img = Image.open(image_path)
        return pytesseract.image_to_string(img, lang=self.lang)
