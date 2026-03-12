"""
PII Detector — Identifies sensitive information in text using regex patterns.
Supports Indian document formats + universal patterns.
"""
import re


# ─── Pattern Definitions ─────────────────────────────────────────────────────
# Each pattern is a dict with:
#   name      — Human-readable label for the UI
#   pattern   — Compiled regex
#   severity  — "high" | "medium" | "low" (controls default check state in UI)
#   validator — Optional callable for extra validation (e.g., Luhn check)

def _luhn_check(number_str):
    """Validate a credit card number using the Luhn algorithm."""
    digits = [int(d) for d in number_str if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    reverse = digits[::-1]
    for i, d in enumerate(reverse):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


PII_PATTERNS = [
    {
        "name": "Aadhaar Number",
        "pattern": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        "severity": "high",
        "validator": lambda m: len(re.sub(r"[\s\-]", "", m)) == 12,
    },
    {
        "name": "PAN Card",
        "pattern": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
        "severity": "high",
        "validator": None,
    },
    {
        "name": "Indian Phone",
        "pattern": re.compile(r"(?:\+91[\s\-]?)?(?:\(?0?\)?[\s\-]?)?\b[6-9]\d{4}[\s\-]?\d{5}\b"),
        "severity": "high",
        "validator": None,
    },
    {
        "name": "Email Address",
        "pattern": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "severity": "medium",
        "validator": None,
    },
    {
        "name": "Credit Card",
        "pattern": re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),
        "severity": "high",
        "validator": lambda m: _luhn_check(m),
    },
    {
        "name": "Date (DD/MM/YYYY)",
        "pattern": re.compile(
            r"\b(?:0?[1-9]|[12]\d|3[01])[/\-.](?:0?[1-9]|1[0-2])[/\-.](?:19|20)\d{2}\b"
        ),
        "severity": "low",
        "validator": None,
    },
    {
        "name": "Date (YYYY-MM-DD)",
        "pattern": re.compile(
            r"\b(?:19|20)\d{2}[/\-.](?:0?[1-9]|1[0-2])[/\-.](?:0?[1-9]|[12]\d|3[01])\b"
        ),
        "severity": "low",
        "validator": None,
    },
    {
        "name": "Indian Passport",
        "pattern": re.compile(r"\b[A-Z]\d{7}\b"),
        "severity": "high",
        "validator": None,
    },
    {
        "name": "Indian Pincode",
        "pattern": re.compile(r"\b[1-9]\d{5}\b"),
        "severity": "low",
        "validator": None,
    },
]


class PIIDetector:
    """Detects personally identifiable information in text."""

    def __init__(self, extra_patterns=None):
        """
        Args:
            extra_patterns: Optional list of additional pattern dicts to include.
        """
        self.patterns = list(PII_PATTERNS)
        if extra_patterns:
            self.patterns.extend(extra_patterns)

    def detect(self, text):
        """
        Scan text for all PII matches.

        Args:
            text: The string to scan.

        Returns:
            list of dicts: [
                {"type": "Aadhaar Number", "value": "1234 5678 9012",
                 "start": 10, "end": 24, "severity": "high"},
                ...
            ]
        """
        detections = []

        for pattern_def in self.patterns:
            for match in pattern_def["pattern"].finditer(text):
                value = match.group()

                # Run optional validator
                if pattern_def["validator"] and not pattern_def["validator"](value):
                    continue

                detections.append({
                    "type": pattern_def["name"],
                    "value": value,
                    "start": match.start(),
                    "end": match.end(),
                    "severity": pattern_def["severity"],
                })

        # Remove duplicates (same value at same position from overlapping patterns)
        seen = set()
        unique = []
        for d in detections:
            key = (d["start"], d["end"], d["type"])
            if key not in seen:
                seen.add(key)
                unique.append(d)

        return unique

    def detect_in_word(self, word):
        """
        Quick check: does this single word (or short phrase) contain PII?
        Returns the first matching pattern name, or None.
        """
        for pattern_def in self.patterns:
            if pattern_def["pattern"].search(word):
                validator = pattern_def["validator"]
                if validator is None or validator(word):
                    return pattern_def["name"]
        return None
