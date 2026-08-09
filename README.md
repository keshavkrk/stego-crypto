# Stego-Crypt — SecureGuard AI

SecureGuard AI is a desktop application for the controlled redaction and secure sharing of sensitive documents. Instead of permanently deleting sensitive information, the application hides selected data and protects the original content so that authorized users can securely restore it with a password.

The application combines OCR-based sensitive-information detection, image processing, cryptography, and steganography in a single desktop workflow.

## Key Features

- **Smart Scan** — automatically scans documents and detects sensitive information using OCR and pattern-based PII detection.
- **Controlled Redaction** — sensitive regions can be hidden without permanently destroying the original information.
- **Manual Redaction** — users can select and redact regions manually when automatic detection is not sufficient.
- **Secure Restoration** — authorized users can recover protected content using the correct password.
- **Image Steganography** — encrypted document data can be embedded into images using LSB steganography.
- **PDF Support** — PDF pages can be converted to images for processing and redaction.
- **Desktop GUI** — built with CustomTkinter with separate Smart Scan, Draw & Redact, and Restore workflows.

## Architecture

```text
                         SecureGuard AI
                               │
                ┌──────────────┴──────────────┐
                │                             │
          Desktop GUI                    Core Modules
        (CustomTkinter)                       │
                │              ┌──────────────┼──────────────┐
                │              │              │              │
                ▼              ▼              ▼              ▼
          Document Input     OCR/PII      Redaction      PDF Conversion
                │            Detection     Processing          │
                │              │              │                 │
                └──────────────┴──────────────┴─────────────────┘
                               │
                         Crypto Manager
                               │
                    Password → PBKDF2-SHA256
                               │
                         Fernet Encryption
                               │
                         Stego Manager
                               │
                         LSB Embedding
                               ▼
                         Protected Image
```

## Security Design

### Password-based encryption

The cryptography layer derives an encryption key from the user's password using **PBKDF2-HMAC-SHA256** with a randomly generated 16-byte salt. The derived key is then used with Fernet authenticated encryption.

The salt is stored alongside the encrypted payload so the same key can be derived during restoration. The password itself is never stored in the protected payload.

### Steganography

The steganography module embeds encrypted data into the least significant bits of image color channels. Before embedding, the payload is compressed with `zlib` and framed with a length header.

```text
Original data
     │
     ▼
Compression (zlib)
     │
     ▼
Length header + compressed payload
     │
     ▼
LSB embedding into PNG
     │
     ▼
Stego image
```

The application uses PNG for the stego output because the lossless format preserves the embedded LSB data.

## Automatic Redaction Pipeline

The Smart Scan workflow follows:

```text
Document
   │
   ▼
PDF → Image conversion (when required)
   │
   ▼
OCR text + bounding boxes
   │
   ▼
PII pattern detection
   │
   ▼
Map detections to image regions
   │
   ▼
Assign severity / confidence
   │
   ▼
User reviews detected regions
   │
   ▼
Controlled redaction
```

The OCR layer preserves word-level bounding boxes, allowing detected sensitive information to be mapped back to the corresponding region of the document.

## Technology Stack

| Component | Technology |
|---|---|
| Language | Python |
| GUI | CustomTkinter |
| Image Processing | OpenCV, Pillow, NumPy |
| OCR | Tesseract / pytesseract |
| PDF Processing | PyMuPDF |
| Cryptography | Python `cryptography` library |
| Key Derivation | PBKDF2-HMAC-SHA256 |
| Encryption | Fernet |
| Steganography | LSB image steganography |
| Compression | zlib |
| Testing | pytest |

## Project Structure

```text
Stego-Crypt/
├── core/
│   ├── auto_redactor.py
│   ├── crypto_manager.py
│   ├── stego_manager.py
│   ├── image_processor.py
│   ├── ocr_engine.py
│   ├── pdf_converter.py
│   └── pii_detector.py
│
├── gui/
│   ├── app.py
│   └── animations.py
│
├── tests/
├── main.py
├── requirements.txt
└── README.md
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/keshavkrk/stego-crypto.git
cd stego-crypto
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR

`pytesseract` requires the Tesseract OCR engine to be installed separately and available to the application.

## Running the Application

```bash
python main.py
```

The application opens the SecureGuard AI desktop interface with three primary workflows:

- **Smart Scan** — automatic OCR and PII detection
- **Draw & Redact** — manual region selection and redaction
- **Restore** — recovery of protected content using the password

## Important Notes

- Use PNG for steganographic output to avoid lossy compression destroying hidden data.
- The application is intended for controlled document protection and authorized use.
- Generated images and temporary files should not be committed to version control.
- Keep passwords and other sensitive material outside the source repository.

## Project Goal

The goal of SecureGuard AI is to provide a practical approach to document privacy where sensitive information can be **hidden and securely recoverable**, rather than irreversibly deleted during the redaction process.
