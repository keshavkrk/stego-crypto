"""
PDF Converter — Converts PDF pages to images and creates secured PDFs.
Uses PyMuPDF (fitz) for fast, dependency-free PDF rendering.
"""
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import tempfile
import json


class PDFConverter:
    """Converts PDF documents to images and creates secured PDF output."""

    def __init__(self, dpi=200):
        self.dpi = dpi
        self.zoom = dpi / 72

    def get_page_count(self, pdf_path):
        """Return the number of pages in a PDF."""
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count

    def pdf_page_to_image(self, pdf_path, page_num=0):
        """Convert a single PDF page to a PIL Image."""
        doc = fitz.open(pdf_path)
        if page_num >= len(doc):
            doc.close()
            raise ValueError(f"Page {page_num + 1} does not exist (PDF has {len(doc)} pages).")

        page = doc[page_num]
        mat = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        doc.close()
        return img

    def pdf_page_to_temp_file(self, pdf_path, page_num=0):
        """Convert a PDF page and save it as a temporary PNG file."""
        img = self.pdf_page_to_image(pdf_path, page_num)
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(tmp_path, format="PNG")
        return tmp_path

    @staticmethod
    def save_secured_pdf(redacted_image_path, encrypted_data, output_path):
        """
        Create a secured PDF from a redacted image with encrypted data
        stored as a hidden PDF embedded file attachment.

        Also stores the original image pixel dimensions so we can
        render back at the exact same size during restoration.
        """
        doc = fitz.open()

        # Read the redacted image and get its pixel dimensions
        pil_img = Image.open(redacted_image_path)
        orig_w, orig_h = pil_img.size
        pil_img.close()

        # Convert image to PDF bytes
        img = fitz.open(redacted_image_path)
        pdf_bytes = img.convert_to_pdf()
        img.close()

        img_pdf = fitz.open("pdf", pdf_bytes)

        # Scale the page to fit a standard size (A4 = 595×842 pts)
        # while preserving the image aspect ratio
        max_w, max_h = 595.0, 842.0
        aspect = orig_w / orig_h
        if aspect > max_w / max_h:
            # Landscape-ish: fit to width
            page_w = max_w
            page_h = max_w / aspect
        else:
            # Portrait-ish: fit to height
            page_h = max_h
            page_w = max_h * aspect

        page = doc.new_page(width=page_w, height=page_h)
        page.show_pdf_page(page.rect, img_pdf, 0)
        img_pdf.close()

        # Embed encrypted payload as a hidden attachment
        doc.embfile_add(
            "secureguard_payload.enc",
            buffer_=encrypted_data,
            filename="secureguard_payload.enc",
            desc="SecureGuard encrypted PII data"
        )

        # Also embed the original image dimensions as metadata
        meta = json.dumps({"orig_w": orig_w, "orig_h": orig_h}).encode()
        doc.embfile_add(
            "secureguard_meta.json",
            buffer_=meta,
            filename="secureguard_meta.json",
            desc="SecureGuard metadata"
        )

        doc.save(output_path)
        doc.close()

    @staticmethod
    def extract_secured_pdf(pdf_path):
        """
        Extract the encrypted payload from a secured PDF.

        Returns:
            bytes: The encrypted payload.
        """
        doc = fitz.open(pdf_path)
        names = doc.embfile_names()
        if "secureguard_payload.enc" not in names:
            doc.close()
            raise ValueError(
                "This PDF does not contain SecureGuard encrypted data.\n"
                "Make sure you're loading a PDF that was secured with SecureGuard."
            )
        data = doc.embfile_get("secureguard_payload.enc")
        doc.close()
        return data

    @staticmethod
    def get_secured_pdf_image(pdf_path):
        """
        Render the secured PDF page back to an image at the EXACT same
        pixel dimensions as the original image that was embedded.

        Returns:
            PIL.Image: The rendered page, sized to match original coordinates.
        """
        doc = fitz.open(pdf_path)
        names = doc.embfile_names()

        # Read original dimensions from metadata
        orig_w, orig_h = None, None
        if "secureguard_meta.json" in names:
            meta_raw = doc.embfile_get("secureguard_meta.json")
            meta = json.loads(meta_raw.decode())
            orig_w = meta.get("orig_w")
            orig_h = meta.get("orig_h")

        page = doc[0]

        if orig_w and orig_h:
            # Compute exact zoom to get pixel-perfect match
            zoom_x = orig_w / page.rect.width
            zoom_y = orig_h / page.rect.height
            mat = fitz.Matrix(zoom_x, zoom_y)
        else:
            # Fallback: use standard 200 DPI
            zoom = 200 / 72
            mat = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        doc.close()
        return img

    @staticmethod
    def pdf_to_pil_image(pdf_path, page_num=0, dpi=200):
        """Convert a PDF page to PIL Image (for preview)."""
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        doc.close()
        return img

    @staticmethod
    def is_pdf(file_path):
        """Check if a file is a PDF based on extension."""
        return file_path.lower().endswith(".pdf")
