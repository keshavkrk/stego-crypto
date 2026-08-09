# Stego-Crypt — SecureGuard AI

SecureGuard AI is a Python desktop application for **controlled document redaction, sensitive-information detection, encryption, and secure restoration**.

The central idea is different from ordinary destructive redaction: instead of permanently discarding the original sensitive information, SecureGuard AI can hide the selected information from the visible document while preserving an encrypted copy that an authorized user can later restore with the correct password.

The project combines:

- OCR-based document analysis
- Pattern-based PII detection
- Image processing and redaction
- PDF rendering and reconstruction
- Password-based authenticated encryption
- LSB image steganography
- A desktop GUI built with CustomTkinter

The application is organized into reusable core modules and a graphical interface, making the individual stages independently understandable and testable.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Application Architecture](#application-architecture)
- [End-to-End Workflow](#end-to-end-workflow)
- [Smart Scan](#smart-scan)
- [PII Detection](#pii-detection)
- [Controlled Redaction](#controlled-redaction)
- [Cryptography](#cryptography)
- [Steganography](#steganography)
- [PDF Processing](#pdf-processing)
- [Restoration](#restoration)
- [GUI](#gui)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Installation](#installation)
- [Tesseract OCR Setup](#tesseract-ocr-setup)
- [Running the Application](#running-the-application)
- [Core Modules](#core-modules)
- [Security Design](#security-design)
- [Data Flow](#data-flow)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Important Limitations](#important-limitations)
- [Future Improvements](#future-improvements)
- [Security Notes](#security-notes)

---

# Project Overview

SecureGuard AI provides three main workflows through its desktop interface:

```text
+--------------------+
|    SecureGuard AI  |
+---------+----------+
          |
    +-----+-----+----------------+
    |           |                |
    v           v                v
 Smart Scan   Draw & Redact    Restore
    |           |                |
    v           v                v
 OCR + PII    Manual regions   Password
 detection    + redaction      + decrypt
    |           |                |
    +-----+-----+----------------+
          |
          v
    Protected Document
```

### Smart Scan

Automatically analyzes a document image using OCR and pattern-based PII detection. Detected sensitive regions are returned with their type, severity, confidence, and bounding box so the user can review them before redaction.

### Draw & Redact

Allows the user to manually select regions of a document when automatic detection is insufficient or when the user wants explicit control over what is protected.

### Restore

Uses the correct password to decrypt the protected information and reconstruct the original document content.

---

# Key Features

## Automatic sensitive-data detection

The Smart Scan workflow uses Tesseract OCR to extract words and their pixel coordinates, then applies regular-expression-based PII detection to the extracted text.

The detector currently contains patterns for:

- Aadhaar numbers
- PAN cards
- Indian phone numbers
- Email addresses
- Credit-card numbers
- Dates in `DD/MM/YYYY`-style formats
- Dates in `YYYY-MM-DD`-style formats
- Indian passport numbers
- Indian pincodes

Credit-card matches additionally use the Luhn algorithm for validation. Aadhaar detection also performs a basic 12-digit validation. citeturn43file0

## Region-aware OCR

The OCR engine does not only return text. It preserves:

```text
text
x
 y
w
h
confidence
```

for each detected word. This allows the PII detector's text matches to be mapped back to actual regions of the document image. citeturn42file0

## Multi-word detection

The automatic redaction layer groups OCR word boxes into approximate text lines so patterns spanning multiple OCR tokens can still be detected.

For example:

```text
1234     5678     9012
  |        |        |
  +--------+--------+
           |
      Aadhaar match
           |
           v
   Merged bounding box
```

The detector then merges the corresponding word boxes into one region and removes duplicate/contained detections. citeturn44file0

## Controlled redaction

Detected or manually selected regions can be redacted using:

- Solid black fill
- Gaussian blur

The image-processing module validates/clamps regions against image boundaries before modifying the image. citeturn46file0

## Password-protected restoration

The cryptography module derives an encryption key from a user password using PBKDF2-HMAC-SHA256 and a random salt, then encrypts the protected payload with Fernet. citeturn40file0

## Steganographic storage

Encrypted data can be hidden inside an image using least-significant-bit (LSB) steganography. The payload is compressed first and framed with a 4-byte length header. citeturn41file0

## Secured PDF support

The application can create secured PDFs in which the redacted image forms the visible page while the encrypted payload is stored as a PDF embedded attachment. Original image dimensions are also stored as metadata so restoration can reproduce the original coordinate system. citeturn45file0

---

# Application Architecture

The project separates the GUI from the document-processing and security components.

```text
                         SecureGuard AI
                               |
             +-----------------+-----------------+
             |                                   |
             v                                   v
       CustomTkinter GUI                    Core Modules
             |                                   |
     +-------+-------+             +-------------+-------------+
     |       |       |             |       |       |       |   |
     v       v       v             v       v       v       v   v
 Smart    Manual   Restore        OCR     PII    Image   Crypto Stego
 Scan     Redact                 Engine Detector Proc.  Manager Manager
     |       |       |             |       |       |       |   |
     +-------+-------+-------------+-------+-------+-------+---+
                               |
                               v
                         PDF Converter
                               |
                               v
                       Protected Document
```

The GUI constructs instances of `CryptoManager`, `StegoManager`, `ImageProcessor`, `AutoRedactor`, and `PDFConverter` and coordinates them from the desktop application. citeturn47file0

---

# End-to-End Workflow

## Automatic document protection

```text
                    Input Document
                          |
                    +-----+-----+
                    |           |
                   PDF        Image
                    |           |
                    v           |
             PDF → PNG/Image    |
                    |           |
                    +-----+-----+
                          |
                          v
                    Tesseract OCR
                          |
                          v
                Word text + bounding boxes
                          |
                          v
                    PII Detector
                          |
                          v
              Detected sensitive regions
                          |
                          v
                  User review/select
                          |
                          v
                    Redaction
                          |
                          +----------------+
                          |                |
                          v                v
                  Visible redacted      Original
                       image             content
                                          |
                                          v
                                   CryptoManager
                                          |
                                          v
                                  Encrypted payload
                                          |
                                          v
                             Stego image / secured PDF
```

The exact GUI path can vary depending on whether the user is working with an image, a PDF page, or a manually selected region, but the core components are designed around this separation of detection, redaction, encryption, and protected storage.

---

# Smart Scan

Smart Scan is the automated document-analysis workflow.

## Step 1 — Load the document

The application accepts document images and PDF input. PDFs can be rendered into PNG images using PyMuPDF before OCR/redaction processing. citeturn45file0

## Step 2 — Run OCR

Tesseract extracts individual words and their positions.

Example internal representation:

```python
{
    "text": "example@email.com",
    "x": 100,
    "y": 50,
    "w": 180,
    "h": 24,
    "confidence": 95
}
```

The OCR engine ignores empty/low-confidence words according to its configured minimum confidence, which defaults to `40`. citeturn42file0

## Step 3 — Detect PII

The PII detector applies the configured patterns to the OCR text.

Each detection contains information such as:

```text
Type
Value
Start / End position
Severity
```

The automatic redactor then maps those detections to image coordinates. citeturn43file0turn44file0

## Step 4 — Review detections

The GUI presents detected regions to the user so that automatic detection can be reviewed before sensitive content is hidden.

This is important because regex-based detection is inherently pattern-based and can produce false positives or false negatives.

## Step 5 — Redact selected regions

Selected regions are passed to the image processor for black-fill or blur redaction. citeturn46file0

---

# PII Detection

The PII detector is deliberately implemented as a modular pattern engine rather than coupling detection logic directly to OCR or GUI code.

## Pattern definition

Each PII pattern contains:

```text
name
pattern
severity
validator
```

For example:

```text
Credit Card
    |
    +--> Regex pattern
    |
    +--> High severity
    |
    +--> Luhn validation
```

This makes additional PII types possible without changing the main scanning pipeline. The detector also accepts optional `extra_patterns`. citeturn43file0

## Severity levels

The current detector uses:

```text
high
medium
low
```

Severity is used by the application UI to help distinguish more sensitive detections from lower-priority matches.

---

# Controlled Redaction

The `ImageProcessor` supports two main redaction modes.

## Black redaction

The selected region is replaced with a solid black rectangle.

```text
Original
+----------------------+
| Name: John Doe       |
| Email: x@example.com |
+----------------------+

        |
        v

Redacted
+----------------------+
| Name: █████████      |
| Email: █████████████ |
+----------------------+
```

## Blur redaction

The selected region is replaced with a strong Gaussian blur so that the underlying text becomes difficult to read.

The implementation chooses a relatively large odd-sized kernel based on the selected region. citeturn46file0

## Manual redaction

The GUI also provides a manual Draw & Redact workflow, allowing the user to explicitly select a region rather than relying on automatic PII detection. The application interface contains separate Smart Scan, Draw & Redact, and Restore views. citeturn47file0

---

# Cryptography

The cryptography layer is responsible for protecting the original sensitive data before it is stored or hidden.

## Key derivation

The password is not used directly as a Fernet key.

Instead:

```text
User password
     |
     v
Random 16-byte salt
     |
     v
PBKDF2-HMAC-SHA256
     |
     | 480,000 iterations
     v
32-byte derived key
     |
     v
URL-safe Base64 encoding
     |
     v
Fernet key
```

The current implementation uses:

```text
Algorithm:       PBKDF2-HMAC-SHA256
Salt length:     16 bytes
Iterations:      480,000
Derived length:  32 bytes
Encryption:      Fernet
```

The salt is randomly generated for each encryption operation and prepended to the encrypted output. citeturn40file0

## Encryption format

The encrypted payload is conceptually:

```text
+------------------+----------------------+
| 16-byte salt     | Fernet ciphertext    |
+------------------+----------------------+
```

During decryption, the first 16 bytes are extracted as the salt. The same password is passed through PBKDF2 with that salt to recreate the Fernet key.

If decryption fails, the implementation reports an invalid password or corrupted-data error. citeturn40file0

## Why encryption comes before steganography

Steganography hides the existence/visibility of the data inside another file, but it should not be treated as encryption.

SecureGuard AI therefore uses:

```text
Sensitive data
     |
     v
Encryption
     |
     v
Ciphertext
     |
     v
Steganographic embedding
     |
     v
Hidden protected payload
```

Even if the hidden payload is extracted, it remains encrypted without the password.

---

# Steganography

The `StegoManager` implements LSB image steganography using OpenCV and NumPy.

## Embedding process

```text
Encrypted bytes
      |
      v
zlib compression
      |
      v
4-byte big-endian length header
      |
      v
Convert bytes → bits
      |
      v
Replace image-channel LSBs
      |
      v
Save as PNG
```

The payload format is:

```text
[ 4-byte payload length ][ compressed encrypted payload ]
```

The 4-byte header tells the extractor exactly how many compressed bytes it needs to read. citeturn41file0

## Capacity

The implementation estimates image capacity as:

```text
(width × height × 3) / 8 bytes
```

because one bit is stored in each of the three color channels of each pixel.

If the framed payload exceeds the image capacity, the operation fails rather than silently truncating data. citeturn41file0

## Extraction

Extraction happens in two stages:

```text
Stego PNG
   |
   v
Read 32-bit length header
   |
   v
Read exact payload length
   |
   v
zlib decompression
   |
   v
Encrypted bytes
```

The implementation therefore avoids scanning the entire image after the payload length is known. Corrupt compressed data produces an explicit decompression error. citeturn41file0

## Why PNG?

The steganography implementation saves the output as PNG because PNG is lossless. Lossy formats such as JPEG can modify pixel values and destroy LSB-embedded information.

---

# PDF Processing

PDF handling is implemented using PyMuPDF (`fitz`).

## PDF → image

The converter can:

- Determine page count.
- Render an individual page to a PIL image.
- Render a page to a temporary PNG file.
- Convert pages for preview.

The default rendering DPI is `200`. citeturn45file0

## Secured PDF format

A secured PDF contains:

```text
PDF page
  |
  +--> Redacted visible image
  |
  +--> Embedded secureguard_payload.enc
  |
  +--> Embedded secureguard_meta.json
```

The encrypted payload is stored as a PDF embedded file attachment rather than as visible document content.

The metadata stores the original image dimensions:

```json
{
  "orig_w": 1234,
  "orig_h": 5678
}
```

Those dimensions allow the restoration process to render the secured PDF back into the same pixel coordinate system used during redaction. citeturn45file0

## Extracting a secured PDF

The converter checks for:

```text
secureguard_payload.enc
```

and rejects PDFs that do not contain the expected SecureGuard payload.

---

# Restoration

The restoration workflow reverses the protection process.

Conceptually:

```text
Protected Image / Secured PDF
            |
            v
    Extract encrypted payload
            |
            v
       Read salt
            |
            v
    Derive key from password
            |
            v
      Fernet decrypt
            |
            v
      Original payload
            |
            v
 Restore protected regions
```

The password must be correct because the encrypted payload is authenticated by Fernet. An incorrect password or corrupted ciphertext causes decryption to fail. citeturn40file0

For secured PDFs, the original image dimensions stored in `secureguard_meta.json` are used to render the page back at the original coordinate dimensions. citeturn45file0

---

# GUI

The desktop interface is implemented using CustomTkinter.

The current GUI is presented as a dark-themed application called **SecureGuard AI | Document Intelligence & Redaction**.

The main navigation contains three modules:

```text
┌─────────────────────────┐
│ MODULES                 │
│                         │
│ 🔍 Smart Scan           │
│ ✏️ Draw & Redact        │
│ 🔓 Restore              │
└─────────────────────────┘
```

The GUI creates the core processing objects during initialization:

```text
CryptoManager
StegoManager
ImageProcessor
AutoRedactor
PDFConverter
```

It also maintains state for selected documents, scan results, PDF pages, temporary files, and manual drawing operations. citeturn47file0

The application starts from `main.py`, which creates `StegoApp` and enters the Tkinter event loop. citeturn48file0

---

# Project Structure

The repository is organized into GUI and reusable core modules:

```text
Stego-Crypt/
│
├── core/
│   ├── __init__.py
│   ├── auto_redactor.py
│   ├── crypto_manager.py
│   ├── image_processor.py
│   ├── ocr_engine.py
│   ├── pdf_converter.py
│   ├── pii_detector.py
│   └── stego_manager.py
│
├── gui/
│   ├── app.py
│   └── animations.py
│
├── tests/
│
├── main.py
├── requirements.txt
└── README.md
```

### `core/`

Contains the reusable processing and security logic.

### `gui/`

Contains the desktop interface and UI animation helpers.

### `tests/`

Contains automated tests for the project.

### `main.py`

Application entry point:

```python
from gui.app import StegoApp

if __name__ == "__main__":
    app = StegoApp()
    app.mainloop()
```

citeturn48file0

---

# Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| Desktop GUI | CustomTkinter |
| Image Processing | OpenCV |
| Image Representation | Pillow, NumPy |
| OCR | Tesseract / pytesseract |
| PDF Processing | PyMuPDF |
| Encryption | Fernet via `cryptography` |
| Key Derivation | PBKDF2-HMAC-SHA256 |
| Steganography | LSB image steganography |
| Compression | zlib |
| Testing | pytest |

The current `requirements.txt` specifies CustomTkinter, cryptography, OpenCV, Pillow, NumPy, pytesseract, PyMuPDF, and pytest. citeturn39file0

---

# Installation

## Prerequisites

Install:

- Python 3
- pip
- Tesseract OCR for Smart Scan

Tesseract is a system-level dependency and is not installed by `pip install -r requirements.txt`.

## 1. Clone the repository

```bash
git clone https://github.com/keshavkrk/stego-crypto.git
cd stego-crypto
```

## 2. Create a virtual environment

### Windows PowerShell

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell execution policy prevents activation in the current process:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

# Tesseract OCR Setup

Smart Scan requires the Tesseract executable.

On Windows, the OCR engine automatically checks common installation locations including:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
C:\Program Files (x86)\Tesseract-OCR\tesseract.exe
```

It also checks common Local AppData installation locations and the system `PATH`. citeturn42file0

If Tesseract is unavailable, the application raises a dedicated `TesseractNotInstalledError` with installation guidance. The code explicitly notes that manual redaction and decryption can operate without Tesseract. citeturn42file0

---

# Running the Application

From the repository root, with the virtual environment activated:

```bash
python main.py
```

The application opens the SecureGuard AI desktop interface.

The main workflows are:

```text
Smart Scan
Draw & Redact
Restore
```

The GUI entry point is `main.py`, which instantiates `StegoApp`. citeturn48file0

---

# Core Modules

## `crypto_manager.py`

Responsible for:

- Password-based key derivation.
- Random salt generation.
- Fernet encryption.
- Fernet decryption.
- Validation of encrypted payload length.
- Invalid-password/corruption handling.

citeturn40file0

## `stego_manager.py`

Responsible for:

- Compressing encrypted payloads.
- Building the length-prefixed payload.
- Calculating image capacity.
- Embedding bits into RGB-channel LSBs.
- Saving PNG stego images.
- Extracting the length header.
- Extracting the exact payload.
- Decompressing the recovered bytes.

citeturn41file0

## `ocr_engine.py`

Responsible for:

- Detecting/configuring Tesseract.
- Running word-level OCR.
- Returning bounding boxes.
- Filtering low-confidence OCR results.
- Providing full-text OCR.

citeturn42file0

## `pii_detector.py`

Responsible for:

- Defining PII regex patterns.
- Applying validators.
- Assigning severity levels.
- Removing duplicate detections.
- Supporting custom additional patterns.

citeturn43file0

## `auto_redactor.py`

Responsible for combining OCR and PII detection.

Its workflow is:

```text
OCR
 |
 v
Word boxes
 |
 v
Single-word detection
 |
 v
Group words into lines
 |
 v
Multi-word PII detection
 |
 v
Map matches to bounding boxes
 |
 v
Merge + deduplicate
 |
 v
Redaction regions
```

citeturn44file0

## `image_processor.py`

Responsible for visual document modification.

It supports:

- Single black redaction boxes.
- Multiple black redaction boxes.
- Gaussian blur redaction.
- Highlight boxes for preview.
- Saving processed images.
- Bounds validation/clamping.

citeturn46file0

## `pdf_converter.py`

Responsible for:

- PDF page counting.
- PDF-to-image rendering.
- Temporary PNG creation.
- Secured PDF creation.
- Embedded encrypted payloads.
- Embedded restoration metadata.
- Secure payload extraction.
- Pixel-dimension-preserving rendering.

citeturn45file0

## `gui/app.py`

Coordinates the core modules and provides the user-facing desktop application. It manages Smart Scan, Draw & Redact, and Restore views and maintains document/PDF/manual-selection state. citeturn47file0

---

# Security Design

SecureGuard AI deliberately separates **confidentiality** from **concealment**.

## Encryption provides confidentiality

The sensitive data is encrypted using a password-derived Fernet key.

```text
Password
   |
   v
PBKDF2-HMAC-SHA256
   |
   v
Fernet key
   |
   v
Encrypted payload
```

## Steganography provides concealment

The encrypted payload can then be hidden in image pixels:

```text
Encrypted payload
       |
       v
Compressed payload
       |
       v
LSB embedding
       |
       v
Stego image
```

Therefore the two techniques have different responsibilities:

| Mechanism | Purpose |
|---|---|
| PBKDF2 | Derive a cryptographic key from the password |
| Fernet | Encrypt and authenticate the sensitive data |
| zlib | Compress the encrypted payload before embedding |
| LSB | Conceal the payload inside image pixels |
| PNG | Preserve pixel values losslessly |

---

# Data Flow

A simplified secure-sharing flow is:

```text
                 Sensitive Document
                         |
                         v
                    OCR / Manual
                         |
                         v
                 Sensitive Regions
                         |
                         +--------------------+
                         |                    |
                         v                    v
                   Redacted Image       Original Regions
                                              |
                                              v
                                         Serialize data
                                              |
                                              v
                                          Encrypt
                                              |
                                              v
                                         Compress
                                              |
                                              v
                                      Hide / Embed
                                              |
                         +--------------------+
                         |
                         v
                  Protected Artifact
                         |
                    +----+----+
                    |         |
                    v         v
                 Stego PNG  Secured PDF
```

Restoration reverses the protected-data path using the correct password.

---

# Error Handling

The project includes explicit failure handling at several levels.

## OCR availability

If Tesseract is unavailable, the OCR engine raises a dedicated error rather than failing with an obscure import/runtime error. citeturn42file0

## Invalid images

The image processor and steganography manager check whether an image can be loaded and raise a descriptive error if it cannot. citeturn41file0turn46file0

## Insufficient steganography capacity

Before embedding, the stego manager compares the framed payload size with image capacity and refuses to write an incomplete payload. citeturn41file0

## Corrupted stego data

Invalid payload length or failed zlib decompression is reported as missing/corrupted hidden data. citeturn41file0

## Invalid password

Fernet decryption failures are converted into an explicit invalid-password/corrupted-data error. citeturn40file0

## Invalid secured PDF

The PDF converter checks for the expected `secureguard_payload.enc` embedded attachment and rejects PDFs that were not produced in the expected SecureGuard format. citeturn45file0

---

# Testing

The repository includes a `tests/` directory and lists `pytest` as a development/testing dependency. citeturn39file0

Run the test suite from the repository root with:

```bash
pytest
```

For a focused test run:

```bash
pytest tests/<test_file>.py
```

The exact available test modules should be checked against the current `tests/` directory before running a specific test filename.

---

# Important Limitations

The current implementation has several limitations that are important when considering production use.

1. **Regex-based PII detection is not universal.** It can miss sensitive information that does not match the configured patterns and can produce false positives.
2. **OCR accuracy affects detection.** Poor scans, unusual fonts, low resolution, or document layouts can reduce OCR quality.
3. **Steganographic capacity depends on the cover image.** Larger encrypted payloads require sufficiently large images.
4. **PNG is required for reliable LSB storage.** Converting the stego image through a lossy format can destroy hidden data.
5. **The password is security-critical.** If the password is lost, the encrypted payload cannot be recovered through the normal decryption path.
6. **The application is desktop-oriented.** It is not currently presented as a multi-user server-side document-management system.
7. **PDF embedded attachments are not equivalent to a dedicated secure storage system.** Production deployments may require stronger access controls, audit logging, and controlled key management.
8. **Automatic redaction should be reviewed by a human.** Detection should not be treated as guaranteed identification of every sensitive field.
9. **Steganography is not a substitute for encryption.** The security of the protected content depends primarily on the encryption layer, not on the hidden nature of the carrier image.

---

# Future Improvements

Potential extensions include:

- Add more international PII formats and document-specific detectors.
- Add configurable PII patterns through the GUI.
- Improve OCR preprocessing for noisy/scanned documents.
- Add multi-page automated PDF scanning and redaction workflows.
- Add stronger document integrity and provenance metadata.
- Add authenticated packaging/versioning for secured artifacts.
- Add automated end-to-end tests covering encrypt → hide → extract → decrypt → restore.
- Add a formal threat model and security audit.
- Add secure key-management options rather than relying solely on user passwords.
- Add audit logs for redaction and restoration operations.
- Improve large-payload handling and stego carrier selection.
- Add configurable OCR language support.
- Package the application for Windows distribution.

---

# Security Notes

This project handles potentially sensitive document information. For that reason:

- Never commit API keys, passwords, or other credentials.
- Do not commit private source documents or generated sensitive artifacts.
- Keep temporary files and generated stego images outside version control where appropriate.
- Use strong passwords for protected documents.
- Prefer lossless PNG output for LSB steganography.
- Treat automated PII detection as an assistive system and review results before sharing protected documents.
- Rotate credentials immediately if they are accidentally exposed.

---

# Summary

SecureGuard AI combines document intelligence and security techniques into one desktop workflow:

```text
       OCR + PII Detection
                |
                v
        Controlled Redaction
                |
                v
        Password-based Crypto
                |
                v
       Optional Steganography
                |
                v
       Protected Document
                |
                v
       Authorized Restoration
```

The project demonstrates practical integration of **OCR, computer vision, regular-expression-based PII detection, PDF processing, password-based cryptography, and image steganography** in a modular Python application.

The most important architectural principle is the separation of responsibilities:

```text
Detection       → What information is sensitive?
Redaction       → What should be hidden visually?
Cryptography    → How is the original information protected?
Steganography   → Where can the protected payload be concealed?
Restoration     → How can an authorized user recover it?
GUI             → How does the user control the workflow?
```

urlView the repository on GitHubhttps://github.com/keshavkrk/stego-crypto
