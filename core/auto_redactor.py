"""
Auto Redactor — Orchestrates OCR + PII Detection to find sensitive regions.
This is the brain of the automatic scanning pipeline.
"""
from core.ocr_engine import OCREngine
from core.pii_detector import PIIDetector


class AutoRedactor:
    """Scans a document image, detects PII, and returns redaction regions."""

    def __init__(self, lang="eng", min_confidence=40, extra_patterns=None):
        self.ocr = OCREngine(lang=lang, min_confidence=min_confidence)
        self.pii = PIIDetector(extra_patterns=extra_patterns)

    def scan_document(self, image_path):
        """
        Full pipeline: OCR → PII Detection → Region mapping.

        Args:
            image_path: Path to the document image.

        Returns:
            list of dicts: [
                {
                    "type": "Aadhaar Number",
                    "value": "1234 5678 9012",
                    "severity": "high",
                    "bbox": {"x": 100, "y": 50, "w": 200, "h": 30},
                    "confidence": 92,
                    "word_boxes": [...]  # individual word boxes that form this detection
                },
                ...
            ]
        """
        # Step 1: Extract all words with positions
        word_boxes = self.ocr.extract_text_with_boxes(image_path)

        if not word_boxes:
            return []

        # Step 2: Build a position-mapped text for multi-word PII detection
        # We need to reconstruct text lines and map character positions back to pixel boxes
        detections = []

        # --- Single-word PII detection ---
        for wb in word_boxes:
            pii_type = self.pii.detect_in_word(wb["text"])
            if pii_type:
                detections.append({
                    "type": pii_type,
                    "value": wb["text"],
                    "severity": self._get_severity(pii_type),
                    "bbox": {"x": wb["x"], "y": wb["y"], "w": wb["w"], "h": wb["h"]},
                    "confidence": wb["confidence"],
                    "word_boxes": [wb],
                })

        # --- Multi-word PII detection (e.g., "1234 5678 9012" as 3 separate words) ---
        # Group words by approximate line (similar y-coordinate)
        lines = self._group_into_lines(word_boxes)

        for line_words in lines:
            line_text = " ".join(w["text"] for w in line_words)
            pii_matches = self.pii.detect(line_text)

            for match in pii_matches:
                # Find which word boxes correspond to this match
                matched_boxes = self._find_matching_boxes(
                    line_words, line_text, match["start"], match["end"]
                )
                if matched_boxes and not self._is_duplicate(detections, matched_boxes):
                    merged_bbox = self._merge_boxes(matched_boxes)
                    detections.append({
                        "type": match["type"],
                        "value": match["value"],
                        "severity": match["severity"],
                        "bbox": merged_bbox,
                        "confidence": min(wb["confidence"] for wb in matched_boxes),
                        "word_boxes": matched_boxes,
                    })

        # Deduplicate overlapping detections
        detections = self._deduplicate(detections)

        return detections

    def _get_severity(self, pii_type):
        """Look up severity for a PII type name."""
        for p in self.pii.patterns:
            if p["name"] == pii_type:
                return p["severity"]
        return "medium"

    def _group_into_lines(self, word_boxes, y_threshold=15):
        """Group word boxes into lines based on y-coordinate proximity."""
        if not word_boxes:
            return []

        sorted_boxes = sorted(word_boxes, key=lambda b: (b["y"], b["x"]))
        lines = []
        current_line = [sorted_boxes[0]]

        for wb in sorted_boxes[1:]:
            if abs(wb["y"] - current_line[0]["y"]) <= y_threshold:
                current_line.append(wb)
            else:
                lines.append(sorted(current_line, key=lambda b: b["x"]))
                current_line = [wb]

        if current_line:
            lines.append(sorted(current_line, key=lambda b: b["x"]))

        return lines

    def _find_matching_boxes(self, line_words, line_text, start, end):
        """Map character positions in the joined line text back to word boxes."""
        matched = []
        char_pos = 0

        for w in line_words:
            word_start = char_pos
            word_end = char_pos + len(w["text"])

            # Check if this word overlaps with the match span
            if word_end > start and word_start < end:
                matched.append(w)

            char_pos = word_end + 1  # +1 for the space between words

        return matched

    def _merge_boxes(self, boxes):
        """Merge multiple bounding boxes into one enclosing box with padding."""
        if not boxes:
            return {"x": 0, "y": 0, "w": 0, "h": 0}

        padding = 4  # pixels of padding around merged region
        x_min = min(b["x"] for b in boxes) - padding
        y_min = min(b["y"] for b in boxes) - padding
        x_max = max(b["x"] + b["w"] for b in boxes) + padding
        y_max = max(b["y"] + b["h"] for b in boxes) + padding

        return {
            "x": max(0, x_min),
            "y": max(0, y_min),
            "w": x_max - max(0, x_min),
            "h": y_max - max(0, y_min),
        }

    def _is_duplicate(self, existing_detections, new_boxes):
        """Check if these word boxes are already covered by an existing detection."""
        new_set = set((b["x"], b["y"], b["w"], b["h"]) for b in new_boxes)
        for det in existing_detections:
            existing_set = set(
                (b["x"], b["y"], b["w"], b["h"]) for b in det["word_boxes"]
            )
            if new_set.issubset(existing_set) or new_set == existing_set:
                return True
        return False

    def _deduplicate(self, detections):
        """Remove detections whose bboxes are fully contained within another."""
        if len(detections) <= 1:
            return detections

        result = []
        for i, det in enumerate(detections):
            is_contained = False
            for j, other in enumerate(detections):
                if i == j:
                    continue
                if self._bbox_contains(other["bbox"], det["bbox"]) and i > j:
                    is_contained = True
                    break
            if not is_contained:
                result.append(det)

        return result

    def _bbox_contains(self, outer, inner):
        """Check if outer bbox fully contains inner bbox."""
        return (
            outer["x"] <= inner["x"]
            and outer["y"] <= inner["y"]
            and outer["x"] + outer["w"] >= inner["x"] + inner["w"]
            and outer["y"] + outer["h"] >= inner["y"] + inner["h"]
        )
