"""
SecureGuard AI — Premium Document Redaction System
Ultra-modern dark-mode GUI with polished design.
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

from gui.animations import pulse_button, typewriter_text, glow_border

from core.crypto_manager import CryptoManager
from core.stego_manager import StegoManager
from core.image_processor import ImageProcessor
from core.auto_redactor import AutoRedactor
from core.ocr_engine import TesseractNotInstalledError
from core.pdf_converter import PDFConverter

# ─── Theme ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

C = {
    "bg":           "#080B12",
    "card":         "#111827",
    "card2":        "#1A2332",
    "input":        "#1E293B",
    "accent":       "#00E5FF",
    "accent_h":     "#00B8D4",
    "accent_dim":   "#0D4F5C",
    "primary":      "#7C3AED",
    "primary_h":    "#6D28D9",
    "primary_dim":  "#3B1F7A",
    "danger":       "#FF2A55",
    "danger_h":     "#E61A41",
    "danger_dim":   "#5C1028",
    "success":      "#00E676",
    "success_h":    "#00C853",
    "success_dim":  "#0A4D2E",
    "warning":      "#FFB300",
    "text":         "#F8FAFC",
    "text2":        "#94A3B8",
    "text3":        "#64748B",
    "border":       "#1E293B",
    "border_h":     "#334155",
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
        self.geometry("1360x880")
        self.minsize(1100, 750)
        self.configure(fg_color=C["bg"])

        self.crypto = CryptoManager()
        self.stego = StegoManager()
        self.img_proc = ImageProcessor()
        self.auto_redactor = AutoRedactor()
        self.pdf_conv = PDFConverter(dpi=200)

        self.selected_image_path = None
        self.dec_image_path = None
        self.scan_results = []
        self.scan_check_vars = []

        # PDF state
        self._pdf_path = None
        self._pdf_pages = 0
        self._pdf_page = 0
        self._pdf_temp_files = []

        # Manual draw state
        self._draw_img = None
        self._draw_tk_img = None
        self._draw_scale = 1.0
        self._draw_rect_id = None
        self._draw_start = None
        self._draw_box = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        self._create_header()
        self._create_tabs()
        self._create_status_bar()

        # Pulsing CTA buttons
        self.after(500, lambda: pulse_button(self.btn_scan, C["primary"], "#9D5CFF"))
        self.after(500, lambda: pulse_button(self.btn_secure, C["danger"], "#FF5C7A"))
        self.after(500, lambda: pulse_button(self.btn_manual_go, C["danger"], "#FF5C7A"))
        self.after(500, lambda: pulse_button(self.btn_decrypt_go, C["success"], "#33FF99"))

    # ═══════════════════════════════════════════════════════════════════════════
    #  HEADER
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_header(self):
        hdr = ctk.CTkFrame(self, height=72, fg_color=C["card"],
                           corner_radius=0, border_width=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(2, weight=1)

        # Shield icon
        ctk.CTkLabel(hdr, text="🛡️",
                     font=ctk.CTkFont(size=30)).grid(row=0, column=0,
                     padx=(28, 6), pady=14, sticky="w")

        # Title
        tf = ctk.CTkFrame(hdr, fg_color="transparent")
        tf.grid(row=0, column=1, pady=14, sticky="w")
        ctk.CTkLabel(tf, text="Secure",
                     font=ctk.CTkFont(family=FNT, size=24, weight="bold"),
                     text_color=C["text"]).pack(side="left")
        ctk.CTkLabel(tf, text="Guard",
                     font=ctk.CTkFont(family=FNT, size=24, weight="bold"),
                     text_color=C["accent"]).pack(side="left")
        ctk.CTkLabel(tf, text=" AI",
                     font=ctk.CTkFont(family=FNT, size=24, weight="bold"),
                     text_color=C["primary"]).pack(side="left")

        # Subtitle
        ctk.CTkLabel(hdr, text="Next-Gen Document Redaction & Intelligence",
                     font=ctk.CTkFont(family=FNT, size=12, slant="italic"),
                     text_color=C["text3"]).grid(row=0, column=2,
                     padx=20, pady=14, sticky="w")

        # Version badge
        badge = ctk.CTkFrame(hdr, fg_color=C["primary_dim"], corner_radius=20,
                             border_width=1, border_color=C["primary"])
        badge.grid(row=0, column=3, padx=28, pady=14, sticky="e")
        ctk.CTkLabel(badge, text="  v2.0 PRO  ",
                     font=ctk.CTkFont(family=FNT, size=10, weight="bold"),
                     text_color=C["primary"]).pack(padx=8, pady=4)

    # ═══════════════════════════════════════════════════════════════════════════
    #  NAVIGATION + VIEWS
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_tabs(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=1, column=0, padx=20, pady=(10, 8), sticky="nsew")
        container.grid_columnconfigure(1, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Sidebar nav
        nav = ctk.CTkFrame(container, width=210, fg_color=C["card"],
                           corner_radius=16, border_width=1, border_color=C["border"])
        nav.grid(row=0, column=0, padx=(0, 12), sticky="nsew")
        nav.grid_propagate(False)

        ctk.CTkLabel(nav, text="  MODULES",
                     font=ctk.CTkFont(family=FNT, size=10, weight="bold"),
                     text_color=C["text3"]).pack(padx=18, pady=(28, 12), fill="x")

        self.nav_btns = {}
        nav_items = [
            ("🔍  Smart Scan",    "smart",   C["accent"]),
            ("✏️  Draw & Redact", "manual",  C["danger"]),
            ("🔓  Restore",       "decrypt", C["success"]),
        ]
        for label, key, color in nav_items:
            b = ctk.CTkButton(nav, text=label, height=46,
                              font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                              fg_color="transparent", text_color=C["text2"],
                              hover_color=C["card2"], anchor="w",
                              corner_radius=12,
                              command=lambda k=key: self._switch(k))
            b.pack(padx=10, pady=3, fill="x")
            self.nav_btns[key] = (b, color)

        # Decorative separator
        ctk.CTkFrame(nav, height=1, fg_color=C["border"]).pack(
            padx=20, pady=(20, 15), fill="x")

        # Info card in sidebar
        info = ctk.CTkFrame(nav, fg_color=C["card2"], corner_radius=12,
                            border_width=1, border_color=C["border"])
        info.pack(padx=14, pady=5, fill="x")
        ctk.CTkLabel(info, text="💡 Quick Tip",
                     font=ctk.CTkFont(family=FNT, size=11, weight="bold"),
                     text_color=C["accent"]).pack(padx=12, pady=(10, 4), anchor="w")
        ctk.CTkLabel(info, text="Use Smart Scan to auto-\ndetect sensitive data like\nSSN, emails, and more.",
                     font=ctk.CTkFont(family=FNT, size=10),
                     text_color=C["text3"], justify="left").pack(padx=12, pady=(0, 10), anchor="w")

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
        for k, (b, color) in self.nav_btns.items():
            b.configure(fg_color="transparent", text_color=C["text2"])
            self.views[k].grid_forget()
        btn, col = self.nav_btns[key]
        btn.configure(fg_color=C["card2"], text_color=col)
        self.views[key].grid(row=0, column=0, sticky="nsew")

    # ═══════════════════════════════════════════════════════════════════════════
    #  EMPTY STATE WIDGET
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_empty_state(self, parent, icon, title, subtitle, color):
        """Create a premium empty-state placeholder."""
        wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # Circular icon holder
        icon_bg = ctk.CTkFrame(wrapper, width=80, height=80, fg_color=color,
                               corner_radius=40)
        icon_bg.pack(pady=(0, 16))
        icon_bg.pack_propagate(False)
        ctk.CTkLabel(icon_bg, text=icon, font=ctk.CTkFont(size=32),
                     text_color=C["text"]).place(relx=0.5, rely=0.5,
                     anchor="center")

        ctk.CTkLabel(wrapper, text=title,
                     font=ctk.CTkFont(family=FNT, size=16, weight="bold"),
                     text_color=C["text"]).pack(pady=(0, 6))
        ctk.CTkLabel(wrapper, text=subtitle,
                     font=ctk.CTkFont(family=FNT, size=12),
                     text_color=C["text3"]).pack()

        return wrapper

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
                          corner_radius=16, border_width=1, border_color=C["border"])
        lp.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        lp.grid_propagate(False)
        lp.grid_columnconfigure(0, weight=1)

        # Section header
        hdr = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=12)
        hdr.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        ctk.CTkLabel(hdr, text="🧠  Intelligence Engine",
                     font=ctk.CTkFont(family=FNT, size=15, weight="bold"),
                     text_color=C["text"]).pack(padx=14, pady=10, anchor="w")

        ctk.CTkButton(lp, text="📂  Load Document", height=44,
                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                      fg_color=C["input"], hover_color=C["border_h"],
                      border_width=1, border_color=C["border_h"], text_color=C["text"],
                      corner_radius=12,
                      command=self._smart_load).grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        self.btn_scan = ctk.CTkButton(lp, text="⚡  Start AI Scan", height=44,
                                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                                      fg_color=C["primary"], hover_color=C["primary_h"],
                                      corner_radius=12,
                                      command=self._start_smart_scan, state="disabled")
        self.btn_scan.grid(row=2, column=0, padx=15, pady=(5, 12), sticky="ew")

        self.lbl_det = ctk.CTkLabel(lp, text="Detected Targets (0)",
                                    font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                                    text_color=C["text2"], anchor="w")
        self.lbl_det.grid(row=3, column=0, padx=20, pady=(8, 4), sticky="ew")

        self.det_scroll = ctk.CTkScrollableFrame(lp, fg_color=C["input"],
                                                  corner_radius=12)
        self.det_scroll.grid(row=4, column=0, padx=12, pady=(0, 10), sticky="nsew")
        lp.grid_rowconfigure(4, weight=1)

        # Password section
        sf = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=12)
        sf.grid(row=5, column=0, padx=12, pady=(0, 12), sticky="ew")
        sf.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sf, text="🔑  Encryption Key",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
        self.smart_pwd = ctk.CTkEntry(sf, placeholder_text="Enter password...", show="•", height=40,
                                      fg_color=C["input"], border_color=C["border_h"],
                                      text_color=C["accent"], corner_radius=10)
        self.smart_pwd.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.btn_secure = ctk.CTkButton(sf, text="🔒  Redact & Secure", height=48,
                                        font=ctk.CTkFont(family=FNT, size=14, weight="bold"),
                                        fg_color=C["danger"], hover_color=C["danger_h"],
                                        corner_radius=12,
                                        command=self._start_smart_encrypt, state="disabled")
        self.btn_secure.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")

        # Right panel
        rp = ctk.CTkFrame(v, fg_color=C["card"], corner_radius=16,
                          border_width=1, border_color=C["border"])
        rp.grid(row=0, column=1, sticky="nsew")
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)
        glow_border(rp, C["border"], C["accent_dim"], interval=80)

        ctk.CTkLabel(rp, text="📊  Visual Analysis",
                     font=ctk.CTkFont(family=FNT, size=15, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        bg = ctk.CTkFrame(rp, fg_color=C["bg"], corner_radius=12)
        bg.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        bg.grid_columnconfigure(0, weight=1)
        bg.grid_rowconfigure(0, weight=1)

        self.smart_preview = ctk.CTkLabel(bg, text="")
        self.smart_preview.grid(row=0, column=0)
        self.smart_empty = self._create_empty_state(
            bg, "📂", "No Document Loaded",
            "Click 'Load Document' to get started", C["accent_dim"])

    # ═══════════════════════════════════════════════════════════════════════════
    #  VIEW 2: DRAW & REDACT
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_manual(self):
        v = self.views["manual"]
        v.grid_columnconfigure(0, weight=0)
        v.grid_columnconfigure(1, weight=1)
        v.grid_rowconfigure(0, weight=1)

        # Left panel
        lp = ctk.CTkFrame(v, width=300, fg_color=C["card"],
                          corner_radius=16, border_width=1, border_color=C["border"])
        lp.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        lp.grid_propagate(False)
        lp.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=12)
        hdr.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        ctk.CTkLabel(hdr, text="✏️  Draw & Redact",
                     font=ctk.CTkFont(family=FNT, size=15, weight="bold"),
                     text_color=C["text"]).pack(padx=14, pady=10, anchor="w")

        ctk.CTkButton(lp, text="📂  Load Document", height=44,
                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                      fg_color=C["input"], hover_color=C["border_h"],
                      border_width=1, border_color=C["border_h"], text_color=C["text"],
                      corner_radius=12,
                      command=self._manual_load).grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        # Instructions
        tip = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=10)
        tip.grid(row=2, column=0, padx=15, pady=(10, 5), sticky="ew")
        ctk.CTkLabel(tip, text="💡 Click and drag on the\nimage to draw a redaction box.",
                     font=ctk.CTkFont(family=FNT, size=11),
                     text_color=C["text3"], justify="left").pack(padx=12, pady=10, anchor="w")

        # Coordinates display
        coord_frame = ctk.CTkFrame(lp, fg_color=C["input"], corner_radius=12,
                                   border_width=1, border_color=C["border"])
        coord_frame.grid(row=3, column=0, padx=15, pady=8, sticky="ew")

        ctk.CTkLabel(coord_frame, text="📐 Selected Region",
                     font=ctk.CTkFont(family=FNT, size=11, weight="bold"),
                     text_color=C["text2"]).grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")
        self.lbl_coords = ctk.CTkLabel(coord_frame, text="No selection yet",
                                       font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                                       text_color=C["accent"], justify="left")
        self.lbl_coords.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="w")

        ctk.CTkButton(lp, text="✖  Clear Selection", height=34,
                      font=ctk.CTkFont(family=FNT, size=12),
                      fg_color="transparent", hover_color=C["input"],
                      border_width=1, border_color=C["border_h"], text_color=C["text2"],
                      corner_radius=10,
                      command=self._clear_draw_box).grid(row=4, column=0, padx=15, pady=4, sticky="ew")

        # Password
        pwd_frame = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=12)
        pwd_frame.grid(row=5, column=0, padx=12, pady=(10, 12), sticky="ew")
        pwd_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pwd_frame, text="🔑  Encryption Key",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
        self.manual_pwd = ctk.CTkEntry(pwd_frame, placeholder_text="Enter password...", show="•", height=40,
                                       fg_color=C["input"], border_color=C["border_h"],
                                       text_color=C["accent"], corner_radius=10)
        self.manual_pwd.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.btn_manual_go = ctk.CTkButton(pwd_frame, text="🔒  Redact & Secure", height=48,
                                           font=ctk.CTkFont(family=FNT, size=14, weight="bold"),
                                           fg_color=C["danger"], hover_color=C["danger_h"],
                                           corner_radius=12,
                                           command=self._start_manual_encrypt, state="disabled")
        self.btn_manual_go.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")

        # Right panel — Canvas for drawing
        rp = ctk.CTkFrame(v, fg_color=C["card"], corner_radius=16,
                          border_width=1, border_color=C["border"])
        rp.grid(row=0, column=1, sticky="nsew")
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)
        glow_border(rp, C["border"], C["danger_dim"], interval=80)

        ctk.CTkLabel(rp, text="🎯  Draw Redaction Box",
                     font=ctk.CTkFont(family=FNT, size=15, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        canvas_bg = ctk.CTkFrame(rp, fg_color=C["bg"], corner_radius=12)
        canvas_bg.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        canvas_bg.grid_columnconfigure(0, weight=1)
        canvas_bg.grid_rowconfigure(0, weight=1)

        self.draw_canvas = Canvas(canvas_bg, bg=C["bg"], highlightthickness=0, cursor="crosshair")
        self.draw_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.draw_canvas.bind("<ButtonPress-1>", self._on_draw_press)
        self.draw_canvas.bind("<B1-Motion>", self._on_draw_drag)
        self.draw_canvas.bind("<ButtonRelease-1>", self._on_draw_release)

        self.draw_canvas.create_text(300, 200,
            text="Load a document, then drag to draw a box.",
            fill=C["text3"], font=(FNT, 13), tags="placeholder")

    # ═══════════════════════════════════════════════════════════════════════════
    #  VIEW 3: DECRYPT
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_decrypt(self):
        v = self.views["decrypt"]
        v.grid_columnconfigure(0, weight=0)
        v.grid_columnconfigure(1, weight=1)
        v.grid_rowconfigure(0, weight=1)

        lp = ctk.CTkFrame(v, width=340, fg_color=C["card"],
                          corner_radius=16, border_width=1, border_color=C["border"])
        lp.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        lp.grid_propagate(False)
        lp.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=12)
        hdr.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        ctk.CTkLabel(hdr, text="🔓  Recovery Module",
                     font=ctk.CTkFont(family=FNT, size=15, weight="bold"),
                     text_color=C["text"]).pack(padx=14, pady=10, anchor="w")

        ctk.CTkButton(lp, text="📂  Load Secured Asset", height=44,
                      font=ctk.CTkFont(family=FNT, size=13, weight="bold"),
                      fg_color=C["input"], hover_color=C["border_h"],
                      border_width=1, border_color=C["border_h"], text_color=C["text"],
                      corner_radius=12,
                      command=self._decrypt_load).grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        pwd_frame = ctk.CTkFrame(lp, fg_color=C["card2"], corner_radius=12)
        pwd_frame.grid(row=2, column=0, padx=12, pady=(12, 8), sticky="ew")
        pwd_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pwd_frame, text="🔑  Decryption Key",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
        self.decrypt_pwd = ctk.CTkEntry(pwd_frame, placeholder_text="Enter password...", show="•", height=40,
                                        fg_color=C["input"], border_color=C["border_h"],
                                        text_color=C["accent"], corner_radius=10)
        self.decrypt_pwd.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="ew")

        self.btn_decrypt_go = ctk.CTkButton(pwd_frame, text="🔓  Authenticate & Reveal", height=48,
                      font=ctk.CTkFont(family=FNT, size=14, weight="bold"),
                      fg_color=C["success"], hover_color=C["success_h"],
                      corner_radius=12,
                      command=self._start_decryption)
        self.btn_decrypt_go.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")

        # Results
        ctk.CTkLabel(lp, text="📋  Decryption Results",
                     font=ctk.CTkFont(family=FNT, size=12, weight="bold"),
                     text_color=C["text2"]).grid(row=3, column=0, padx=20, pady=(8, 4), sticky="w")

        self.dec_info_scroll = ctk.CTkScrollableFrame(lp, fg_color=C["input"],
                                                       corner_radius=12)
        self.dec_info_scroll.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="nsew")
        lp.grid_rowconfigure(4, weight=1)

        self.dec_info_label = ctk.CTkLabel(self.dec_info_scroll,
                                           text="Results appear here after decryption.",
                                           font=ctk.CTkFont(family=FNT, size=12),
                                           text_color=C["text3"], justify="left", wraplength=260)
        self.dec_info_label.pack(padx=12, pady=12, anchor="nw")

        # Right panel
        rp = ctk.CTkFrame(v, fg_color=C["card"], corner_radius=16,
                          border_width=1, border_color=C["border"])
        rp.grid(row=0, column=1, sticky="nsew")
        rp.grid_columnconfigure(0, weight=1)
        rp.grid_rowconfigure(1, weight=1)
        glow_border(rp, C["border"], C["success_dim"], interval=80)

        ctk.CTkLabel(rp, text="🖼️  Restored Preview",
                     font=ctk.CTkFont(family=FNT, size=15, weight="bold"),
                     text_color=C["text"]).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        bg = ctk.CTkFrame(rp, fg_color=C["bg"], corner_radius=12)
        bg.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        bg.grid_columnconfigure(0, weight=1)
        bg.grid_rowconfigure(0, weight=1)

        self.decrypt_preview = ctk.CTkLabel(bg, text="")
        self.decrypt_preview.grid(row=0, column=0)
        self.decrypt_empty = self._create_empty_state(
            bg, "🔓", "No Secured Document",
            "Load a secured .png or .pdf to decrypt", C["success_dim"])

    # ═══════════════════════════════════════════════════════════════════════════
    #  STATUS BAR
    # ═══════════════════════════════════════════════════════════════════════════
    def _create_status_bar(self):
        bar = ctk.CTkFrame(self, height=40, fg_color=C["card"], corner_radius=0)
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        bar.grid_propagate(False)

        self.status_lbl = ctk.CTkLabel(bar, text="● SYSTEM READY",
                                       font=ctk.CTkFont(family=FNT, size=11, weight="bold"),
                                       text_color=C["text3"])
        self.status_lbl.grid(row=0, column=0, padx=24, pady=10, sticky="w")

        self.progress = ctk.CTkProgressBar(bar, width=200, height=6, corner_radius=3,
                                           progress_color=C["accent"], fg_color=C["input"])
        self.progress.grid(row=0, column=1, padx=24, pady=16, sticky="e")
        self.progress.set(0)

    def _status(self, msg, color=None):
        try:
            self.status_lbl.configure(text_color=color or C["text3"])
            typewriter_text(self.status_lbl, msg, interval=18)
        except:
            pass

    def _prog(self, v):
        try:
            self.progress.set(v)
        except:
            pass

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

            # Hide empty state
            if label == self.smart_preview and hasattr(self, 'smart_empty'):
                self.smart_empty.place_forget()
                self.smart_preview_img = img
            if label == self.decrypt_preview and hasattr(self, 'decrypt_empty'):
                self.decrypt_empty.place_forget()
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
        self._draw_offset_x = (cw - display_w) // 2
        self._draw_offset_y = (ch - display_h) // 2
        self.draw_canvas.create_image(self._draw_offset_x, self._draw_offset_y,
                                       anchor="nw", image=self._draw_tk_img, tags="bg_image")

    def _on_draw_press(self, event):
        if self._draw_img is None:
            return
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
        ox, oy = self._draw_offset_x, self._draw_offset_y
        scale = self._draw_scale

        x1 = int((min(sx, ex) - ox) / scale)
        y1 = int((min(sy, ey) - oy) / scale)
        x2 = int((max(sx, ex) - ox) / scale)
        y2 = int((max(sy, ey) - oy) / scale)

        iw, ih = self._draw_img.size
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(iw, x2), min(ih, y2)

        w, h = x2 - x1, y2 - y1
        if w > 5 and h > 5:
            self._draw_box = (x1, y1, x2, y2)
            self.lbl_coords.configure(text=f"X={x1}  Y={y1}  W={w}  H={h}")
            self.btn_manual_go.configure(state="normal")
            self._status(f"● Selection: {w}×{h} pixels")
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

    def _cleanup_pdf_temps(self):
        """Remove any temp files from previous PDF loads."""
        for f in self._pdf_temp_files:
            try: os.remove(f)
            except: pass
        self._pdf_temp_files = []

    def _load_file_as_image(self, path, page=0):
        if PDFConverter.is_pdf(path):
            self._pdf_path = path
            self._pdf_pages = self.pdf_conv.get_page_count(path)
            self._pdf_page = page
            tmp = self.pdf_conv.pdf_page_to_temp_file(path, page)
            self._pdf_temp_files.append(tmp)
            return tmp
        else:
            self._pdf_path = None
            self._pdf_pages = 0
            self._pdf_page = 0
            return path

    FILE_TYPES = [("Documents", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.pdf")]

    def _smart_load(self):
        path = filedialog.askopenfilename(filetypes=self.FILE_TYPES)
        if not path: return
        self._cleanup_pdf_temps()
        try:
            img_path = self._load_file_as_image(path)
        except Exception as e:
            messagebox.showerror("Load Error", str(e)); return
        self.selected_image_path = img_path
        self._show_preview(img_path, self.smart_preview)
        self.btn_scan.configure(state="normal")
        self.btn_secure.configure(state="disabled")
        self.scan_results = []
        self._clear_det_list()
        name = os.path.basename(path)
        page_info = f" (page {self._pdf_page + 1}/{self._pdf_pages})" if self._pdf_path else ""
        self._status(f"● Loaded: {name}{page_info}")

    def _start_smart_scan(self):
        self.btn_scan.configure(state="disabled")
        self._status("● SCANNING FOR PII...", C["warning"])
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
                self._status(f"● FOUND {len(results)} TARGET(S)", C["success"])
            else:
                self._status("● ALL CLEAR: No sensitive data found.", C["text3"])
        except TesseractNotInstalledError as e:
            _msg = str(e)
            self._status("● TESSERACT NOT INSTALLED", C["danger"])
            self.after(0, lambda m=_msg: messagebox.showerror("Tesseract Required", m))
        except Exception as e:
            _msg = str(e)
            self._status("● SCAN FAILED", C["danger"])
            self.after(0, lambda m=_msg: messagebox.showerror("Scan Error", m))
        finally:
            self.after(0, lambda: self.btn_scan.configure(state="normal"))
            self._prog(0)

    def _show_scan_results(self):
        self._clear_det_list()
        self.scan_check_vars = []
        if not self.scan_results:
            ctk.CTkLabel(self.det_scroll, text="No sensitive data detected.",
                         text_color=C["text3"]).pack(padx=10, pady=10)
            return

        self.lbl_det.configure(text=f"Detected Targets ({len(self.scan_results)})")
        for det in self.scan_results:
            var = ctk.BooleanVar(value=True)
            self.scan_check_vars.append(var)
            sev_color = SEV.get(det["severity"], C["accent"])

            fr = ctk.CTkFrame(self.det_scroll, fg_color=C["card2"],
                              corner_radius=10, border_width=1, border_color=C["border"])
            fr.pack(padx=4, pady=3, fill="x")

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

    def _extract_raw_slots(self, image_path):
        """
        Extract the raw list of independently-encrypted slot blobs from a stego image.
        Returns a list of bytes objects — one per slot.
        If the image has no stego payload, returns [].
        """
        try:
            blob = self.stego.extract_data(image_path)
            # Try to parse as multislot wrapper
            try:
                wrapper = json.loads(blob.decode())
                if wrapper.get("format") == "multislot":
                    # Each slot is base64-encoded raw encrypted bytes
                    return [base64.b64decode(s) for s in wrapper.get("slots", [])]
            except Exception:
                pass
            # Not a multislot wrapper: it's a single-slot raw encrypted blob
            return [blob]
        except Exception:
            return []  # Image has no stego payload at all

    def _wrap_multislot(self, slot_blobs):
        """
        Wrap a list of raw encrypted blobs into a multislot JSON payload (bytes).
        """
        wrapper = {
            "format": "multislot",
            "slots": [base64.b64encode(b).decode() for b in slot_blobs]
        }
        return json.dumps(wrapper).encode()

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
            self._status("● ENCRYPTING...", C["warning"])
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

            # Encrypt new regions as a fresh slot
            payload = json.dumps({"version": 2, "regions": regions}).encode()
            new_slot = self.crypto.encrypt(payload, pwd)

            # Collect all existing slots from the source image (different passwords OK)
            existing_slots = self._extract_raw_slots(self.selected_image_path)
            all_slots = existing_slots + [new_slot]
            if existing_slots:
                self._status(f"● Chaining {len(existing_slots)} prior slot(s) + 1 new", C["warning"])

            # Wrap everything as a multislot payload and hide it
            combined = self._wrap_multislot(all_slots)
            self._prog(0.6)

            redacted = self.img_proc.draw_redaction_boxes(self.selected_image_path, bboxes, mode="black")
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            self.img_proc.save_image(redacted, tmp)

            save = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image (stego)", "*.png"), ("PDF Document", "*.pdf")]
            )
            if not save:
                os.remove(tmp); return
            self._prog(0.8)

            if save.lower().endswith(".pdf"):
                PDFConverter.save_secured_pdf(tmp, combined, save)
            else:
                self.stego.hide_data(tmp, save, combined)

            os.remove(tmp)
            self._prog(1.0)
            self._status("● ASSET SECURED", C["success"])
            fmt = "PDF" if save.lower().endswith(".pdf") else "PNG"
            self.after(0, lambda s=save, f=fmt: messagebox.showinfo("Success", f"Saved as {f}:\n{s}"))
        except Exception as e:
            _msg = str(e)
            self._status("● ERROR", C["danger"])
            self.after(0, lambda m=_msg: messagebox.showerror("Error", m))
        finally:
            self._prog(0)
            self.after(0, lambda: self.btn_secure.configure(state="normal"))

    # ═══════════════════════════════════════════════════════════════════════════
    #  MANUAL REDACT LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def _manual_load(self):
        path = filedialog.askopenfilename(filetypes=self.FILE_TYPES)
        if not path: return
        self._cleanup_pdf_temps()
        try:
            img_path = self._load_file_as_image(path)
        except Exception as e:
            messagebox.showerror("Load Error", str(e)); return
        self.selected_image_path = img_path
        self._load_image_to_canvas(img_path)
        self._status(f"● Loaded: {os.path.basename(path)} — draw a box to select area")

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
            self._status("● Processing...", C["warning"])
            self._prog(0.2)
            orig = Image.open(self.selected_image_path)
            roi = orig.crop((x, y, x+w, y+h))
            buf = io.BytesIO()
            roi.save(buf, format="PNG")
            new_region = {"x": x, "y": y, "w": w, "h": h, "type": "manual",
                          "image_data": base64.b64encode(buf.getvalue()).decode()}

            # Encrypt new region as a fresh slot
            payload = json.dumps({"version": 2, "regions": [new_region]}).encode()
            new_slot = self.crypto.encrypt(payload, pwd)

            # Collect all existing slots from source image (any prior passwords)
            existing_slots = self._extract_raw_slots(self.selected_image_path)
            all_slots = existing_slots + [new_slot]
            if existing_slots:
                self._status(f"● Chaining {len(existing_slots)} prior slot(s) + 1 new", C["warning"])

            combined = self._wrap_multislot(all_slots)
            self._prog(0.5)

            redacted = self.img_proc.draw_redaction_box(self.selected_image_path, x, y, w, h)
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            self.img_proc.save_image(redacted, tmp)

            save = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG Image (stego)", "*.png"), ("PDF Document", "*.pdf")]
            )
            if not save:
                os.remove(tmp); return
            self._prog(0.8)

            if save.lower().endswith(".pdf"):
                PDFConverter.save_secured_pdf(tmp, combined, save)
            else:
                self.stego.hide_data(tmp, save, combined)

            os.remove(tmp)
            self._prog(1.0)
            self._status("● SAVED", C["success"])
            fmt = "PDF" if save.lower().endswith(".pdf") else "PNG"
            self.after(0, lambda s=save, f=fmt: messagebox.showinfo("Success", f"Saved as {f}:\n{s}"))
        except Exception as e:
            _msg = str(e)
            self._status("● ERROR", C["danger"])
            self.after(0, lambda m=_msg: messagebox.showerror("Error", m))
        finally:
            self._prog(0)
            self.after(0, lambda: self.btn_manual_go.configure(state="normal"))

    # ═══════════════════════════════════════════════════════════════════════════
    #  DECRYPT LOGIC
    # ═══════════════════════════════════════════════════════════════════════════
    def _decrypt_load(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Secured Documents", "*.png *.pdf"),
        ])
        if not path:
            return
        self.dec_image_path = path
        if PDFConverter.is_pdf(path):
            try:
                img = PDFConverter.pdf_to_pil_image(path)
                self._show_preview(img, self.decrypt_preview)
            except:
                self.decrypt_preview.configure(text="PDF loaded (preview unavailable)")
        else:
            self._show_preview(path, self.decrypt_preview)
        self._status(f"● Loaded: {os.path.basename(path)}")

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
            self._status("● AUTHENTICATING...", C["warning"])
            self._prog(0.2)

            if PDFConverter.is_pdf(self.dec_image_path):
                raw = PDFConverter.extract_secured_pdf(self.dec_image_path)
            else:
                raw = self.stego.extract_data(self.dec_image_path)

            # ── Detect multislot vs single-slot format ──
            slots_to_try = []
            try:
                wrapper = json.loads(raw.decode())
                if wrapper.get("format") == "multislot":
                    slots_to_try = [base64.b64decode(s) for s in wrapper.get("slots", [])]
                else:
                    slots_to_try = [raw]  # Parsed as JSON but not multislot → single legacy slot
            except Exception:
                slots_to_try = [raw]  # Not JSON at all → raw encrypted single slot

            # ── Try each slot with the given password ──
            all_regions = []
            matched_slots = 0
            for i, slot_blob in enumerate(slots_to_try):
                try:
                    js = self.crypto.decrypt(slot_blob, pwd).decode()
                    data = json.loads(js)
                    if data.get("version") == 2:
                        all_regions.extend(data.get("regions", []))
                    else:
                        # Legacy single-region format
                        all_regions.append({
                            "x": data["x"], "y": data["y"],
                            "w": data["w"], "h": data["h"],
                            "type": "legacy", "image_data": data["image_data"]
                        })
                    matched_slots += 1
                except Exception:
                    pass  # Wrong password for this slot — skip it

            if not all_regions:
                raise ValueError("No data could be decrypted with this password.")

            self._prog(0.5)

            if PDFConverter.is_pdf(self.dec_image_path):
                full = PDFConverter.get_secured_pdf_image(self.dec_image_path)
            else:
                full = Image.open(self.dec_image_path)

            draw = ImageDraw.Draw(full)
            info = []

            for i, r in enumerate(all_regions):
                x, y, w, h = r["x"], r["y"], r["w"], r["h"]
                patch = Image.open(io.BytesIO(base64.b64decode(r["image_data"])))
                full.paste(patch, (x, y))
                draw.rectangle([x, y, x+w, y+h], outline=C["success"], width=4)
                info.append(f"✓ Region {i+1}: {r.get('type', 'data')} [{w}×{h}]")
                self._prog(0.5 + 0.45*((i+1)/len(all_regions)))

            self.after(0, lambda img=full: self._show_preview(img, self.decrypt_preview))
            slot_note = f" ({matched_slots}/{len(slots_to_try)} slot(s) matched)" if len(slots_to_try) > 1 else ""
            txt = f"VERIFIED: {len(all_regions)} region(s) restored{slot_note}\n\n" + "\n".join(info)
            self.after(0, lambda: self.dec_info_label.configure(text="", text_color=C["success"]))
            self.after(0, lambda t=txt: typewriter_text(self.dec_info_label, t, interval=15))
            self._prog(1.0)
            self._status("● RESTORATION COMPLETE", C["success"])
        except ValueError as e:
            err_msg = str(e)
            self._status("● ACCESS DENIED", C["danger"])
            self.after(0, lambda m=err_msg: self.dec_info_label.configure(
                text=f"ACCESS DENIED: {m}", text_color=C["danger"]))
        except Exception as e:
            err_msg = str(e)
            self._status("● FAILED", C["danger"])
            self.after(0, lambda m=err_msg: messagebox.showerror("Error", m))
        finally:
            self._prog(0)
