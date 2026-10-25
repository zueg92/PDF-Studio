"""Widget anteprima PDF con navigazione, zoom e rotazione live, basato su PyMuPDF."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QSpinBox, QComboBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QTransform
import fitz


class PdfPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._current_page = 0
        self._zoom = 1.5
        self._cache = {}
        self._rotation = 0

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._render)

        self._build_ui()

    # ---------- costruzione UI ----------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_next = QPushButton("▶")
        self.spin_page = QSpinBox()
        self.spin_page.setRange(0, 0)
        self.lbl_total = QLabel("/ 0")
        self.cmb_fit = QComboBox()
        self.cmb_fit.addItems(["Adatta larghezza", "Adatta pagina", "Manuale"])
        self.cmb_fit.setCurrentIndex(0)
        self.btn_zoom_out = QPushButton("−")
        self.btn_zoom_in = QPushButton("+")
        self.lbl_zoom = QLabel("—")

        for w in (self.btn_prev, self.spin_page, self.lbl_total, self.btn_next):
            bar.addWidget(w)
        bar.addStretch()
        bar.addWidget(self.cmb_fit)
        bar.addWidget(self.btn_zoom_out)
        bar.addWidget(self.lbl_zoom)
        bar.addWidget(self.btn_zoom_in)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet("background: #2b2b2b;")

        self.image_label = QLabel("Nessun PDF caricato")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("color: #888; padding: 20px;")
        self.scroll.setWidget(self.image_label)

        layout.addLayout(bar)
        layout.addWidget(self.scroll, 1)

        self.btn_prev.clicked.connect(lambda: self.go_to_page(self._current_page - 1))
        self.btn_next.clicked.connect(lambda: self.go_to_page(self._current_page + 1))
        self.spin_page.valueChanged.connect(lambda v: self.go_to_page(v - 1))
        self.btn_zoom_in.clicked.connect(lambda: self._set_zoom(self._zoom + 0.25))
        self.btn_zoom_out.clicked.connect(lambda: self._set_zoom(self._zoom - 0.25))
        self.cmb_fit.currentIndexChanged.connect(lambda _: self._render())

    # ---------- API pubblica ----------
    def load_pdf(self, path):
        try:
            if self._doc:
                self._doc.close()
            self._doc = fitz.open(str(path))
            self._cache.clear()
            self._current_page = 0
            self._rotation = 0
            n = self._doc.page_count
            self.spin_page.blockSignals(True)
            self.spin_page.setRange(1, n)
            self.spin_page.setValue(1)
            self.spin_page.blockSignals(False)
            self.lbl_total.setText(f"/ {n}")
            self._render()
        except Exception as e:
            self.clear()
            self.image_label.setText(f"Errore anteprima: {e}")

    def go_to_page(self, idx):
        if not self._doc:
            return
        idx = max(0, min(idx, self._doc.page_count - 1))
        if idx != self._current_page:
            self._current_page = idx
            self.spin_page.blockSignals(True)
            self.spin_page.setValue(idx + 1)
            self.spin_page.blockSignals(False)
            self._render()

    def set_rotation(self, angle: int):
        """Imposta la rotazione visiva (0, 90, 180, 270) e aggiorna l'anteprima."""
        angle = angle % 360
        if angle not in (0, 90, 180, 270):
            angle = 0
        if self._rotation != angle:
            self._rotation = angle
            self._cache.clear()  # forza il re-render
            self._render()

    def clear(self):
        if self._doc:
            self._doc.close()
            self._doc = None
        self._cache.clear()
        self._rotation = 0
        self.image_label.clear()
        self.image_label.setText("Nessun PDF caricato")
        self.spin_page.blockSignals(True)
        self.spin_page.setRange(0, 0)
        self.spin_page.blockSignals(False)
        self.lbl_total.setText("/ 0")
        self.lbl_zoom.setText("—")

    # ---------- interni ----------
    def _set_zoom(self, z):
        self._zoom = max(0.25, min(5.0, z))
        if self.cmb_fit.currentIndex() != 2:
            self.cmb_fit.blockSignals(True)
            self.cmb_fit.setCurrentIndex(2)
            self.cmb_fit.blockSignals(False)
        self._render()

    def _render(self):
        if not self._doc:
            return

        page = self._doc[self._current_page]
        dpr = self.devicePixelRatioF() or 1.0
        mode = self.cmb_fit.currentIndex()
        zoom = self._zoom

        vw = self.scroll.viewport().width() - 20
        vh = self.scroll.viewport().height() - 20

        # Se la pagina è ruotata di 90/270, per il fit devo scambiare larghezza/altezza
        page_w = page.rect.width
        page_h = page.rect.height
        if self._rotation in (90, 270):
            page_w, page_h = page_h, page_w

        if mode == 0 and page_w:
            zoom = vw / page_w
        elif mode == 1 and page_w and page_h:
            zoom = min(vw / page_w, vh / page_h)

        key = (self._current_page, round(zoom, 3), round(dpr, 2), self._rotation)
        if key not in self._cache:
            mat = fitz.Matrix(zoom * dpr, zoom * dpr)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            if len(self._cache) > 30:
                self._cache.clear()
            self._cache[key] = pix
        pix = self._cache[key]

        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pm = QPixmap.fromImage(img)

        # Applica la rotazione visiva
        if self._rotation:
            pm = pm.transformed(QTransform().rotate(self._rotation), Qt.SmoothTransformation)

        pm.setDevicePixelRatio(dpr)
        self.image_label.setPixmap(pm)
        self.image_label.setFixedSize(int(pm.width() / dpr), int(pm.height() / dpr))
        self.lbl_zoom.setText(f"{int(zoom * 100)}%")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._doc:
            self._resize_timer.start(120)

    def closeEvent(self, e):
        self.clear()
        super().closeEvent(e)