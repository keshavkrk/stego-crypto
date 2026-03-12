"""
SecureGuard — Premium Document Redaction System
Ultra-modern GUI with canvas draw-box for manual redaction.
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os
import threading
import json
import base64
import io
import tempfile

from core.crypto_manager import CryptoManager
from core.stego_manager import StegoManager
from core.image_processor import ImageProcessor
from core.auto_redactor import AutoRedactor
from core.ocr_engine import TesseractNotInstalledError

# ─── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

C = {
    "bg":           "#0A0D14",
    "card":         "#131824",
    "input":        "#1C2436",
    "accent":       "#00E5FF",
    "accent_h":     "#00B8D4",
    "primary":      "#7C3AED",
    "primary_h":    "#6D28D9",
    "danger":       "#FF2A55",
    "danger_h":     "#E61A41",
    "success":      "#00E676",
    "success_h":    "#00C853",
    "warning":      "#FFB300",
    "text":         "#FFFFFF",
    "text2":        "#9CA3AF",
    "border":       "#2E3B52",
    "sev_high":     "#FF2A55",
    "sev_med":      "#FFB300",
    "sev_low":      "#00E5FF",
}

SEV = {"high": C["sev_high"], "medium": C["sev_med"], "low": C["sev_low"]}
FNT = "Segoe UI"


class StegoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SecureGuard AI | Document Intelligence & Redaction")
        self.geometry("1280x850")
        self.minsize(1100, 750)
        self.configure(fg_color=C["bg"])

        self.crypto = CryptoManager()
        self.stego = StegoManager()
        self.img_proc = ImageProcessor()
        self.auto_redactor = AutoRedactor()

        self.selected_image_path = None
        self.dec_image_path = None
        self.scan_results = []
        self.scan_check_vars = []

        # Manual draw state
        self._draw_img = None        # PIL Image loaded for manual
        self._draw_tk_img = None     # PhotoImage reference
        self._draw_scale = 1.0       # scale factor
        self._draw_rect_id = None    # canvas rectangle id
        self._draw_start = None      # (x, y) start of drag
        self._draw_box = None        # (x1, y1, x2, y2) in image coords

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._create_header()
        self._create_tabs()
        self._create_status_bar()

    # ═══════════════════════════════════════════════════════════════════════════
    #  HEADER
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_header(self):
        hdr = ctk.CTkFrame(self, height=70, fg_color=C["card"], corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)

        tf = ctk.CTkFrame(hdr, fg_color="transparent")
        tf.grid(row=0, column=0, padx=30, pady=12, sticky="w")
        ctk.CTkLabel(tf, text="🛡️ Secure", font=ctk.CTkFont(family=FNT, size=26, weight="bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(tf, text="Guard", font=ctk.CTkFont(family=FNT, size=26, weight="bold"),
                     text_color=C["accent"]).pack(side="left")

        ctk.CTkLabel(hdr, text="Next-Gen Document Redaction",
                     font=ctk.CTkFont(family=FNT, size=13, slant="italic"),
                     text_color=C["text2"]).grid(row=0, column=1, padx=15, pady=12, sticky="w")

    # ═══════════════════════════════════════════════════════════════════════════
    #  NAVIGATION + VIEWS
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_tabs(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Sidebar nav
        nav = ctk.CTkFrame(container, width=200, fg_color=C["card"],
                           corner_radius=14, border_width=1, border_color=C["border"])
        nav.grid(row=0, column=0, padx=(0, 15), sticky="nsew")
        nav.grid_propagate(False)

        ctk.CTkLabel(nav, text="NAVIGATION",
                     font=ctk.CTkFont(family=FNT, size=11, weight="bold"),
                     text_color=C["text2"]).pack(padx=20, pady=(25, 10), fill="x")

        self.nav_btns = {}
        for label, key in [("🔍  Smart Scan", "smart"), ("✏️  Draw & Redact", "manual"),
                           ("🔓  Restore", "decrypt")]:
            b = ctk.CTkButton(nav, text=label, height=42,
                              font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                              fg_color="transparent", text_color=C["text2"],
                              hover_color=C["input"], anchor="w",
                              command=lambda k=key: self._switch(k))
            b.pack(padx=10, pady=4, fill="x")
            self.nav_btns[key] = b

        # Content area
        self.content = ctk.CTkFrame(container, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.views = {}
        for key in ("smart", "manual", "decrypt"):
            f = ctk.CTkFrame(self.content, fg_color="transparent")
            self.views[key] = f

        self._build_smart()
        self._build_manual()
        self._build_decrypt()
        self._switch("smart")

    def _switch(self, key):
        for k, b in self.nav_btns.items():
            b.configure(fg_color="transparent", text_color=C["text2"])
            self.views[k].grid_forget()
        self.nav_btns[key].configure(fg_color=C["input"], text_color=C["accent"])
        self.views[key].grid(row=0, column=0, sticky="nsew")

    # ═══════════════════════════════════════════════════════════════════════════
    #  VIEW 1: SMART SCAN
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_smart(self):
        v = self.views["smart"]
        v.grid_columnconfigure(0, weight=0)
        v.grid_columnconfigure(1, weight=1)
        v.grid_rowconfigure(0, weight=1)

        # Left panel
        lp = ctk.CTkFrame(v, width=340, fg_color=C["card"],
                          corner_radius=14, border_width=1, border_color=C["border"])
        lp.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        lp.grid_propagate(False)
        lp.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lp, text="Intelligence Engine",
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        ctk.CTkButton(lp, text="📂 Load Document", height=42,
                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                      fg_color=C["input"], hover_color="#2D3A54",
                      border_width=1, border_color=C["border"], text_color=C["text"],
                      command=self._smart_load).grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.btn_scan = ctk.CTkButton(lp, text="⚡ Start AI Scan", height=42,
                                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                                      fg_color=C["primary"], hover_color=C["primary_h"],
                                      command=self._start_smart_scan, state="disabled")
        self.btn_scan.grid(row=2, column=0, padx=20, pady=(8, 12), sticky="ew")

        self.lbl_det = ctk.CTkLabel(lp, text="Detected Targets (0)",
                                    font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                                    text_color=C["text2"], anchor="w")
        self.lbl_det.grid(row=3, column=0, padx=20, pady=(8, 4), sticky="ew")

        self.det_scroll = ctk.CTkScrollableFrame(lp, fg_color=C["input"], corner_radius=10)
        self.det_scroll.grid(row=4, column=0, padx=15, pady=(0, 10), sticky="nsew")
        lp.grid_rowconfigure(4, weight=1)

        sf = ctk.CTkFrame(lp, fg_color="transparent")
        sf.grid(row=5, column=0, padx=15, pady=(0, 15), sticky="ew")
        sf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sf, text="Encryption Key",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=0, column=0, padx=5, pady=(0, 4), sticky="w")
        self.smart_pwd = ctk.CTkEntry(sf, placeholder_text="Password...", show="•", height=38,
                                      fg_color=C["input"], border_color=C["border"], text_color=C["accent"])
        self.smart_pwd.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="ew")

        self.btn_secure = ctk.CTkButton(sf, text="🔒 Redact & Secure", height=48,
                                        font=ctk.CTkFont(family=FNT, size=14, weight="bold"),
                                        fg_color=C["danger"], hover_color=C["danger_h"],
                                        command=self._start_smart_encrypt, state="disabled")
        self.btn_secure.grid(row=2, column=0, padx=5, sticky="ew")

        # Right panel
        rp = ctk.CTkFrame(v, fg_color=C["card"], corner_radius=14,
                          border_width=1, border_color=C["border"])
        rp.grid(row=0, column=1, sticky="nsew")
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(rp, text="Visual Analysis",
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        bg = ctk.CTkFrame(rp, fg_color=C["bg"], corner_radius=10)
        bg.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        bg.grid_columnconfigure(0, weight=1)
        bg.grid_rowconfigure(0, weight=1)

        self.smart_preview = ctk.CTkLabel(bg, text="Load a document to begin.",
                                          font=ctk.CTkFont(family=FNT, size=14), text_color=C["text2"])
        self.smart_preview.grid(row=0, column=0)

    # ═══════════════════════════════════════════════════════════════════════════
    #  VIEW 2: DRAW & REDACT — Canvas with mouse drawing
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_manual(self):
        v = self.views["manual"]
        v.grid_columnconfigure(0, weight=0)
        v.grid_columnconfigure(1, weight=1)
        v.grid_rowconfigure(0, weight=1)

        # Left panel
        lp = ctk.CTkFrame(v, width=300, fg_color=C["card"],
                          corner_radius=14, border_width=1, border_color=C["border"])
        lp.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        lp.grid_propagate(False)
        lp.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lp, text="Draw & Redact",
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(20, 8), sticky="w")

        ctk.CTkButton(lp, text="📂 Load Document", height=42,
                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                      fg_color=C["input"], hover_color="#2D3A54",
                      border_width=1, border_color=C["border"], text_color=C["text"],
                      command=self._manual_load).grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        # Instructions
        ctk.CTkLabel(lp, text="Click and drag on the image\nto draw a redaction box.",
                     font=ctk.CTkFont(family=FNT, size=12),
                     text_color=C["text2"], justify="left"
                     ).grid(row=2, column=0, padx=20, pady=(15, 5), sticky="w")

        # Coordinates display (read-only, auto-populated from drawing)
        coord_frame = ctk.CTkFrame(lp, fg_color=C["input"], corner_radius=10)
        coord_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        coord_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(coord_frame, text="Selected Region",
                     font=ctk.CTkFont(family=FNT, size=11, weight="bold"),
                     text_color=C["text2"]).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        self.lbl_coords = ctk.CTkLabel(coord_frame, text="No selection yet",
                                       font=ctk.CTkFont(family=FNT, size=12),
                                       text_color=C["accent"], justify="left")
        self.lbl_coords.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="w")

        # Clear selection button
        ctk.CTkButton(lp, text="✖ Clear Selection", height=32,
                      font=ctk.CTkFont(family=FNT, size=12),
                      fg_color="transparent", hover_color=C["input"],
                      border_width=1, border_color=C["border"], text_color=C["text2"],
                      command=self._clear_draw_box).grid(row=4, column=0, padx=20, pady=5, sticky="ew")

        # Password
        ctk.CTkLabel(lp, text="Encryption Key",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=5, column=0, padx=25, pady=(15, 4), sticky="w")

        self.manual_pwd = ctk.CTkEntry(lp, placeholder_text="Password...", show="•", height=38,
                                       fg_color=C["input"], border_color=C["border"], text_color=C["accent"])
        self.manual_pwd.grid(row=6, column=0, padx=20, pady=(0, 15), sticky="ew")

        self.btn_manual_go = ctk.CTkButton(lp, text="🔒 Redact & Secure", height=48,
                                           font=ctk.CTkFont(family=FNT, size=14, weight="bold"),
                                           fg_color=C["danger"], hover_color=C["danger_h"],
                                           command=self._start_manual_encrypt, state="disabled")
        self.btn_manual_go.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="ew")

        # Right panel — Canvas for drawing
        rp = ctk.CTkFrame(v, fg_color=C["card"], corner_radius=14,
                          border_width=1, border_color=C["border"])
        rp.grid(row=0, column=1, sticky="nsew")
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(rp, text="Draw Redaction Box",
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        canvas_bg = ctk.CTkFrame(rp, fg_color=C["bg"], corner_radius=10)
        canvas_bg.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        canvas_bg.grid_columnconfigure(0, weight=1)
        canvas_bg.grid_rowconfigure(0, weight=1)

        self.draw_canvas = Canvas(canvas_bg, bg="#0A0D14", highlightthickness=0, cursor="crosshair")
        self.draw_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Mouse bindings for drawing
        self.draw_canvas.bind("<ButtonPress-1>", self._on_draw_press)
        self.draw_canvas.bind("<B1-Motion>", self._on_draw_drag)
        self.draw_canvas.bind("<ButtonRelease-1>", self._on_draw_release)

        # Placeholder text
        self.draw_canvas.create_text(300, 200, text="Load a document, then drag to draw a box.",
                                     fill=C["text2"], font=(FNT, 14), tags="placeholder")

    # ═══════════════════════════════════════════════════════════════════════════
    #  VIEW 3: DECRYPT
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_decrypt(self):
        v = self.views["decrypt"]
        v.grid_columnconfigure(0, weight=0)
        v.grid_columnconfigure(1, weight=1)
        v.grid_rowconfigure(0, weight=1)

        lp = ctk.CTkFrame(v, width=340, fg_color=C["card"],
                          corner_radius=14, border_width=1, border_color=C["border"])
        lp.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        lp.grid_propagate(False)
        lp.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lp, text="Recovery Module",
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(20, 12), sticky="w")

        ctk.CTkButton(lp, text="📂 Load Secured Asset", height=42,
                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                      fg_color=C["input"], hover_color="#2D3A54",
                      border_width=1, border_color=C["border"], text_color=C["text"],
                      command=self._decrypt_load).grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(lp, text="Decryption Key",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=2, column=0, padx=25, pady=(20, 4), sticky="w")

        self.decrypt_pwd = ctk.CTkEntry(lp, placeholder_text="Password...", show="•", height=38,
                                        fg_color=C["input"], border_color=C["border"], text_color=C["accent"])
        self.decrypt_pwd.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")

        ctk.CTkButton(lp, text="🔓 Authenticate & Reveal", height=48,
                      font=ctk.CTkFont(family=FNT, size=14, weight="bold"),
                      fg_color=C["success"], hover_color=C["success_h"],
                      command=self._start_decryption).grid(row=4, column=0, padx=20, pady=0, sticky="ew")

        self.dec_info_scroll = ctk.CTkScrollableFrame(lp, fg_color=C["input"], corner_radius=10)
        self.dec_info_scroll.grid(row=5, column=0, padx=20, pady=(15, 15), sticky="nsew")
        lp.grid_rowconfigure(5, weight=1)

        self.dec_info_label = ctk.CTkLabel(self.dec_info_scroll, text="Results appear here after decryption.",
                                           font=ctk.CTkFont(family=FNT, size=12),
                                           text_color=C["text2"], justify="left", wraplength=260)
        self.dec_info_label.pack(padx=10, pady=10, anchor="nw")

        # Right panel
        rp = ctk.CTkFrame(v, fg_color=C["card"], corner_radius=14,
                          border_width=1, border_color=C["border"])
        rp.grid(row=0, column=1, sticky="nsew")
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(rp, text="Restored Preview",
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        bg = ctk.CTkFrame(rp, fg_color=C["bg"], corner_radius=10)
        bg.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        bg.grid_columnconfigure(0, weight=1)
        bg.grid_rowconfigure(0, weight=1)

        self.decrypt_preview = ctk.CTkLabel(bg, text="Load a secured document.",
                                            font=ctk.CTkFont(family=FNT, size=14), text_color=C["text2"])
        self.decrypt_preview.grid(row=0, column=0)

    # ═══════════════════════════════════════════════════════════════════════════
    #  STATUS BAR
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_status_bar(self):
        bar = ctk.CTkFrame(self, height=38, fg_color=C["card"], corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        self.status_lbl = ctk.CTkLabel(bar, text="SYSTEM READY",
                                       font=ctk.CTkFont(family=FNT, size=11, weight="bold"),
                                       text_color=C["text2"])
        self.status_lbl.grid(row=0, column=0, padx=20, pady=8, sticky="w")

        self.progress = ctk.CTkProgressBar(bar, width=220, height=6, corner_radius=3,
                                           progress_color=C["accent"], fg_color=C["bg"])
        self.progress.grid(row=0, column=1, padx=20, pady=16, sticky="e")
        self.progress.set(0)

    def _status(self, msg, color=None):
        try: self.status_lbl.configure(text=msg, text_color=color or C["text2"])
        except: pass

    def _prog(self, v):
        try: self.progress.set(v)
        except: pass

    # ═══════════════════════════════════════════════════════════════════════════
    #  PREVIEW UTILITY
    # ═══════════════════════════════════════════════════════════════════════════
    def _show_preview(self, img_or_path, label, max_size=700):
        try:
            img = Image.open(img_or_path) if isinstance(img_or_path, str) else img_or_path
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            label.configure(image=photo, text="")
            label._img_ref = photo
        except Exception as e:
            label.configure(text=f"Preview error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    #  CANVAS DRAW-BOX LOGIC (Manual Tab)
    # ═══════════════════════════════════════════════════════════════════════════
    def _load_image_to_canvas(self, path):
        """Load an image into the draw canvas, scaled to fit."""
        self._draw_img = Image.open(path)
        self._draw_box = None
        self._draw_rect_id = None
        self.lbl_coords.configure(text="No selection yet")
        self.btn_manual_go.configure(state="disabled")

        # Wait for canvas to render so we get its size
        self.draw_canvas.update_idletasks()
        cw = max(self.draw_canvas.winfo_width(), 400)
        ch = max(self.draw_canvas.winfo_height(), 400)

        iw, ih = self._draw_img.size
        scale = min(cw / iw, ch / ih, 1.0)
        self._draw_scale = scale

        display_w = int(iw * scale)
        display_h = int(ih * scale)

        resized = self._draw_img.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self._draw_tk_img = ImageTk.PhotoImage(resized)

        self.draw_canvas.delete("all")
        # Center the image on canvas
        self._draw_offset_x = (cw - display_w) // 2
        self._draw_offset_y = (ch - display_h) // 2
        self.draw_canvas.create_image(self._draw_offset_x, self._draw_offset_y,
                                       anchor="nw", image=self._draw_tk_img, tags="bg_image")

    def _on_draw_press(self, event):
        if self._draw_img is None:
            return
        # Remove old rectangle
        if self._draw_rect_id:
            self.draw_canvas.delete(self._draw_rect_id)
        self._draw_start = (event.x, event.y)
        self._draw_rect_id = self.draw_canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline=C["danger"], width=3, dash=(6, 4)
        )

    def _on_draw_drag(self, event):
        if self._draw_start and self._draw_rect_id:
            self.draw_canvas.coords(self._draw_rect_id,
                                     self._draw_start[0], self._draw_start[1],
                                     event.x, event.y)

    def _on_draw_release(self, event):
        if not self._draw_start or self._draw_img is None:
            return

        sx, sy = self._draw_start
        ex, ey = event.x, event.y

        # Convert canvas coords to image coords
        ox, oy = self._draw_offset_x, self._draw_offset_y
        scale = self._draw_scale

        x1 = int((min(sx, ex) - ox) / scale)
        y1 = int((min(sy, ey) - oy) / scale)
        x2 = int((max(sx, ex) - ox) / scale)
        y2 = int((max(sy, ey) - oy) / scale)

        # Clamp to image bounds
        iw, ih = self._draw_img.size
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(iw, x2), min(ih, y2)

        w, h = x2 - x1, y2 - y1
        if w > 5 and h > 5:
            self._draw_box = (x1, y1, x2, y2)
            self.lbl_coords.configure(text=f"X={x1}  Y={y1}  W={w}  H={h}")
            self.btn_manual_go.configure(state="normal")
            self._status(f"Selection: {w}×{h} pixels")
        else:
            self._draw_box = None
            self.lbl_coords.configure(text="Too small — try again")
            self.btn_manual_go.configure(state="disabled")

        self._draw_start = None

    def _clear_draw_box(self):
        if self._draw_rect_id:
            self.draw_canvas.delete(self._draw_rect_id)
            self._draw_rect_id = None
        self._draw_box = None
        self.lbl_coords.configure(text="No selection yet")
        self.btn_manual_go.configure(state="disabled")

    # ═══════════════════════════════════════════════════════════════════════════
    #  SMART SCAN LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def _smart_load(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif")])
        if not path: return
        self.selected_image_path = path
        self._show_preview(path, self.smart_preview)
        self.btn_scan.configure(state="normal")
        self.btn_secure.configure(state="disabled")
        self.scan_results = []
        self._clear_det_list()
        self._status(f"Loaded: {os.path.basename(path)}")

    def _start_smart_scan(self):
        self.btn_scan.configure(state="disabled")
        self._status("🔍 SCANNING FOR PII...", C["warning"])
        self._prog(0.1)
        threading.Thread(target=self._run_scan, daemon=True).start()

    def _run_scan(self):
        try:
            self._prog(0.4)
            results = self.auto_redactor.scan_document(self.selected_image_path)
            self._prog(0.8)
            self.scan_results = results
            self.after(0, self._show_scan_results)
            self._prog(1.0)
            if results:
                self._status(f"🎯 FOUND {len(results)} TARGET(S)", C["success"])
            else:
                self._status("ALL CLEAR: No sensitive data found.", C["text2"])
        except TesseractNotInstalledError as e:
            self._status("❌ TESSERACT NOT INSTALLED", C["danger"])
            self.after(0, lambda: messagebox.showerror("Tesseract Required", str(e)))
        except Exception as e:
            self._status("❌ SCAN FAILED", C["danger"])
            self.after(0, lambda: messagebox.showerror("Scan Error", str(e)))
        finally:
            self.after(0, lambda: self.btn_scan.configure(state="normal"))
            self._prog(0)

    def _show_scan_results(self):
        self._clear_det_list()
        self.scan_check_vars = []
        if not self.scan_results:
            ctk.CTkLabel(self.det_scroll, text="No sensitive data detected.",
                         text_color=C["text2"]).pack(padx=10, pady=10)
            return

        self.lbl_det.configure(text=f"Detected Targets ({len(self.scan_results)})")
        for det in self.scan_results:
            var = ctk.BooleanVar(value=True)
            self.scan_check_vars.append(var)
            sev_color = SEV.get(det["severity"], C["accent"])

            fr = ctk.CTkFrame(self.det_scroll, fg_color=C["card"],
                              corner_radius=8, border_width=1, border_color=C["border"])
            fr.pack(padx=5, pady=4, fill="x")

            # Severity accent bar
            ctk.CTkFrame(fr, width=4, fg_color=sev_color, corner_radius=0).pack(side="left", fill="y")

            ctk.CTkCheckBox(fr, variable=var, text="", width=24,
                            checkbox_width=20, checkbox_height=20,
                            fg_color=C["accent"], hover_color=C["accent_h"],
                            command=self._update_smart_preview).pack(side="left", padx=(8, 4), pady=8)

            info = ctk.CTkFrame(fr, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            ctk.CTkLabel(info, text=det["type"],
                         font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                         text_color=C["text"], anchor="w").pack(fill="x")

            val = det["value"]
            if len(val) > 22: val = val[:19] + "..."
            ctk.CTkLabel(info, text=val, font=ctk.CTkFont(family=FNT, size=11),
                         text_color=sev_color, anchor="w").pack(fill="x")

        self.btn_secure.configure(state="normal")
        self._update_smart_preview()

    def _update_smart_preview(self):
        if not self.selected_image_path: return
        img = Image.open(self.selected_image_path).copy()
        draw = ImageDraw.Draw(img)
        try: fnt = ImageFont.truetype("arialbd.ttf", 18)
        except: fnt = ImageFont.load_default()

        for i, det in enumerate(self.scan_results):
            if i < len(self.scan_check_vars) and self.scan_check_vars[i].get():
                b = det["bbox"]
                sc = SEV.get(det["severity"], C["accent"])
                draw.rectangle([b["x"], b["y"], b["x"]+b["w"], b["y"]+b["h"]], outline=sc, width=4)
                try:
                    tb = draw.textbbox((b["x"], max(0, b["y"]-22)), det["type"], font=fnt)
                    draw.rectangle(tb, fill=sc)
                    draw.text((b["x"], max(0, b["y"]-22)), det["type"], font=fnt, fill="black")
                except: pass

        self._show_preview(img, self.smart_preview)

    def _clear_det_list(self):
        for w in self.det_scroll.winfo_children(): w.destroy()
        self.lbl_det.configure(text="Detected Targets (0)")

    def _start_smart_encrypt(self):
        pwd = self.smart_pwd.get()
        if not pwd:
            messagebox.showwarning("Key Required", "Provide an encryption key.")
            return
        selected = [d for i, d in enumerate(self.scan_results)
                    if i < len(self.scan_check_vars) and self.scan_check_vars[i].get()]
        if not selected:
            messagebox.showwarning("No Targets", "Select at least one region.")
            return
        self.btn_secure.configure(state="disabled")
        threading.Thread(target=self._run_smart_encrypt, args=(selected, pwd), daemon=True).start()

    def _run_smart_encrypt(self, dets, pwd):
        try:
            self._status("🔒 ENCRYPTING...", C["warning"])
            self._prog(0.2)
            orig = Image.open(self.selected_image_path)
            regions, bboxes = [], []

            for i, d in enumerate(dets):
                b = d["bbox"]
                x, y, w, h = max(0, b["x"]), max(0, b["y"]), b["w"], b["h"]
                iw, ih = orig.size
                w, h = min(w, iw-x), min(h, ih-y)
                if w <= 0 or h <= 0: continue
                roi = orig.crop((x, y, x+w, y+h))
                buf = io.BytesIO()
                roi.save(buf, format="PNG")
                regions.append({"x": x, "y": y, "w": w, "h": h, "type": d["type"],
                                "image_data": base64.b64encode(buf.getvalue()).decode()})
                bboxes.append({"x": x, "y": y, "w": w, "h": h})
                self._prog(0.2 + 0.3*((i+1)/len(dets)))

            if not regions: return
            payload = json.dumps({"version": 2, "regions": regions})
            enc = self.crypto.encrypt(payload.encode(), pwd)
            self._prog(0.6)

            redacted = self.img_proc.draw_redaction_boxes(self.selected_image_path, bboxes, mode="black")
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            self.img_proc.save_image(redacted, tmp)

            save = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if not save:
                os.remove(tmp); return
            self._prog(0.8)
            self.stego.hide_data(tmp, save, enc)
            os.remove(tmp)
            self._prog(1.0)
            self._status("✅ ASSET SECURED", C["success"])
            self.after(0, lambda: messagebox.showinfo("Success", f"Saved to:\n{save}"))
        except Exception as e:
            self._status("❌ ERROR", C["danger"])
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self._prog(0)
            self.after(0, lambda: self.btn_secure.configure(state="normal"))

    # ═══════════════════════════════════════════════════════════════════════════
    #  MANUAL REDACT LOGIC (Draw-box based)
    # ═══════════════════════════════════════════════════════════════════════════
    def _manual_load(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif")])
        if not path: return
        self.selected_image_path = path
        self._load_image_to_canvas(path)
        self._status(f"Loaded: {os.path.basename(path)} — draw a box to select area")

    def _start_manual_encrypt(self):
        if not self.selected_image_path or not self._draw_box:
            messagebox.showwarning("Error", "Load a document and draw a redaction box first.")
            return
        pwd = self.manual_pwd.get()
        if not pwd:
            messagebox.showwarning("Error", "Password is required.")
            return
        x1, y1, x2, y2 = self._draw_box
        w, h = x2 - x1, y2 - y1
        self.btn_manual_go.configure(state="disabled")
        threading.Thread(target=self._run_manual, args=(x1, y1, w, h, pwd), daemon=True).start()

    def _run_manual(self, x, y, w, h, pwd):
        try:
            self._status("🔒 Processing...", C["warning"])
            self._prog(0.2)
            orig = Image.open(self.selected_image_path)
            roi = orig.crop((x, y, x+w, y+h))
            buf = io.BytesIO()
            roi.save(buf, format="PNG")
            payload = json.dumps({"version": 2, "regions": [
                {"x": x, "y": y, "w": w, "h": h, "type": "manual",
                 "image_data": base64.b64encode(buf.getvalue()).decode()}
            ]})
            enc = self.crypto.encrypt(payload.encode(), pwd)
            self._prog(0.5)

            redacted = self.img_proc.draw_redaction_box(self.selected_image_path, x, y, w, h)
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            self.img_proc.save_image(redacted, tmp)

            save = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if not save:
                os.remove(tmp); return
            self._prog(0.8)
            self.stego.hide_data(tmp, save, enc)
            os.remove(tmp)
            self._prog(1.0)
            self._status("✅ SAVED", C["success"])
            self.after(0, lambda: messagebox.showinfo("Success", f"Saved to:\n{save}"))
        except Exception as e:
            self._status("❌ ERROR", C["danger"])
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self._prog(0)
            self.after(0, lambda: self.btn_manual_go.configure(state="normal"))

    # ═══════════════════════════════════════════════════════════════════════════
    #  DECRYPT LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def _decrypt_load(self):
        path = filedialog.askopenfilename(filetypes=[("PNG Images", "*.png")])
        if path:
            self.dec_image_path = path
            self._show_preview(path, self.decrypt_preview)
            self._status(f"Loaded: {os.path.basename(path)}")

    def _start_decryption(self):
        if not self.dec_image_path:
            messagebox.showwarning("Error", "Load a secured document first.")
            return
        pwd = self.decrypt_pwd.get()
        if not pwd:
            messagebox.showwarning("Error", "Password is required.")
            return
        threading.Thread(target=self._run_decrypt, args=(pwd,), daemon=True).start()

    def _run_decrypt(self, pwd):
        try:
            self._status("🔓 AUTHENTICATING...", C["warning"])
            self._prog(0.3)
            blob = self.stego.extract_data(self.dec_image_path)
            js = self.crypto.decrypt(blob, pwd).decode()
            data = json.loads(js)

            regions = data["regions"] if data.get("version") == 2 else [
                {"x": data["x"], "y": data["y"], "w": data["w"], "h": data["h"],
                 "type": "legacy", "image_data": data["image_data"]}
            ]

            full = Image.open(self.dec_image_path)
            draw = ImageDraw.Draw(full)
            info = []

            for i, r in enumerate(regions):
                x, y, w, h = r["x"], r["y"], r["w"], r["h"]
                patch = Image.open(io.BytesIO(base64.b64decode(r["image_data"])))
                full.paste(patch, (x, y))
                draw.rectangle([x, y, x+w, y+h], outline=C["success"], width=4)
                info.append(f"✓ Region {i+1}: {r.get('type', 'data')} [{w}×{h}]")
                self._prog(0.3 + 0.6*((i+1)/len(regions)))

            self.after(0, lambda img=full: self._show_preview(img, self.decrypt_preview))
            txt = f"VERIFIED: {len(regions)} region(s) restored\n\n" + "\n".join(info)
            self.after(0, lambda: self.dec_info_label.configure(text=txt, text_color=C["success"]))
            self._prog(1.0)
            self._status("✅ RESTORATION COMPLETE", C["success"])
        except ValueError:
            self._status("❌ ACCESS DENIED", C["danger"])
            self.after(0, lambda: self.dec_info_label.configure(
                text="ACCESS DENIED: Wrong password or corrupt data.", text_color=C["danger"]))
        except Exception as e:
            self._status("❌ FAILED", C["danger"])
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self._prog(0)