"""Finestra principale con tutte le operazioni."""
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QTabWidget, QLineEdit, QCheckBox, QComboBox, QGroupBox, QSplitter,
)
from PySide6.QtCore import Qt, QThread, Signal

from core import merger, optimizer, extractor, ocr
from ui.pdf_preview import PdfPreviewWidget


class Worker(QThread):
    """Esegue operazioni pesanti senza bloccare la UI."""
    done = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn, self.args, self.kwargs = fn, args, kwargs

    def run(self):
        try:
            self.done.emit(self.fn(*self.args, **self.kwargs))
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Studio")
        self.resize(1100, 720)

        # Stato
        self.files: list[str] = []
        self.split_file: str | None = None
        self.opt_file: str | None = None
        self.ext_file: str | None = None
        self.ocr_file: str | None = None

        self._build_ui()

    # ============================================================
    # COSTRUZIONE UI
    # ============================================================
    def _build_ui(self):
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px;
            }
            QTabBar::tab {
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                min-width: 90px;
            }
            QTabBar::tab:selected {
                background: #3b82f6;
                color: white;
            }
        """)
        tabs.addTab(self._tab_merge(),    "🔗 Unisci")
        tabs.addTab(self._tab_split(),    "✂️ Dividi / Ruota")
        tabs.addTab(self._tab_optimize(), "🗜 Comprimi / Proteggi")
        tabs.addTab(self._tab_extract(),  "📄 Estrai")
        tabs.addTab(self._tab_ocr(),      "🔍 OCR")

        self.preview = PdfPreviewWidget()
        self.preview.setMinimumWidth(320)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(6)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(tabs)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([640, 440])

        outer.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(True)
        self.status.showMessage("Pronto")

    # ============================================================
    # TAB MERGE
    # ============================================================
    def _tab_merge(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        b_add = QPushButton("➕ Aggiungi PDF…")
        b_add.clicked.connect(self._add_files)
        b_clear = QPushButton("🗑 Svuota")
        b_clear.clicked.connect(self._clear_files)
        btns.addWidget(b_add)
        btns.addWidget(b_clear)
        btns.addStretch()
        layout.addLayout(btns)

        layout.addWidget(QLabel("Trascina le righe per riordinare:"))

        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setMinimumHeight(200)
        self.list_widget.currentItemChanged.connect(self._on_merge_selection)
        layout.addWidget(self.list_widget, 1)

        self.chk_bookmarks = QCheckBox("Aggiungi segnalibri per file")
        self.chk_bookmarks.setChecked(True)
        layout.addWidget(self.chk_bookmarks)

        # Selettore formato pagine
        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        size_row.addWidget(QLabel("Formato pagine:"))

        self.cmb_page_size = QComboBox()
        self.cmb_page_size.addItem("Auto (dal primo PDF)", "auto")
        self.cmb_page_size.addItem("A4 verticale",        "a4")
        self.cmb_page_size.addItem("A4 orizzontale",      "a4_landscape")
        self.cmb_page_size.addItem("Lettera verticale",   "letter")
        self.cmb_page_size.addItem("Lettera orizzontale", "letter_landscape")
        self.cmb_page_size.addItem("Non uniformare",      "none")
        size_row.addWidget(self.cmb_page_size, 1)
        layout.addLayout(size_row)

        b_merge = QPushButton("🔗 Unisci e salva…")
        b_merge.setMinimumHeight(36)
        b_merge.clicked.connect(self._do_merge)
        layout.addWidget(b_merge)

        return w

    def _on_merge_selection(self, current, _previous):
        if current is not None:
            path = current.data(Qt.UserRole)
            if path:
                self.preview.load_pdf(path)

    def _add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona PDF", "", "PDF (*.pdf)")
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                item = QListWidgetItem(f"{len(self.files)}. {Path(p).name}")
                item.setData(Qt.UserRole, p)
                self.list_widget.addItem(item)

        if paths and self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)

    def _clear_files(self):
        self.files.clear()
        self.list_widget.clear()

    def _do_merge(self):
        if self.list_widget.count() < 2:
            QMessageBox.warning(self, "Attenzione", "Servono almeno 2 PDF.")
            return
        order = [self.list_widget.item(i).data(Qt.UserRole)
                 for i in range(self.list_widget.count())]
        out, _ = QFileDialog.getSaveFileName(self, "Salva come", "unito.pdf", "PDF (*.pdf)")
        if not out:
            return
        
        size_choice = self.cmb_page_size.currentData()
        self._run(
            merger.merge_pdfs, 
            order, 
            out, 
            self.chk_bookmarks.isChecked(),
            size_choice
        )

    # ============================================================
    # TAB SPLIT / RUOTA
    # ============================================================
    def _tab_split(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        b_in = QPushButton("📂 Scegli PDF…")
        self.lbl_split_file = QLabel("Nessun file")
        b_in.clicked.connect(self._pick_split_file)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(b_in)
        row.addWidget(self.lbl_split_file, 1)
        layout.addLayout(row)

        g_split = QGroupBox("Dividi")
        g_split.setStyleSheet("QGroupBox { padding-top: 14px; margin-top: 6px; }")
        sl = QVBoxLayout(g_split)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.setSpacing(8)

        self.inp_ranges = QLineEdit()
        self.inp_ranges.setPlaceholderText("Es: 1-3, 5, 7-10  (vuoto = una pagina per file)")
        sl.addWidget(QLabel("Range pagine (1-based):"))
        sl.addWidget(self.inp_ranges)

        b_split = QPushButton("✂️ Dividi…")
        b_split.clicked.connect(self._do_split)
        sl.addWidget(b_split)
        layout.addWidget(g_split)

        g_rot = QGroupBox("Ruota")
        g_rot.setStyleSheet("QGroupBox { padding-top: 14px; margin-top: 6px; }")
        rl = QHBoxLayout(g_rot)
        rl.setContentsMargins(12, 12, 12, 12)
        rl.setSpacing(8)

        self.cmb_angle = QComboBox()
        self.cmb_angle.addItems(["0", "90", "180", "270"])
        self.cmb_angle.currentTextChanged.connect(self._on_angle_changed)

        b_rot = QPushButton("↻ Ruota…")
        b_rot.clicked.connect(self._do_rotate)

        rl.addWidget(QLabel("Angolo:"))
        rl.addWidget(self.cmb_angle)
        rl.addWidget(b_rot)
        rl.addStretch()
        layout.addWidget(g_rot)

        layout.addStretch()
        return w

    def _pick_split_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if p:
            self.split_file = p
            self.lbl_split_file.setText(Path(p).name)
            self.cmb_angle.blockSignals(True)
            self.cmb_angle.setCurrentText("0")
            self.cmb_angle.blockSignals(False)
            self.preview.load_pdf(p)

    def _on_angle_changed(self, text):
        try:
            angolo = int(text)
        except ValueError:
            angolo = 0
        self.preview.set_rotation(angolo)

    def _parse_ranges(self, s: str):
        if not s.strip():
            return None
        out = []
        for part in s.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-")
                out.append((int(a), int(b)))
            else:
                out.append((int(part), int(part)))
        return out

    def _do_split(self):
        if not self.split_file:
            QMessageBox.warning(self, "Attenzione", "Scegli un PDF.")
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Cartella output")
        if not out_dir:
            return
        ranges = self._parse_ranges(self.inp_ranges.text())
        self._run(merger.split_pdf, self.split_file, out_dir, ranges)

    def _do_rotate(self):
        if not self.split_file:
            QMessageBox.warning(self, "Attenzione", "Scegli un PDF.")
            return
        angle = int(self.cmb_angle.currentText())
        if angle == 0:
            QMessageBox.information(self, "Nessuna rotazione", "Seleziona 90, 180 o 270.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva come", "ruotato.pdf", "PDF (*.pdf)")
        if not out:
            return
        self._run(merger.rotate_pages, self.split_file, out, angle)

    # ============================================================
    # TAB COMPRIMI / PROTEGGI
    # ============================================================
    def _tab_optimize(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        b = QPushButton("📂 Scegli PDF…")
        self.lbl_opt = QLabel("Nessun file")
        b.clicked.connect(self._pick_opt_file)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(b)
        row.addWidget(self.lbl_opt, 1)
        layout.addLayout(row)

        b_comp = QPushButton("🗜 Comprimi…")
        b_comp.clicked.connect(self._do_compress)
        layout.addWidget(b_comp)

        g_pw = QGroupBox("Password")
        g_pw.setStyleSheet("QGroupBox { padding-top: 14px; margin-top: 6px; }")
        pl = QVBoxLayout(g_pw)
        pl.setContentsMargins(12, 12, 12, 12)
        pl.setSpacing(8)

        self.inp_pw = QLineEdit()
        self.inp_pw.setEchoMode(QLineEdit.Password)
        pl.addWidget(QLabel("Password:"))
        pl.addWidget(self.inp_pw)

        b_prot = QPushButton("🔒 Proteggi…")
        b_prot.clicked.connect(self._do_protect)
        pl.addWidget(b_prot)
        layout.addWidget(g_pw)

        g_wm = QGroupBox("Watermark")
        g_wm.setStyleSheet("QGroupBox { padding-top: 14px; margin-top: 6px; }")
        wl = QHBoxLayout(g_wm)
        wl.setContentsMargins(12, 12, 12, 12)
        wl.setSpacing(8)

        self.inp_wm = QLineEdit("BOZZA")
        b_wm = QPushButton("Aggiungi…")
        b_wm.clicked.connect(self._do_watermark)
        wl.addWidget(QLabel("Testo:"))
        wl.addWidget(self.inp_wm, 1)
        wl.addWidget(b_wm)
        layout.addWidget(g_wm)

        layout.addStretch()
        return w

    def _pick_opt_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if p:
            self.opt_file = p
            self.lbl_opt.setText(Path(p).name)
            self.preview.load_pdf(p)

    def _do_compress(self):
        if not self.opt_file:
            QMessageBox.warning(self, "Attenzione", "Scegli PDF.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva come", "compresso.pdf", "PDF (*.pdf)")
        if not out:
            return
        self._run(optimizer.compress_pdf, self.opt_file, out)

    def _do_protect(self):
        if not self.opt_file:
            QMessageBox.warning(self, "Attenzione", "Scegli PDF.")
            return
        if not self.inp_pw.text():
            QMessageBox.warning(self, "Attenzione", "Inserisci password.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva come", "protetto.pdf", "PDF (*.pdf)")
        if not out:
            return
        self._run(optimizer.protect_pdf, self.opt_file, out, self.inp_pw.text())

    def _do_watermark(self):
        if not self.opt_file:
            QMessageBox.warning(self, "Attenzione", "Scegli PDF.")
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva come", "watermark.pdf", "PDF (*.pdf)")
        if not out:
            return
        self._run(optimizer.add_watermark, self.opt_file, out, self.inp_wm.text())

    # ============================================================
    # TAB ESTRAI
    # ============================================================
    def _tab_extract(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        b = QPushButton("📂 Scegli PDF…")
        self.lbl_ext = QLabel("Nessun file")
        b.clicked.connect(self._pick_ext_file)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(b)
        row.addWidget(self.lbl_ext, 1)
        layout.addLayout(row)

        for label, slot in [
            ("📝 Estrai testo → .txt", self._do_extract_text),
            ("📊 Estrai tabelle → .csv", self._do_extract_tables),
            ("🖼 Estrai immagini → cartella", self._do_extract_images),
            ("🖨 Pagine → PNG", self._do_pdf_to_img),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(32)
            btn.clicked.connect(slot)
            layout.addWidget(btn)

        layout.addStretch()
        return w

    def _pick_ext_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if p:
            self.ext_file = p
            self.lbl_ext.setText(Path(p).name)
            self.preview.load_pdf(p)

    def _do_extract_text(self):
        if not self.ext_file:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva", "estratto.txt", "Testo (*.txt)")
        if not out:
            return
        pages = extractor.extract_text(self.ext_file)
        Path(out).write_text(
            "\n\n".join(f"=== Pagina {n} ===\n{t}" for n, t in pages.items()),
            encoding="utf-8",
        )
        QMessageBox.information(self, "Fatto", f"Salvato in {out}")

    def _do_extract_tables(self):
        if not self.ext_file:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva", "tabelle.csv", "CSV (*.csv)")
        if not out:
            return
        import csv
        tables = extractor.extract_tables(self.ext_file)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for t in tables:
                w.writerow([f"# Pagina {t['page']}"])
                for row in t["table"]:
                    w.writerow([c or "" for c in row])
                w.writerow([])
        QMessageBox.information(self, "Fatto", f"{len(tables)} tabelle salvate in {out}")

    def _do_extract_images(self):
        if not self.ext_file:
            return
        out = QFileDialog.getExistingDirectory(self, "Cartella output")
        if not out:
            return
        paths = extractor.extract_images(self.ext_file, out)
        QMessageBox.information(self, "Fatto", f"{len(paths)} immagini estratte.")

    def _do_pdf_to_img(self):
        if not self.ext_file:
            return
        out = QFileDialog.getExistingDirectory(self, "Cartella output")
        if not out:
            return
        self._run(extractor.pdf_to_images, self.ext_file, out)

    # ============================================================
    # TAB OCR
    # ============================================================
    def _tab_ocr(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        b = QPushButton("📂 Scegli PDF scansionato…")
        self.lbl_ocr = QLabel("Nessun file")
        b.clicked.connect(self._pick_ocr_file)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(b)
        row.addWidget(self.lbl_ocr, 1)
        layout.addLayout(row)

        self.inp_lang = QLineEdit("ita+eng")
        layout.addWidget(QLabel("Lingue Tesseract:"))
        layout.addWidget(self.inp_lang)

        b_ocr = QPushButton("🔍 Esegui OCR…")
        b_ocr.setMinimumHeight(36)
        b_ocr.clicked.connect(self._do_ocr)
        layout.addWidget(b_ocr)

        layout.addStretch()
        return w

    def _pick_ocr_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "PDF", "", "PDF (*.pdf)")
        if p:
            self.ocr_file = p
            self.lbl_ocr.setText(Path(p).name)
            self.preview.load_pdf(p)

    def _do_ocr(self):
        if not self.ocr_file:
            return
        out, _ = QFileDialog.getSaveFileName(self, "Salva come", "ocr.pdf", "PDF (*.pdf)")
        if not out:
            return
        self._run(ocr.ocr_pdf, self.ocr_file, out, self.inp_lang.text())

    # ============================================================
    # HELPER
    # ============================================================
    def _run(self, fn, *args, **kwargs):
        self.status.showMessage("Elaborazione in corso…")
        self.worker = Worker(fn, *args, **kwargs)
        self.worker.done.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_done(self, result):
        self.status.showMessage("Completato")

        if isinstance(result, dict):
            msg = "\n".join(f"{k}: {v}" for k, v in result.items())
        elif isinstance(result, list):
            msg = f"{len(result)} file generati."
        else:
            msg = str(result)
        QMessageBox.information(self, "Fatto", msg)

        # Se l'output è un PDF, mostralo in anteprima
        out_path = None
        if isinstance(result, dict):
            out_path = result.get("output")
        elif isinstance(result, str):
            out_path = result
        elif isinstance(result, list) and result:
            out_path = result[0]

        if out_path and Path(out_path).suffix.lower() == ".pdf" and Path(out_path).exists():
            self.preview.load_pdf(out_path)
            self.status.showMessage(f"Completato — anteprima: {Path(out_path).name}")

    def _on_error(self, err):
        self.status.showMessage("Errore")
        QMessageBox.critical(self, "Errore", err)