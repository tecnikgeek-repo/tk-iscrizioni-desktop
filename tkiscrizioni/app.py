"""Finestra principale di tk-iscrizioni: caselle e filtri a sinistra, servizi al centro, dettaglio a destra."""
import csv
import html
import json
import os
import sys
import time
import urllib.parse

from PySide6.QtCore import (
    QAbstractTableModel, QModelIndex, QPointF, QRectF, QSize, QSortFilterProxyModel, Qt, QThread, QTimer, QUrl, Signal,
)
from PySide6.QtGui import (
    QBrush, QColor, QDesktopServices, QFont, QIcon, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QFrame, QGraphicsDropShadowEffect, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLayout, QLineEdit, QMainWindow, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QStackedWidget, QStyle, QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
)

from tkiscrizioni import (
    APP_TITLE, AUTHOR, AUTHOR_URL, PRIVACY_URL, TERMS_URL, URL_SORGENTE, VERSION, classify, disiscrizione, mailscan,
    msoauth, pro, providers, updater, vault,
)
from tkiscrizioni.store import Store
from tkiscrizioni.tk_licenza_qt import LicenzeDialog, dentro_lo_schermo
from tkiscrizioni.util import (
    IS_WIN, Settings, cartella_licenze, create_desktop_shortcut, data_dir, ensure_folder_shortcut, export_dir,
    human_size, is_installed, log_dir,
)

NAVY = "#0f172a"
NAVY_2 = "#1e293b"
NAVY_3 = "#334155"
ACCENT = "#7c3aed"
ACCENT_D = "#6d28d9"
ACCENT_L = "#ede9fe"
ACCENT_2 = "#8b5cf6"
GRAY_50 = "#f8fafc"
GRAY_100 = "#f1f5f9"
GRAY_200 = "#e2e8f0"
GRAY_300 = "#cbd5e1"
GRAY_400 = "#94a3b8"
GRAY_500 = "#64748b"
GREEN = "#16a34a"
RED = "#dc2626"

CAT_COLORS = {"account": ACCENT, "social": "#2563eb", "acquisti": "#059669", "newsletter": "#d97706",
              "altro": GRAY_500, "persona": GRAY_400}
STATUS = {"": ("", ""), "tenere": ("Da tenere", GREEN), "cancellare": ("Da cancellare", RED),
          # «disiscritto» (chiave interna, resta così nell'archivio): la richiesta è partita, non è una conferma
          "fatto": ("Account cancellato", GRAY_500), "disiscritto": ("Richiesta inviata", GRAY_500)}

STYLE = f"""
QMainWindow {{ background:#e9edf4; }}
QWidget {{ font-size:13px; color:{NAVY}; }}
QWidget#canvas {{ background:transparent; }}
QScrollArea {{ background:transparent; border:0; }}
QFrame#header {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {NAVY},stop:1 #1b2a4a); border-radius:16px; }}
QFrame#card {{ background:#ffffff; border-radius:16px; }}
QFrame#tile {{ background:#ffffff; border-radius:14px; }}
QLabel#brand {{ color:#fff; font-size:19px; font-weight:800; }}
QLabel#ver {{ color:{GRAY_300}; font-size:11px; }}
QLabel#cardtitle {{ color:{NAVY}; font-size:12px; font-weight:800; letter-spacing:1.5px; }}
QLabel#hint {{ color:{GRAY_500}; font-size:12px; }}
QLabel#field {{ color:{GRAY_500}; font-size:11px; font-weight:700; }}
QLabel#icobox {{ background:{ACCENT_L}; border-radius:10px; }}
QLabel#tilenum {{ font-size:26px; font-weight:800; color:{NAVY}; }}
QLabel#tilelab {{ font-size:11px; font-weight:700; color:{GRAY_500}; letter-spacing:.5px; }}
QLabel#bigname {{ font-size:22px; font-weight:800; color:{NAVY}; }}
QPushButton {{ background:#fff; border:1px solid {GRAY_300}; border-radius:10px; padding:0 14px; min-height:36px; color:{NAVY}; font-weight:600; }}
QPushButton:hover {{ background:{GRAY_100}; border-color:{GRAY_400}; }}
QPushButton:disabled {{ color:{GRAY_300}; background:{GRAY_50}; }}
QPushButton#ghost {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14); color:#fff; }}
QPushButton#ghost:hover {{ background:rgba(255,255,255,.18); }}
QPushButton#accent {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {ACCENT_2},stop:1 {ACCENT_D}); border:0; color:#fff; font-weight:800; padding:0 18px; }}
QPushButton#accent:hover {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #a78bfa,stop:1 {ACCENT}); }}
QPushButton#accent:disabled {{ background:{GRAY_300}; color:#fff; }}
QPushButton#mini {{ min-width:32px; max-width:32px; min-height:32px; padding:0; border-radius:9px; }}
QPushButton#chip {{ background:{GRAY_100}; border:1px solid {GRAY_200}; border-radius:15px; min-height:30px; padding:0 12px; color:{NAVY_3}; }}
QPushButton#chip:hover {{ background:{GRAY_200}; }}
QPushButton#chip:checked {{ background:{NAVY}; border-color:{NAVY}; color:#fff; }}
QPushButton#seg {{ background:#fff; border:1px solid {GRAY_200}; border-radius:10px; min-height:34px; padding:0 8px; font-size:12px; }}
QPushButton#seg:checked {{ background:{NAVY}; border-color:{NAVY}; color:#fff; }}
QPushButton#link {{ background:transparent; border:0; color:{ACCENT_D}; font-weight:700; padding:0; min-height:22px; text-align:left; }}
QPushButton#link:hover {{ text-decoration:underline; }}
QFrame#acct {{ background:{GRAY_50}; border:1px solid {GRAY_200}; border-radius:12px; }}
QLineEdit {{ background:{GRAY_50}; border:1px solid {GRAY_200}; border-radius:10px; padding:0 12px; min-height:36px; selection-background-color:{ACCENT}; }}
QLineEdit:focus {{ background:#fff; border:1px solid {ACCENT}; }}
QCheckBox {{ color:{NAVY_3}; spacing:8px; }}
QTableView {{ background:#fff; border:0; gridline-color:transparent; selection-background-color:{ACCENT_L}; selection-color:{NAVY}; outline:0; alternate-background-color:{GRAY_50}; }}
QTableView::item {{ padding:0 8px; border-bottom:1px solid {GRAY_100}; }}
QHeaderView::section {{ background:{NAVY}; border:0; padding:8px; color:#fff; font-size:11px; font-weight:800; }}
QHeaderView::section:first {{ border-top-left-radius:10px; }}
QHeaderView::section:last {{ border-top-right-radius:10px; }}
QScrollBar:vertical {{ background:transparent; width:12px; margin:2px; }}
QScrollBar::handle:vertical {{ background:{GRAY_300}; border-radius:5px; min-height:30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; width:0; }}
QScrollBar:horizontal {{ height:0; }}
QStatusBar {{ background:transparent; color:{GRAY_500}; }}
QProgressBar#scan {{ background:{GRAY_200}; border:0; border-radius:4px; max-height:8px; }}
QProgressBar#scan::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {NAVY},stop:1 {ACCENT}); border-radius:4px; }}
QToolTip {{ background:{NAVY}; color:#fff; border:0; padding:5px 8px; }}
QDialog#tk {{ background:transparent; }}
QFrame#tkcard {{ background:{NAVY}; border-radius:20px; border:1px solid {NAVY_3}; }}
QDialog#tk QLabel {{ color:#fff; }}
QDialog#tk QLabel#asub {{ color:{GRAY_300}; }}
QDialog#tk QLabel#err {{ color:#fca5a5; font-weight:600; }}
QDialog#tk QLabel#afield {{ color:{GRAY_300}; font-size:11px; font-weight:700; }}
QDialog#tk QFrame#acard {{ background:{NAVY_2}; border-radius:14px; }}
QDialog#tk QLabel#atitle {{ color:#c4b5fd; font-size:11px; font-weight:800; letter-spacing:1.5px; }}
QDialog#tk QLineEdit, QDialog#tk QComboBox {{ background:{NAVY_2}; border:1px solid {NAVY_3}; color:#fff; border-radius:10px; padding:0 12px; min-height:38px; selection-background-color:{ACCENT}; }}
QDialog#tk QLineEdit:focus, QDialog#tk QComboBox:focus {{ border-color:{ACCENT_2}; }}
QDialog#tk QComboBox::drop-down {{ border:0; width:28px; }}
QDialog#tk QComboBox QAbstractItemView {{ background:{NAVY_2}; color:#fff; selection-background-color:{ACCENT}; border:1px solid {NAVY_3}; }}
QDialog#tk QProgressBar {{ background:{NAVY_2}; border:0; border-radius:5px; }}
QDialog#tk QProgressBar::chunk {{ background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {ACCENT},stop:1 #a78bfa); border-radius:5px; }}
QDialog#tk QPushButton#link {{ color:#c4b5fd; }}
"""


# ---------------------------------------------------------------- icone e grafica
def ic(name, color="#ffffff", size=20):
    """Icone a tratto disegnate a mano (niente emoji)."""
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size * 2 / 24, size * 2 / 24)
    pen = QPen(QColor(color), 2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    L = lambda *a: p.drawLine(QPointF(a[0], a[1]), QPointF(a[2], a[3]))
    R = lambda x, y, w, h, r=2: p.drawRoundedRect(QRectF(x, y, w, h), r, r)

    def poly(*pts):
        path = QPainterPath(QPointF(*pts[0]))
        for pt in pts[1:]:
            path.lineTo(QPointF(*pt))
        p.drawPath(path)

    if name == "plus":
        L(12, 5, 12, 19); L(5, 12, 19, 12)
    elif name == "mail":
        R(3, 5, 18, 14, 3); poly((4, 7), (12, 13), (20, 7))
    elif name == "refresh":
        p.drawArc(QRectF(4, 4, 16, 16), 40 * 16, 270 * 16); poly((17, 3), (19, 8), (14, 9))
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 9, 9); L(12, 11, 12, 17); L(12, 7.5, 12, 7.6)
    elif name == "trash":
        L(5, 7, 19, 7); R(7, 7, 10, 13); poly((9, 7), (9, 4), (15, 4), (15, 7)); L(10, 11, 10, 17); L(14, 11, 14, 17)
    elif name == "export":
        L(12, 4, 12, 15); poly((7, 10), (12, 15), (17, 10)); poly((4, 15), (4, 20), (20, 20), (20, 15))
    elif name == "heart":
        path = QPainterPath(QPointF(12, 20))
        path.cubicTo(QPointF(2, 13), QPointF(3, 4), QPointF(12, 8))
        path.cubicTo(QPointF(21, 4), QPointF(22, 13), QPointF(12, 20))
        p.drawPath(path)
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5); L(15.5, 15.5, 20, 20)
    elif name == "globe":
        p.drawEllipse(QPointF(12, 12), 9, 9); L(3, 12, 21, 12); p.drawEllipse(QPointF(12, 12), 4, 9)
    elif name == "unsub":
        R(3, 5, 18, 14, 3); poly((4, 7), (12, 13), (20, 7)); L(15, 3, 21, 9); L(21, 3, 15, 9)
    elif name == "user-x":
        p.drawEllipse(QPointF(9, 8), 4, 4); poly((2, 20), (3, 15), (9, 13), (14, 15), (15, 18)); L(16, 9, 21, 14); L(21, 9, 16, 14)
    elif name == "alert":
        poly((12, 3), (22, 20), (2, 20), (12, 3)); L(12, 10, 12, 14); L(12, 17, 12, 17.1)
    elif name == "help":
        p.drawEllipse(QPointF(12, 12), 9, 9); L(12, 17, 12, 17.1); p.drawArc(QRectF(9, 7, 6, 6), 120 * 16, -250 * 16)
    elif name == "lock":
        R(5, 11, 14, 10, 3); p.drawArc(QRectF(8, 4, 8, 12), 0, 180 * 16); L(8, 10, 8, 11); L(16, 10, 16, 11)
    elif name == "check":
        poly((5, 12), (10, 17), (19, 7))
    elif name == "stop":
        R(6, 6, 12, 12, 2)
    elif name == "eye":
        path = QPainterPath(QPointF(2, 12))
        path.quadTo(QPointF(12, 2), QPointF(22, 12)); path.quadTo(QPointF(12, 22), QPointF(2, 12))
        p.drawPath(path); p.drawEllipse(QPointF(12, 12), 3, 3)
    elif name == "doc":
        poly((6, 3), (14, 3), (19, 8), (19, 21), (6, 21), (6, 3)); poly((14, 3), (14, 8), (19, 8))
    elif name == "microsoft":
        p.setPen(Qt.PenStyle.NoPen)
        for (x, y, c) in ((3, 3, "#f25022"), (12.5, 3, "#7fba00"), (3, 12.5, "#00a4ef"), (12.5, 12.5, "#ffb900")):
            p.setBrush(QColor(c)); p.drawRect(QRectF(x, y, 8.5, 8.5))
    p.end()
    pm.setDevicePixelRatio(2)
    return QIcon(pm)


def render_icon(size=64):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor("#1e293b"))
    g.setColorAt(1, QColor(NAVY))
    p.setBrush(QBrush(g))
    p.drawRoundedRect(0, 0, size, size, size * 0.24, size * 0.24)
    # busta
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(QRectF(size * .15, size * .26, size * .62, size * .44), size * .06, size * .06)
    pen = QPen(QColor(NAVY), max(1.5, size * .045))
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    path = QPainterPath(QPointF(size * .19, size * .31))
    path.lineTo(QPointF(size * .46, size * .51))
    path.lineTo(QPointF(size * .73, size * .31))
    p.drawPath(path)
    # bollino viola con la spunta
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(ACCENT_2))
    p.drawEllipse(QPointF(size * .74, size * .72), size * .17, size * .17)
    pen = QPen(QColor("#ffffff"), max(1.5, size * .05))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    path = QPainterPath(QPointF(size * .66, size * .72))
    path.lineTo(QPointF(size * .72, size * .78))
    path.lineTo(QPointF(size * .83, size * .66))
    p.drawPath(path)
    p.end()
    return QPixmap.fromImage(img)


def shadow(widget, blur=30, dy=6, alpha=45):
    e = QGraphicsDropShadowEffect(widget)
    e.setBlurRadius(blur)
    e.setOffset(0, dy)
    e.setColor(QColor(15, 23, 42, alpha))
    widget.setGraphicsEffect(e)


def text_btn(icon_name, text, fn, color="#ffffff", name="ghost", tip=""):
    b = QPushButton(text)
    b.setObjectName(name)
    if icon_name:
        b.setIcon(ic(icon_name, color, 18))
        b.setIconSize(QSize(18, 18))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tip:
        b.setToolTip(tip)
    b.clicked.connect(fn)
    return b


def mini_btn(icon_name, tip, fn, color=NAVY):
    b = QPushButton()
    b.setObjectName("mini")
    b.setIcon(ic(icon_name, color, 16))
    b.setIconSize(QSize(16, 16))
    b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.clicked.connect(fn)
    return b


class Card(QFrame):
    def __init__(self, icon_name, title):
        super().__init__()
        self.setObjectName("card")
        shadow(self, 26, 5, 38)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(18, 16, 18, 18)
        self.lay.setSpacing(10)
        head = QHBoxLayout()
        box = QLabel(objectName="icobox")
        box.setFixedSize(32, 32)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.setPixmap(ic(icon_name, ACCENT, 17).pixmap(17, 17))
        head.addWidget(box)
        head.addSpacing(4)
        head.addWidget(QLabel(title.upper(), objectName="cardtitle"))
        head.addStretch(1)
        self.head = head
        self.lay.addLayout(head)


def fmt_date(ts, with_time=False):
    if not ts:
        return "—"
    return time.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y", time.localtime(ts))


def open_url(url):
    QDesktopServices.openUrl(QUrl(url))


def cella_csv(valore):
    """Testo per una cella del CSV: con «'» davanti se Excel lo leggerebbe come formula
    (nomi e oggetti arrivano dalle email, li sceglie chi le spedisce)."""
    if not isinstance(valore, str):
        return valore
    return "'" + valore if valore[:1] in ("=", "+", "-", "@", "\t", "\r") else valore


# ---------------------------------------------------------------- finestre nel nostro stile
class TkDialog(QDialog):
    """Scheda navy arrotondata con ombra, senza la barra di sistema."""

    def __init__(self, parent, width=460):
        super().__init__(parent)
        self.setObjectName("tk")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 22, 28, 34)
        # la finestra segue sempre il contenuto (testi che vanno a capo, campi che compaiono)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.card = QFrame(objectName="tkcard")
        self.card.setFixedWidth(width)
        shadow(self.card, 44, 12, 110)
        outer.addWidget(self.card)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(26, 24, 26, 24)
        self.body.setSpacing(12)
        self._drag = None

    def head(self, icon_pixmap, title, sub=""):
        row = QHBoxLayout()
        row.setSpacing(14)
        ico = QLabel()
        ico.setPixmap(icon_pixmap)
        ico.setAlignment(Qt.AlignmentFlag.AlignTop)
        row.addWidget(ico)
        col = QVBoxLayout()
        col.setSpacing(3)
        t = QLabel(title)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:20px; font-weight:800; color:#ffffff;")
        col.addWidget(t)
        if sub:
            s = QLabel(sub)
            s.setObjectName("asub")
            s.setWordWrap(True)
            col.addWidget(s)
        row.addLayout(col, 1)
        self.body.addLayout(row)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None


def _kind_icon(kind):
    names = {"info": ("info", "#7dd3fc"), "warn": ("alert", "#fbbf24"), "ask": ("help", "#c4b5fd"),
             "ok": ("check", "#86efac")}
    name, color = names[kind]
    box = QPixmap(52, 52)
    box.fill(Qt.GlobalColor.transparent)
    p = QPainter(box)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 22))
    p.drawRoundedRect(0, 0, 52, 52, 16, 16)
    p.drawPixmap(10, 10, ic(name, color, 32).pixmap(32, 32))
    p.end()
    return box


def tk_choice(parent, title, text, buttons, kind="ask", sub=""):
    """Domanda con più pulsanti [(testo, 'accent'|'ghost')]. Ritorna l'indice scelto (-1 se chiusa)."""
    dlg = TkDialog(parent, 440)
    dlg.head(_kind_icon(kind), title, sub)
    if text:
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setTextFormat(Qt.TextFormat.PlainText)
        lab.setStyleSheet("font-size:14px; color:#e2e8f0;")
        dlg.body.addWidget(lab)
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addStretch(1)
    result = {"i": -1}
    for i, (label, style) in enumerate(buttons):
        b = QPushButton(label)
        b.setObjectName(style)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(lambda _=False, k=i: (result.__setitem__("i", k), dlg.accept()))
        if style == "accent":
            b.setDefault(True)
        row.addWidget(b)
    dlg.body.addLayout(row)
    dlg.exec()
    return result["i"]


def tk_info(parent, title, text, kind="info"):
    tk_choice(parent, title, text, [("OK", "accent")], kind)


def tk_warn(parent, title, text):
    tk_choice(parent, title, text, [("OK", "accent")], "warn")


class UpdateDialog(TkDialog):
    def __init__(self, parent, manifest):
        super().__init__(parent, 460)
        self.choice = "later"
        self.head(render_icon(56), f"È disponibile {APP_TITLE} {manifest['version']}",
                  f"Stai usando la versione {VERSION}" +
                  (f" · pubblicata il {manifest['date']}" if manifest.get("date") else ""))
        notes = manifest.get("notes") or []
        if isinstance(notes, str):
            notes = [notes]
        if notes:
            card = QFrame(objectName="acard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(4)
            cl.addWidget(QLabel("NOVITÀ", objectName="atitle"))
            for n in notes:
                lab = QLabel("•  " + str(n))
                lab.setWordWrap(True)
                lab.setStyleSheet("font-size:13px; font-weight:600;")
                cl.addWidget(lab)
            self.body.addWidget(card)
        row = QHBoxLayout()
        row.setSpacing(8)
        for label, value in (("Salta questa versione", "skip"), ("Più tardi", "later")):
            b = QPushButton(label)
            b.setObjectName("ghost")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, v=value: self._done(v))
            row.addWidget(b)
        row.addStretch(1)
        go = text_btn("refresh", "Aggiorna ora", lambda: self._done("go"), "#fff", "accent")
        go.setDefault(True)
        row.addWidget(go)
        self.body.addLayout(row)

    def _done(self, value):
        self.choice = value
        self.accept()


class TkProgress(TkDialog):
    canceled = Signal()

    def __init__(self, parent, title, sub, cancelable=False):
        super().__init__(parent, 420)
        self.head(render_icon(56), title, sub)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setRange(0, 0)
        self.body.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("asub")
        self.body.addWidget(self.status)
        if cancelable:
            row = QHBoxLayout()
            row.addStretch(1)
            b = QPushButton("Annulla")
            b.setObjectName("ghost")
            b.clicked.connect(lambda: (self.canceled.emit(), self.close()))
            row.addWidget(b)
            self.body.addLayout(row)

    def set_progress(self, done, total, text=""):
        if total > 0:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(done * 1000 / total))
        self.status.setText(text)

    def keyPressEvent(self, e):
        if e.key() != Qt.Key.Key_Escape:
            super().keyPressEvent(e)


def _info_card(title, body):
    card = QFrame(objectName="acard")
    cl = QVBoxLayout(card)
    cl.setContentsMargins(16, 12, 16, 12)
    cl.setSpacing(3)
    cl.addWidget(QLabel(title, objectName="atitle"))
    v = QLabel(body)
    v.setWordWrap(True)
    v.setStyleSheet("font-size:13px; font-weight:600;")
    cl.addWidget(v)
    return card


# Benvenuto del primo avvio: la finestra comune (tk_licenza_qt.benvenuto) con queste righe in più.
# Prima della 1.1.0 c'era una finestra di benvenuto del programma: ora è una sola.
BENVENUTO_RIGHE = (
    "<b>Legge solo le intestazioni</b> (mittente, oggetto, data, link di disiscrizione), in sola lettura: "
    "nessuna email viene aperta, segnata come letta, spostata o cancellata.",
    "<b>Sul computer</b> restano l'archivio di mittenti, oggetti e date delle email lette (archivio.db, nella "
    "cartella dei dati) e le password delle caselle, cifrate.",
    "<b>In rete:</b> il tuo fornitore di posta; pietrodefilippis.it per aggiornamenti, configurazione "
    "dell'accesso a Outlook e statistiche (solo col sì qui sotto); i siti dei mittenti solo quando premi "
    "«Disiscriviti». Email e password non passano da altri server.",
)


class AboutDialog(TkDialog):
    def __init__(self, win):
        super().__init__(win, 460)
        self.check = False
        top = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(render_icon(72))
        top.addWidget(icon)
        top.addSpacing(10)
        col = QVBoxLayout()
        t = QLabel(APP_TITLE)
        t.setStyleSheet("font-size:24px; font-weight:800; color:#fff;")
        col.addWidget(t)
        s = QLabel("A cosa sei iscritto con la tua email:\nservizi, account, newsletter e acquisti.")
        s.setObjectName("asub")
        col.addWidget(s)
        top.addLayout(col, 1)
        self.body.addLayout(top)
        for title, body in (("VERSIONE", f"{VERSION} · Software libero · AGPL-3.0"),
                            ("SVILUPPATORE", f"{AUTHOR} · {AUTHOR_URL.split('//')[1]}"),
                            ("I TUOI DATI", html.escape(data_dir()))):
            self.body.addWidget(_info_card(title, body))
        stat = pro.casella_statistiche()
        stat.setStyleSheet("QCheckBox { color:#ffffff; }")
        self.body.addWidget(stat)
        self.body.addWidget(text_btn("refresh", "Controlla aggiornamenti", self._check, "#fff", "accent"))
        self.body.addWidget(text_btn("doc", "Licenze e codice sorgente", self._licenze,
                                     tip="Licenza AGPL-3.0, componenti inclusi e link al codice sorgente"))
        row = QHBoxLayout()
        row.setSpacing(8)
        caffe = pro.pulsante_caffe("ghost")  # ambra, uguale in tutti i software; None a chi ha già donato
        if caffe is not None:
            row.addWidget(caffe, 1)
        if IS_WIN:
            row.addWidget(text_btn("doc", "Icona sul Desktop", self._shortcut), 1)
        row.addWidget(text_btn("", "Chiudi", self.accept), 1)
        self.body.addLayout(row)
        links = QHBoxLayout()
        links.addStretch(1)
        for label, url in (("Termini e condizioni", TERMS_URL), ("Privacy", PRIVACY_URL),
                           ("Contatti", AUTHOR_URL + "/contatti/")):
            b = QPushButton(label)
            b.setObjectName("link")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, u=url: open_url(u))
            links.addWidget(b)
        links.addStretch(1)
        self.body.addLayout(links)

    def _shortcut(self):
        try:
            path = create_desktop_shortcut()
        except Exception as exc:
            tk_warn(self.parent(), APP_TITLE, f"Non riesco a creare l'icona sul Desktop:\n{exc}")
            return
        tk_info(self.parent(), APP_TITLE, f"Icona creata sul Desktop:\n{path}", "ok")

    def _check(self):
        self.check = True
        self.accept()

    def _licenze(self):
        LicenzeDialog(APP_TITLE, VERSION, URL_SORGENTE, cartella_licenze(), self).exec()


# ---------------------------------------------------------------- lavori in sottofondo
class Worker(QThread):
    """Esegue fn() in un thread: done(risultato) oppure failed(messaggio)."""
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)


class DownloadThread(QThread):
    progress = Signal(float, float)
    ok = Signal(str)
    failed = Signal(str)

    def __init__(self, url, dest, sha256, parent=None):
        super().__init__(parent)
        self.url, self.dest, self.sha256 = url, dest, sha256
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            updater.download(self.url, self.dest, self.sha256,
                             lambda d, t: self.progress.emit(float(d), float(t)), lambda: self._cancel)
            self.ok.emit(self.dest)
        except InterruptedError:
            self.failed.emit("")
        except Exception as exc:
            self.failed.emit(str(exc))


def account_secret(acc):
    """Password, oppure access token Microsoft aggiornato. Solleva se mancano le credenziali."""
    secret = vault.get_secret(acc["email"])
    if not secret:
        raise PermissionError("credenziali non trovate su questo computer: togli la casella e aggiungila di nuovo")
    if acc["auth"] != "oauth_ms":
        return secret
    tok = json.loads(secret)
    if time.time() < tok.get("obtained", 0) + int(tok.get("expires_in", 0)) - 120:
        return tok["access_token"]
    cfg = msoauth.config()
    tok = msoauth.refresh(cfg["client_id"] or tok.get("client_id", ""), tok["refresh_token"], cfg["tenant"])
    tok["client_id"] = cfg["client_id"]
    vault.set_secret(acc["email"], json.dumps(tok))
    return tok["access_token"]


class ScanThread(QThread):
    progress = Signal(str, float)
    finished_all = Signal(list)

    def __init__(self, store, accounts, parent=None):
        super().__init__(parent)
        self.store = store
        self.accounts = accounts
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        report = []
        n = len(self.accounts)
        for i, acc in enumerate(self.accounts):
            if self._cancel:
                break
            self.progress.emit(f"{acc['email']}: collegamento…", i / n)
            try:
                im = mailscan.connect(acc["host"], acc["port"], acc["email"], account_secret(acc), acc["auth"])
                try:
                    new = mailscan.scan_account(
                        im, self.store, acc["id"],
                        lambda text, fd, ft: self.progress.emit(f"{acc['email']} · {text}", (i + fd / max(ft, 1)) / n),
                        lambda: self._cancel)
                finally:
                    try:
                        im.logout()
                    except Exception:
                        pass
                self.store.set_scan(acc["id"], time.time(), "")
                report.append((acc["email"], True, new))
            except InterruptedError:
                report.append((acc["email"], None, 0))
                break
            except mailscan.AuthError as e:
                msg = "accesso rifiutato: " + str(e)
                self.store.set_scan(acc["id"], acc.get("last_scan") or 0, msg)
                report.append((acc["email"], False, msg))
            except Exception as e:
                msg = str(e) or e.__class__.__name__
                self.store.set_scan(acc["id"], acc.get("last_scan") or 0, msg)
                report.append((acc["email"], False, msg))
        self.finished_all.emit(report)


# ---------------------------------------------------------------- aggiungere una casella
class AccountDialog(TkDialog):
    def __init__(self, parent, store):
        super().__init__(parent, 480)
        self.store = store
        self.tokens = None
        self.worker = None
        self.head(_kind_icon("info"), "Aggiungi una casella",
                  "Le credenziali restano cifrate su questo computer.")
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.addWidget(QLabel("INDIRIZZO EMAIL", objectName="afield"), 0, 0, 1, 2)
        self.email = QLineEdit()
        self.email.setPlaceholderText("nome@esempio.it")
        self.email.textChanged.connect(self._email_changed)
        g.addWidget(self.email, 1, 0, 1, 2)
        g.addWidget(QLabel("FORNITORE", objectName="afield"), 2, 0, 1, 2)
        self.prov = QComboBox()
        for k in providers.ORDER:
            self.prov.addItem(providers.PROVIDERS[k]["label"], k)
        self.prov.currentIndexChanged.connect(self._prov_changed)
        self._manual = False   # diventa True se l'utente sceglie il fornitore a mano
        self.prov.activated.connect(lambda _i: setattr(self, "_manual", True))
        g.addWidget(self.prov, 3, 0, 1, 2)
        self.body.addLayout(g)

        self.hint = QLabel("")
        self.hint.setObjectName("asub")
        self.hint.setWordWrap(True)
        self.body.addWidget(self.hint)
        self.help_btn = QPushButton("")
        self.help_btn.setObjectName("link")
        self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_btn.clicked.connect(lambda: open_url(providers.PROVIDERS[self.key()].get("help_url", "")))
        self.body.addWidget(self.help_btn)

        self.pw_box = QWidget()
        pl = QVBoxLayout(self.pw_box)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(6)
        self.pw_label = QLabel("PASSWORD", objectName="afield")
        pl.addWidget(self.pw_label)
        prow = QHBoxLayout()
        self.pw = QLineEdit()
        self.pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw.returnPressed.connect(self._save)
        prow.addWidget(self.pw, 1)
        eye = QPushButton()
        eye.setObjectName("ghost")
        eye.setIcon(ic("eye", "#fff", 18))
        eye.setFixedWidth(44)
        eye.setToolTip("Mostra o nascondi la password")
        eye.clicked.connect(lambda: self.pw.setEchoMode(
            QLineEdit.EchoMode.Normal if self.pw.echoMode() == QLineEdit.EchoMode.Password else QLineEdit.EchoMode.Password))
        prow.addWidget(eye)
        pl.addLayout(prow)
        self.body.addWidget(self.pw_box)

        self.ms_btn = text_btn("microsoft", "Accedi con Microsoft", self._ms_login, "#fff", "accent")
        self.body.addWidget(self.ms_btn)

        self.srv_box = QWidget()
        sl = QGridLayout(self.srv_box)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setHorizontalSpacing(10)
        sl.addWidget(QLabel("SERVER IMAP", objectName="afield"), 0, 0)
        sl.addWidget(QLabel("PORTA", objectName="afield"), 0, 1)
        self.host = QLineEdit()
        self.port = QLineEdit("993")
        self.port.setFixedWidth(90)
        sl.addWidget(self.host, 1, 0)
        sl.addWidget(self.port, 1, 1)
        self.body.addWidget(self.srv_box)
        self.adv = QPushButton("Server e porta")
        self.adv.setObjectName("link")
        self.adv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv.clicked.connect(lambda: self.srv_box.setVisible(not self.srv_box.isVisible()))
        self.body.addWidget(self.adv)

        self.err = QLabel("")
        self.err.setObjectName("err")
        self.err.setWordWrap(True)
        self.err.hide()
        self.body.addWidget(self.err)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.setFixedHeight(6)
        self.busy.setTextVisible(False)
        self.busy.hide()
        self.body.addWidget(self.busy)

        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("Annulla")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        row.addWidget(cancel)
        self.go = text_btn("check", "Prova e salva", self._save, "#fff", "accent")
        self.go.setDefault(True)
        row.addWidget(self.go)
        self.body.addLayout(row)
        self._prov_changed()
        self.email.setFocus()

    def key(self):
        return self.prov.currentData()

    def _email_changed(self, text):
        k = providers.detect(text)
        dom = text.strip().lower().rpartition("@")[2]
        if k:
            self.prov.setCurrentIndex(providers.ORDER.index(k))
        elif "@" in text and "." in dom and not self._manual:
            # dominio non noto (es. aziendale): si parte da «Altro», l'utente può scegliere Aruba ecc.
            self.prov.setCurrentIndex(providers.ORDER.index("altro"))
            self.host.setText(providers.guess_host(text))
        elif "@" in text and self.key() == "altro":
            self.host.setText(providers.guess_host(text))

    def _prov_changed(self):
        p = providers.PROVIDERS[self.key()]
        oauth = p["auth"] == "oauth_ms"
        self.hint.setText(p["hint"])
        self.help_btn.setVisible(bool(p.get("help_url")))
        self.help_btn.setText((p.get("help_label") or "") + "  →")
        self.pw_label.setText(p.get("pw_label", "Password della casella").upper())
        self.pw_box.setVisible(not oauth)
        self.ms_btn.setVisible(oauth)
        self.go.setVisible(not oauth)
        self.host.setText(p["host"] or providers.guess_host(self.email.text()))
        self.port.setText(str(p["port"]))
        self.srv_box.setVisible(self.key() == "altro")
        self.adv.setVisible(self.key() != "altro" and not oauth)
        self.err.hide()
        self.adjustSize()

    def _fail(self, msg):
        self.busy.hide()
        self.go.setEnabled(True)
        self.ms_btn.setEnabled(True)
        self.err.setText(msg)
        self.err.show()
        self.adjustSize()

    def _check_email(self):
        e = self.email.text().strip().lower()
        if "@" not in e or "." not in e.rpartition("@")[2]:
            self._fail("Scrivi un indirizzo email valido.")
            return ""
        return e

    def _save(self):
        e = self._check_email()
        if not e:
            return
        pw = self.pw.text()
        host = self.host.text().strip()
        if not pw:
            return self._fail("Scrivi la password.")
        if not host:
            return self._fail("Scrivi il server IMAP.")
        try:
            port = int(self.port.text().strip() or "993")
        except ValueError:
            return self._fail("La porta deve essere un numero (di solito 993).")
        key = self.key()
        self.err.hide()
        self.busy.show()
        self.go.setEnabled(False)

        def work():
            im = mailscan.connect(host, port, e, pw.replace(" ", "") if key == "gmail" else pw)
            fl = mailscan.folders(im)
            im.logout()
            return fl

        def ok(_fl):
            vault.set_secret(e, pw.replace(" ", "") if key == "gmail" else pw)
            self.store.add_account(e, key, host, port, "password")
            self.accept()

        def ko(msg):
            if key in ("gmail", "yahoo", "icloud") and "rifiut" not in msg.lower():
                msg += "\nServe la password per le app, non quella con cui entri nel sito."
            self._fail("Non riesco a entrare: " + msg)

        self.worker = Worker(work, self)
        self.worker.done.connect(ok)
        self.worker.failed.connect(lambda m: ko(m if not m.startswith("[") else m))
        self.worker.start()

    def _ms_login(self):
        e = self._check_email()
        if not e:
            return
        self.err.hide()
        self.busy.show()
        self.ms_btn.setEnabled(False)

        def work():
            cfg = msoauth.config()
            if not cfg["client_id"]:
                raise LookupError("presto")
            tok = msoauth.login(cfg["client_id"], cfg["tenant"], e)
            tok["client_id"] = cfg["client_id"]
            im = mailscan.connect("outlook.office365.com", 993, e, tok["access_token"], "oauth_ms")
            im.logout()
            return tok

        def ok(tok):
            vault.set_secret(e, json.dumps(tok))
            self.store.add_account(e, "outlook", "outlook.office365.com", 993, "oauth_ms")
            self.accept()

        def ko(msg):
            if msg == "presto":
                self._fail("Le caselle Outlook e Hotmail arrivano con un prossimo aggiornamento: "
                           "stiamo completando la registrazione presso Microsoft.")
            else:
                self._fail("Accesso a Microsoft non riuscito: " + msg)

        self.worker = Worker(work, self)
        self.worker.done.connect(ok)
        self.worker.failed.connect(ko)
        self.worker.start()


# ---------------------------------------------------------------- tabella dei servizi
COLS = ["Servizio", "Tipo", "Iscritto dal", "Ultima email", "Email", "Stato"]


class ServiceModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.rows = []

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(COLS)

    def headerData(self, s, o, role=Qt.ItemDataRole.DisplayRole):
        if o == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLS[s].upper()
        return None

    def data(self, idx, role=Qt.ItemDataRole.DisplayRole):
        r = self.rows[idx.row()]
        c = idx.column()
        if role == Qt.ItemDataRole.DisplayRole:
            return (r["name"], classify.CATEGORIES[r["cat"]][0], fmt_date(r["first"]), fmt_date(r["last"]),
                    str(r["n"]), STATUS.get(r["status"], ("", ""))[0])[c]
        if role == Qt.ItemDataRole.UserRole:   # ordinamento
            return (r["name"].lower(), r["cat"], r["first"] or 9e12, r["last"], r["n"], r["status"])[c]
        if role == Qt.ItemDataRole.UserRole + 1:
            return r
        if role == Qt.ItemDataRole.ToolTipRole and c == 0:
            return r["domain"]
        if role == Qt.ItemDataRole.TextAlignmentRole and c == 4:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return None


class ServiceFilter(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.cat = ""
        self.status = ""
        self.text = ""
        self.people = False
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def filterAcceptsRow(self, row, parent):
        r = self.sourceModel().rows[row]
        if r["cat"] == "persona" and not self.people and self.cat != "persona":
            return False
        if self.cat and r["cat"] != self.cat:
            return False
        if self.status == "nuovo" and r["status"]:
            return False
        if self.status and self.status != "nuovo" and r["status"] != self.status:
            return False
        if self.text and self.text not in (r["name"] + " " + r["domain"]).lower():
            return False
        return True


class RowDelegate(QStyledItemDelegate):
    """Prima colonna: nome in grassetto + dominio; colonne Tipo e Stato: pillole colorate."""

    def paint(self, p, opt, idx):
        r = idx.data(Qt.ItemDataRole.UserRole + 1)
        c = idx.column()
        if c not in (0, 1, 5):
            return super().paint(p, opt, idx)
        p.save()
        if opt.state & QStyle.StateFlag.State_Selected:
            p.fillRect(opt.rect, QColor(ACCENT_L))
        elif idx.row() % 2:
            p.fillRect(opt.rect, QColor(GRAY_50))
        else:
            p.fillRect(opt.rect, QColor("#ffffff"))
        rect = opt.rect.adjusted(10, 0, -6, 0)
        if c == 0:
            f = QFont(opt.font)
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(NAVY))
            p.drawText(rect.adjusted(0, 6, 0, -rect.height() // 2), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom),
                       p.fontMetrics().elidedText(r["name"], Qt.TextElideMode.ElideRight, rect.width()))
            f.setBold(False)
            f.setPointSizeF(max(7.0, opt.font.pointSizeF() - 1.5))
            p.setFont(f)
            p.setPen(QColor(GRAY_500))
            p.drawText(rect.adjusted(0, rect.height() // 2 + 1, 0, -4), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop),
                       r["domain"])
        else:
            if c == 1:
                text, col = classify.CATEGORIES[r["cat"]][0], CAT_COLORS[r["cat"]]
            else:
                text, col = STATUS.get(r["status"], ("", ""))
            if text:
                f = QFont(opt.font)
                f.setBold(True)
                f.setPointSizeF(max(7.0, opt.font.pointSizeF() - 1.5))
                p.setFont(f)
                w = p.fontMetrics().horizontalAdvance(text.upper()) + 20
                pill = QRectF(rect.x(), rect.center().y() - 11, w, 22)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setPen(Qt.PenStyle.NoPen)
                bg = QColor(col)
                bg.setAlpha(28)
                p.setBrush(bg)
                p.drawRoundedRect(pill, 11, 11)
                p.setPen(QColor(col))
                p.drawText(pill, int(Qt.AlignmentFlag.AlignCenter), text.upper())
        p.restore()


# ---------------------------------------------------------------- finestra principale
class MainWindow(QMainWindow):
    def __init__(self, settings, store):
        super().__init__()
        self.settings = settings
        self.store = store
        self.manifest = None
        self.scan_thread = None
        self.check_thread = None
        self.dl_thread = None
        self.closing_for_update = False
        self.cur = None
        self.setWindowTitle(APP_TITLE)
        self.setWindowIcon(QIcon(render_icon(128)))
        self.setMinimumWidth(960)  # sotto, la colonna Servizio diventa illeggibile
        self.resize(1440, 900)
        self._build()
        dentro_lo_schermo(self)  # la finestra non esce mai dallo schermo (MacBook)
        self.refresh()
        QTimer.singleShot(1200, self.ensure_shortcut)

    def avvia_rete(self):
        """Dopo il benvenuto (mai prima della risposta dell'utente): controllo aggiornamenti e, solo col
        consenso, il segnale giornaliero delle statistiche."""
        QTimer.singleShot(2500, lambda: self.check_updates(False))
        QTimer.singleShot(6000, self._avvia_licenza)

    def _avvia_licenza(self):
        # segnale giornaliero, in sottofondo: parte solo se l'utente ha detto sì alle statistiche
        lic = pro.licenza()
        if lic is not None:
            lic.avvia()

    def _disponi_tiles(self, colonne):
        if colonne == self._tile_colonne:
            return
        self._tile_colonne = colonne
        g = self._griglia_tiles
        for t in self._tile_widgets:
            g.removeWidget(t)
        for i, t in enumerate(self._tile_widgets):
            g.addWidget(t, i // colonne, i % colonne)
        for c in range(5):
            g.setColumnStretch(c, 1 if c < colonne else 0)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if getattr(self, "_tile_widgets", None):
            w = self.width()
            self._disponi_tiles(5 if w >= 1250 else 3)
            # finestra stretta: via le colonne che il dettaglio a destra mostra già (Email, Ultima email, Iscritto dal)
            nascoste = set() if w >= 1350 else {4} if w >= 1220 else {3, 4} if w >= 1150 else {2, 3, 4}
            for c in (2, 3, 4):
                self.table.setColumnHidden(c, c in nascoste)
            stretta = w < 1150
            self.table.setColumnWidth(1, 104 if stretta else 130)
            self.table.setColumnWidth(5, 124 if stretta else 150)

    # ---- costruzione
    def _build(self):
        central = QWidget(objectName="canvas")
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 14, 16, 8)
        root.setSpacing(14)

        header = QFrame(objectName="header")
        shadow(header, 30, 8, 70)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(18, 12, 18, 12)
        hl.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(render_icon(44))
        hl.addWidget(icon)
        hl.addSpacing(4)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(QLabel(APP_TITLE, objectName="brand"))
        col.addWidget(QLabel(f"Versione {VERSION}", objectName="ver"))
        hl.addLayout(col)
        hl.addStretch(1)
        self.update_btn = text_btn("refresh", "Aggiorna", self.show_update_dialog, "#fff", "accent")
        self.update_btn.hide()
        hl.addWidget(self.update_btn)
        hl.addWidget(text_btn("plus", "Aggiungi casella", self.act_add, tip="Aggiungi una casella email"))
        self.scan_btn = text_btn("refresh", "Analizza", self.act_scan_all, "#fff", "accent",
                                 "Legge le email nuove di tutte le caselle")
        hl.addWidget(self.scan_btn)
        hl.addWidget(text_btn("export", "Esporta", self.act_export, tip="Salva l'elenco in un file per Excel"))
        hl.addWidget(text_btn("info", "", self.act_about, tip="Informazioni e aggiornamenti"))
        root.addWidget(header)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.stack.addWidget(self._build_empty())
        self.stack.addWidget(self._build_main())

        # barra di avanzamento dell'analisi
        self.scan_bar = QFrame(objectName="card")
        sb = QHBoxLayout(self.scan_bar)
        sb.setContentsMargins(16, 10, 16, 10)
        self.scan_text = QLabel("")
        self.scan_text.setObjectName("hint")
        sb.addWidget(self.scan_text, 1)
        self.scan_prog = QProgressBar(objectName="scan")
        self.scan_prog.setTextVisible(False)
        self.scan_prog.setFixedWidth(260)
        self.scan_prog.setRange(0, 1000)
        sb.addWidget(self.scan_prog)
        sb.addWidget(text_btn("stop", "Ferma", self.act_stop, NAVY, "", "Ferma l'analisi (riparte da qui la prossima volta)"))
        self.scan_bar.hide()
        root.addWidget(self.scan_bar)
        self.setCentralWidget(central)

    def _build_empty(self):
        w = QWidget(objectName="canvas")
        lay = QVBoxLayout(w)
        lay.addStretch(1)
        card = QFrame(objectName="card")
        shadow(card, 30, 6, 40)
        card.setMaximumWidth(720)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 36, 40, 36)
        cl.setSpacing(14)
        ico = QLabel()
        ico.setPixmap(render_icon(84))
        ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(ico)
        t = QLabel("A cosa sei iscritto con la tua email?")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet("font-size:26px; font-weight:800;")
        cl.addWidget(t)
        s = QLabel("Collega la tua casella: tk-iscrizioni legge mittenti e oggetti delle email e ti mostra "
                   "a quali siti, servizi e newsletter sei iscritto, da quando, e come uscirne.")
        s.setWordWrap(True)
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet(f"font-size:14px; color:{GRAY_500};")
        cl.addWidget(s)
        steps = QHBoxLayout()
        steps.setSpacing(12)
        for n, (title, body) in enumerate((("Aggiungi la casella", "Gmail, Aruba, Libero, Virgilio, Yahoo, iCloud…"),
                                           ("Analizza", "Solo le intestazioni, sul tuo computer"),
                                           ("Fai pulizia", "Disiscriviti o cancella gli account che non usi")), 1):
            f = QFrame(objectName="acct")
            f.setMinimumHeight(118)
            fl = QVBoxLayout(f)
            fl.setContentsMargins(14, 12, 14, 12)
            fl.setSpacing(4)
            num = QLabel(f"0{n}")
            num.setStyleSheet(f"color:{ACCENT}; font-weight:800; font-size:12px;")
            fl.addWidget(num)
            tt = QLabel(title)
            tt.setStyleSheet("font-weight:800; font-size:14px;")
            fl.addWidget(tt)
            bb = QLabel(body)
            bb.setWordWrap(True)
            bb.setObjectName("hint")
            bb.setMinimumHeight(36)
            bb.setAlignment(Qt.AlignmentFlag.AlignTop)
            fl.addWidget(bb)
            fl.addStretch(1)
            steps.addWidget(f, 1)
        cl.addLayout(steps)
        cl.addSpacing(8)
        go = text_btn("plus", "Aggiungi la tua casella", self.act_add, "#fff", "accent")
        go.setMinimumHeight(46)
        cl.addWidget(go)
        lock = QLabel("Sola lettura · i dati restano sul computer · password cifrate · software libero")
        lock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock.setObjectName("hint")
        cl.addWidget(lock)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(card, 10)
        row.addStretch(1)
        lay.addLayout(row)
        lay.addStretch(2)
        return w

    def _build_main(self):
        w = QWidget(objectName="canvas")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)

        # ---- sinistra: caselle e filtri
        left = QVBoxLayout()
        left.setSpacing(14)
        self.acc_card = Card("mail", "Le tue caselle")
        self.acc_list = QVBoxLayout()
        self.acc_list.setSpacing(8)
        self.acc_card.lay.addLayout(self.acc_list)
        self.acc_card.lay.addWidget(text_btn("plus", "Aggiungi casella", self.act_add, NAVY, ""))
        left.addWidget(self.acc_card)

        fcard = Card("search", "Filtri")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Cerca un servizio…")
        self.search.textChanged.connect(self._filter_changed)
        fcard.lay.addWidget(self.search)
        fcard.lay.addWidget(QLabel("TIPO", objectName="field"))
        self.cat_chips = {}
        grid = QGridLayout()
        grid.setSpacing(6)
        for i, (k, lab) in enumerate([("", "Tutti")] + [(k, v[0]) for k, v in classify.CATEGORIES.items()]):
            b = QPushButton(lab)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, key=k: self._set_cat(key))
            self.cat_chips[k] = b
            grid.addWidget(b, i // 2, i % 2)
        fcard.lay.addLayout(grid)
        fcard.lay.addWidget(QLabel("STATO", objectName="field"))
        self.st_chips = {}
        grid2 = QGridLayout()
        grid2.setSpacing(6)
        for i, (k, lab) in enumerate((("", "Tutti"), ("nuovo", "Da decidere"), ("cancellare", "Da cancellare"),
                                      ("tenere", "Da tenere"))):
            b = QPushButton(lab)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, key=k: self._set_status_filter(key))
            self.st_chips[k] = b
            grid2.addWidget(b, i // 2, i % 2)
        fcard.lay.addLayout(grid2)
        self.people = QCheckBox("Mostra anche le persone")
        self.people.setToolTip("Mittenti con caselle personali (Gmail, Libero…) e del tuo stesso dominio")
        self.people.toggled.connect(self._filter_changed)
        fcard.lay.addWidget(self.people)
        left.addWidget(fcard)
        left.addStretch(1)
        lw = QWidget(objectName="canvas")
        lw.setLayout(left)
        lw.setFixedWidth(236)  # colonne laterali strette: la finestra deve stare anche su un MacBook
        ls = QScrollArea()
        ls.setWidgetResizable(True)
        ls.setFrameShape(QFrame.Shape.NoFrame)
        ls.setWidget(lw)
        ls.setFixedWidth(248)
        lay.addWidget(ls)

        # ---- centro: numeri + tabella
        center = QVBoxLayout()
        center.setSpacing(14)
        # i 5 numeri: in fila sulle finestre larghe, su due righe (3 + 2) su quelle strette (MacBook)
        tiles = QGridLayout()
        tiles.setHorizontalSpacing(12)
        tiles.setVerticalSpacing(12)
        self._griglia_tiles = tiles
        self._tile_widgets = []
        self._tile_colonne = 0
        self.tiles = {}
        for key, lab, color in (("svc", "SERVIZI TROVATI", NAVY), ("acc", "CON UN ACCOUNT", ACCENT),
                                ("news", "NEWSLETTER", "#d97706"), ("del", "DA CANCELLARE", RED),
                                ("mail", "EMAIL ANALIZZATE", GRAY_500)):
            t = QFrame(objectName="tile")
            shadow(t, 20, 4, 30)
            t.setStyleSheet(f"QFrame#tile {{ border-left:4px solid {color}; }}")
            tl = QVBoxLayout(t)
            tl.setContentsMargins(16, 10, 16, 12)
            tl.setSpacing(0)
            num = QLabel("0", objectName="tilenum")
            tl.addWidget(num)
            etichetta = QLabel(lab, objectName="tilelab")
            etichetta.setWordWrap(True)  # «EMAIL ANALIZZATE» va su due righe quando la finestra è stretta
            tl.addWidget(etichetta)
            self.tiles[key] = num
            self._tile_widgets.append(t)
        self._disponi_tiles(5)
        center.addLayout(tiles)
        tcard = QFrame(objectName="card")
        shadow(tcard, 26, 5, 38)
        tl = QVBoxLayout(tcard)
        tl.setContentsMargins(12, 12, 12, 12)
        self.model = ServiceModel()
        self.proxy = ServiceFilter()
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setItemDelegate(RowDelegate(self.table))
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(2, Qt.SortOrder.AscendingOrder)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c, wdt in ((1, 130), (2, 110), (3, 110), (4, 70), (5, 150)):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(c, wdt)
        self.table.selectionModel().currentRowChanged.connect(lambda cur, _p: self.show_detail(cur))
        tl.addWidget(self.table)
        self.count_lab = QLabel("")
        self.count_lab.setObjectName("hint")
        self.count_lab.setWordWrap(True)
        tl.addWidget(self.count_lab)
        center.addWidget(tcard, 1)
        cw = QWidget(objectName="canvas")
        cw.setLayout(center)
        lay.addWidget(cw, 1)

        # ---- destra: dettaglio
        self.detail = QFrame(objectName="card")
        shadow(self.detail, 26, 5, 38)
        self.detail.setMinimumWidth(246)
        self.detail.setMaximumWidth(360)
        dl = QVBoxLayout(self.detail)
        dl.setContentsMargins(20, 20, 20, 20)
        dl.setSpacing(10)
        self.d_name = QLabel("", objectName="bigname")
        self.d_name.setWordWrap(True)
        dl.addWidget(self.d_name)
        self.d_dom = QLabel("")
        self.d_dom.setObjectName("hint")
        dl.addWidget(self.d_dom)
        self.d_cat = QLabel("")
        dl.addWidget(self.d_cat)
        self.d_info = QGridLayout()
        self.d_info.setVerticalSpacing(6)
        self.d_vals = {}
        for i, (k, lab) in enumerate((("first", "Iscritto dal (prima email)"), ("last", "Ultima email"),
                                      ("n", "Email ricevute"), ("box", "Casella"), ("sig", "Segnali trovati"))):
            l = QLabel(lab.upper(), objectName="field")
            v = QLabel("")
            v.setWordWrap(True)
            v.setStyleSheet("font-weight:600;")
            self.d_info.addWidget(l, i * 2, 0)
            self.d_info.addWidget(v, i * 2 + 1, 0)
            self.d_vals[k] = v
        dl.addLayout(self.d_info)
        self.b_site = text_btn("globe", "Apri il sito", self.act_site, NAVY, "")
        self.b_unsub = text_btn("unsub", "Disiscriviti", self.act_unsub, "#fff", "accent")
        self.b_delete = text_btn("user-x", "Come cancello l'account?", self.act_howto_delete, NAVY, "")
        for b in (self.b_unsub, self.b_delete, self.b_site):
            dl.addWidget(b)
        dl.addWidget(QLabel("COSA NE FAI?", objectName="field"))
        seg = QHBoxLayout()
        seg.setSpacing(6)
        self.seg = {}
        for k, lab in (("tenere", "Tengo"), ("cancellare", "Da cancellare"), ("fatto", "Cancellato")):
            b = QPushButton(lab)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, key=k: self.act_status(key))
            self.seg[k] = b
            seg.addWidget(b)
        dl.addLayout(seg)
        self.note = QLineEdit()
        self.note.setPlaceholderText("Una nota (es. «account di lavoro»)")
        self.note.editingFinished.connect(self.act_note)
        dl.addWidget(self.note)
        dl.addWidget(QLabel("ULTIME EMAIL", objectName="field"))
        self.d_recent = QLabel("")
        self.d_recent.setWordWrap(True)
        self.d_recent.setTextFormat(Qt.TextFormat.RichText)
        self.d_recent.setAlignment(Qt.AlignmentFlag.AlignTop)
        rs = QScrollArea()
        rs.setWidgetResizable(True)
        rs.setFrameShape(QFrame.Shape.NoFrame)
        rs.setWidget(self.d_recent)
        dl.addWidget(rs, 1)
        self.d_empty = QLabel("Scegli un servizio dall'elenco per vedere i dettagli.")
        self.d_empty.setWordWrap(True)
        self.d_empty.setObjectName("hint")
        self.d_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(self.d_empty)
        lay.addWidget(self.detail)
        self.cat_chips[""].setChecked(True)
        self.st_chips[""].setChecked(True)
        self._detail_visible(False)
        return w

    # ---- dati
    def refresh(self, keep=None):
        accs = self.store.accounts()
        self.stack.setCurrentIndex(1 if accs else 0)
        while self.acc_list.count():
            item = self.acc_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for a in accs:
            self.acc_list.addWidget(self._account_row(a))
        rows = self.store.services()
        self.model.set_rows(rows)
        real = [r for r in rows if r["cat"] != "persona"]
        self.tiles["svc"].setText(str(len(real)))
        self.tiles["acc"].setText(str(sum(r["cat"] in ("account", "social") for r in real)))
        self.tiles["news"].setText(str(sum(r["cat"] == "newsletter" or r["lst"] > 0 for r in real)))
        self.tiles["del"].setText(str(sum(r["status"] == "cancellare" for r in real)))
        self.tiles["mail"].setText(f"{self.store.total_messages():,}".replace(",", "."))
        for k, b in self.cat_chips.items():
            n = len(real) if k == "" else sum(r["cat"] == k for r in rows)
            b.setText(f"{'Tutti' if k == '' else classify.CATEGORIES[k][0]}  {n}")
        self._update_count()
        if keep:
            self.select_domain(keep)
        elif self.proxy.rowCount() and not self.table.currentIndex().isValid():
            self.table.selectRow(0)

    def _account_row(self, a):
        f = QFrame(objectName="acct")
        l = QHBoxLayout(f)
        l.setContentsMargins(12, 8, 8, 8)
        col = QVBoxLayout()
        col.setSpacing(1)
        e = QLabel(a["email"])
        e.setStyleSheet("font-weight:700;")
        e.setToolTip(f"{a['host']}:{a['port']}")
        col.addWidget(e)
        if a["last_error"]:
            s = QLabel("Errore: " + a["last_error"])
            s.setStyleSheet(f"color:{RED}; font-size:11px;")
            s.setWordWrap(True)
        elif a["last_scan"]:
            s = QLabel(f"{a['n']:,} email · {fmt_date(a['last_scan'], True)}".replace(",", "."))
            s.setObjectName("hint")
            s.setWordWrap(True)
        else:
            s = QLabel("Non ancora analizzata")
            s.setObjectName("hint")
        e.setWordWrap(True)
        col.addWidget(s)
        l.addLayout(col, 1)
        l.addWidget(mini_btn("refresh", "Analizza questa casella", lambda: self.start_scan([a])))
        l.addWidget(mini_btn("trash", "Togli la casella (cancella anche le sue credenziali)",
                             lambda: self.act_remove(a), RED))
        return f

    def select_domain(self, domain):
        for row in range(self.proxy.rowCount()):
            r = self.proxy.index(row, 0).data(Qt.ItemDataRole.UserRole + 1)
            if r["domain"] == domain:
                self.table.selectRow(row)
                return

    def _update_count(self):
        n = self.proxy.rowCount()
        self.count_lab.setText(f"{n} servizi mostrati · clic sulle intestazioni per ordinare")

    def _filter_changed(self, *_):
        self.proxy.text = self.search.text().strip().lower()
        self.proxy.people = self.people.isChecked()
        self.proxy.invalidateFilter()
        self._update_count()

    def _set_cat(self, key):
        for k, b in self.cat_chips.items():
            b.setChecked(k == key)
        self.proxy.cat = key
        self._filter_changed()

    def _set_status_filter(self, key):
        for k, b in self.st_chips.items():
            b.setChecked(k == key)
        self.proxy.status = key
        self._filter_changed()

    def _detail_visible(self, on):
        for w in (self.d_name, self.d_dom, self.d_cat, self.b_site, self.b_unsub, self.b_delete, self.note,
                  self.d_recent.parentWidget().parentWidget()):
            w.setVisible(on)
        for i in range(self.d_info.count()):
            self.d_info.itemAt(i).widget().setVisible(on)
        for b in self.seg.values():
            b.setVisible(on)
        lay = self.detail.layout()
        for i in range(lay.count()):
            wdg = lay.itemAt(i).widget()
            if isinstance(wdg, QLabel) and wdg.objectName() == "field":
                wdg.setVisible(on)
        self.d_empty.setVisible(not on)

    def show_detail(self, idx):
        if not idx.isValid():
            self.cur = None
            self._detail_visible(False)
            return
        r = idx.data(Qt.ItemDataRole.UserRole + 1)
        self.cur = r
        self._detail_visible(True)
        self.d_name.setText(r["name"])
        self.d_dom.setText(r["domain"])
        col = CAT_COLORS[r["cat"]]
        self.d_cat.setText(f"<span style='background:{col}; color:#fff; font-weight:800; font-size:11px;'>"
                           f"&nbsp;&nbsp;{classify.CATEGORIES[r['cat']][0].upper()}&nbsp;&nbsp;</span>"
                           f"&nbsp; <span style='color:{GRAY_500};'>{html.escape(classify.CATEGORIES[r['cat']][1])}</span>")
        self.d_cat.setWordWrap(True)
        self.d_vals["first"].setText(fmt_date(r["first"]))
        self.d_vals["last"].setText(fmt_date(r["last"]))
        self.d_vals["n"].setText(str(r["n"]))
        accs = {a["id"]: a["email"] for a in self.store.accounts()}
        self.d_vals["box"].setText(", ".join(accs.get(i, "?") for i in r["accounts"]))
        sig = []
        if r["acc"]:
            sig.append(f"benvenuto o conferma ({r['acc']})")
        if r["sec"]:
            sig.append(f"codici e password ({r['sec']})")
        if r["pur"]:
            sig.append(f"ordini e ricevute ({r['pur']})")
        if r["lst"]:
            sig.append(f"newsletter ({r['lst']})")
        self.d_vals["sig"].setText(", ".join(sig) or "nessuno: ti hanno solo scritto")
        https, mailto = classify.unsub_links(r["unsub"])
        self.b_unsub.setEnabled(True)
        self.b_unsub.setToolTip("Disiscrizione in un clic" if (https and r["unsub_post"]) else
                                "Apre la pagina di disiscrizione del mittente" if https else
                                "Prepara l'email di disiscrizione" if mailto else
                                "Nessun link di disiscrizione verificato (firma DKIM del mittente): cerco come fare")
        for k, b in self.seg.items():
            b.setChecked(r["status"] == k)
        self.note.setText(r["note"])
        lines = []
        for m in self.store.recent(r["domain"]):
            lines.append(f"<div style='margin-bottom:8px'><span style='color:{GRAY_500}; font-size:11px'>"
                         f"{fmt_date(m['ts'])} · {html.escape(m['from_addr'])}</span><br>"
                         f"<b>{html.escape(m['subject'] or '(senza oggetto)')}</b></div>")
        self.d_recent.setText("".join(lines))

    # ---- azioni
    def act_add(self):
        dlg = AccountDialog(self, self.store)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            accs = self.store.accounts()
            new = [a for a in accs if not a["last_scan"]]
            if new and tk_choice(self, "Casella aggiunta", "Analizzo subito la casella? Con molte email ci vuole "
                                 "qualche minuto: puoi continuare a usare il programma.",
                                 [("Più tardi", "ghost"), ("Analizza ora", "accent")], "ok") == 1:
                self.start_scan(new)

    def act_remove(self, a):
        if tk_choice(self, "Togliere la casella?", f"{a['email']}\n\nCancello dal computer la password e le "
                     "informazioni raccolte da questa casella. Le tue email non vengono toccate.",
                     [("Annulla", "ghost"), ("Togli", "accent")], "warn") != 1:
            return
        vault.delete_secret(a["email"])
        self.store.remove_account(a["id"])
        self.refresh()

    def act_scan_all(self):
        accs = self.store.accounts()
        if not accs:
            return self.act_add()
        self.start_scan(accs)

    def start_scan(self, accs):
        if self.scan_thread and self.scan_thread.isRunning():
            return
        self.scan_btn.setEnabled(False)
        self.scan_bar.show()
        self.scan_prog.setValue(0)
        self.scan_text.setText("Avvio dell'analisi…")
        t = self.scan_thread = ScanThread(self.store, accs, self)
        t.progress.connect(self._scan_progress)
        t.finished_all.connect(self._scan_done)
        t.start()

    def _scan_progress(self, text, frac):
        self.scan_text.setText(text)
        self.scan_prog.setValue(int(frac * 1000))

    def _scan_done(self, report):
        self.scan_bar.hide()
        self.scan_btn.setEnabled(True)
        keep = self.cur["domain"] if self.cur else None
        self.refresh(keep)
        errors = [f"{e}: {m}" for e, ok, m in report if ok is False]
        if errors:
            tk_warn(self, "Analisi con errori", "\n\n".join(errors))
        elif any(ok is None for _e, ok, _m in report):
            self.statusBar().showMessage("Analisi fermata: la prossima volta riparte da dove si è interrotta.", 8000)
        else:
            new = sum(m for _e, ok, m in report if ok)
            self.statusBar().showMessage(f"Analisi completata: {new} email nuove lette.", 8000)

    def act_stop(self):
        if self.scan_thread:
            self.scan_thread.cancel()
            self.scan_text.setText("Mi fermo…")

    def act_site(self):
        if self.cur:
            open_url("https://" + self.cur["domain"])

    def act_howto_delete(self):
        if self.cur:
            q = urllib.parse.quote_plus(f"come cancellare account {self.cur['name']} {self.cur['domain']}")
            open_url("https://duckduckgo.com/?q=" + q)

    def act_unsub(self):
        r = self.cur
        if not r:
            return
        https, mailto = classify.unsub_links(r["unsub"])
        if https and r["unsub_post"]:
            if tk_choice(self, f"Disiscriverti da {r['name']}?",
                         "Chiedo al mittente di toglierti dalla sua lista con la disiscrizione in un clic, "
                         "lo standard che usano Gmail e Outlook. Il tuo account, se c'è, non viene cancellato.\n\n"
                         + self._avviso_link(https, r), [("Annulla", "ghost"), ("Disiscrivimi", "accent")]) != 1:
                return
            self._one_click(r, https)
        elif https:
            if tk_choice(self, f"Disiscriverti da {r['name']}?",
                         "Apro nel browser la pagina di disiscrizione indicata dal mittente.\n\n"
                         + self._avviso_link(https, r), [("Annulla", "ghost"), ("Apri la pagina", "accent")]) != 1:
                return
            open_url(https)
            self.statusBar().showMessage("Ho aperto la pagina di disiscrizione del mittente nel browser.", 8000)
        elif mailto:
            if tk_choice(self, f"Disiscriverti da {r['name']}?",
                         "Preparo nel tuo programma di posta l'email di disiscrizione indicata dal mittente: "
                         "controllala e inviala tu.\n\n" + self._avviso_link(mailto, r),
                         [("Annulla", "ghost"), ("Prepara l'email", "accent")]) != 1:
                return
            open_url(mailto)
            self.statusBar().showMessage("Ho preparato l'email di disiscrizione nel tuo programma di posta.", 8000)
        else:
            q = urllib.parse.quote_plus(f"come disiscriversi dalle email di {r['name']} {r['domain']}")
            open_url("https://duckduckgo.com/?q=" + q)
            self.statusBar().showMessage("Il mittente non indica un modo per disiscriversi: ho aperto la ricerca "
                                         "nel browser. Di solito il link è in fondo a una sua email.", 10000)

    @staticmethod
    def _avviso_link(link, r):
        """Dove porta il link, e un avviso se non è il dominio del servizio."""
        host = disiscrizione.host_di(link) or "?"
        dove = "L'email va a un indirizzo di" if link.lower().startswith("mailto:") else "Il link porta a"
        testo = f"{dove} «{host}»."
        if not classify.stesso_servizio(host, r["domain"]):
            testo += (f"\nAttenzione: non è il dominio del servizio ({r['domain']}). Spesso è la ditta che "
                      "spedisce le sue newsletter, ma se non ti convince annulla.")
        return testo

    def _one_click(self, r, url):
        def work():
            try:
                return True, disiscrizione.invia(url, timeout=20, contesto=mailscan._ctx())
            except disiscrizione.LinkNonAmmesso as e:
                return False, str(e)

        w = Worker(work, self)

        def ok(esito):
            inviata, msg = esito
            if not inviata:
                tk_warn(self, "Disiscrizione non inviata", f"Non mando la richiesta: {msg}.")
                return
            self.store.set_status(r["domain"], "disiscritto")
            self.refresh(r["domain"])
            tk_info(self, "Richiesta inviata", f"Ho chiesto a {r['name']} di toglierti dalla lista. Di solito "
                                               "smettono di scrivere entro pochi giorni.", "ok")

        def ko(msg):
            if tk_choice(self, "Disiscrizione non riuscita", f"Il mittente ha risposto con un errore ({msg}). "
                         "Vuoi aprire la sua pagina di disiscrizione nel browser?",
                         [("No", "ghost"), ("Apri la pagina", "accent")], "warn") == 1:
                open_url(url)
        w.done.connect(ok)
        w.failed.connect(ko)
        self._unsub_worker = w
        w.start()

    def act_status(self, key):
        if not self.cur:
            return
        new = "" if self.cur["status"] == key else key
        self.store.set_status(self.cur["domain"], new)
        self.refresh(self.cur["domain"])

    def act_note(self):
        if self.cur and self.note.text() != self.cur["note"]:
            self.store.set_status(self.cur["domain"], note=self.note.text())
            self.cur["note"] = self.note.text()

    def act_export(self, path=None):
        rows = [self.proxy.index(i, 0).data(Qt.ItemDataRole.UserRole + 1) for i in range(self.proxy.rowCount())]
        if not rows:
            return tk_info(self, APP_TITLE, "Non c'è niente da esportare con i filtri attuali.")
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Esporta l'elenco",
                                                  os.path.join(export_dir(), f"iscrizioni-{time.strftime('%Y-%m-%d')}.csv"),
                                                  "File per Excel (*.csv)")
            if not path:
                return
        accs = {a["id"]: a["email"] for a in self.store.accounts()}
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh, delimiter=";")
            w.writerow(["Servizio", "Dominio", "Tipo", "Iscritto dal", "Ultima email", "Email ricevute", "Caselle",
                        "Stato", "Nota", "Disiscrizione"])
            for r in rows:
                https, mailto = classify.unsub_links(r["unsub"])
                w.writerow([cella_csv(v) for v in (
                    r["name"], r["domain"], classify.CATEGORIES[r["cat"]][0], fmt_date(r["first"]),
                    fmt_date(r["last"]), r["n"], ", ".join(accs.get(i, "") for i in r["accounts"]),
                    STATUS.get(r["status"], ("", ""))[0], r["note"], https or mailto)])
        self.statusBar().showMessage(f"Esportati {len(rows)} servizi in {path}", 10000)
        return path

    def ensure_shortcut(self):
        from tkiscrizioni.util import APP_ROOT
        if not IS_WIN or not is_installed():
            return
        import threading
        from tkiscrizioni.util import migrate_legacy_names
        need_lnk = self.settings.value("lnk_root", "") != APP_ROOT

        def work():
            try:
                migrate_legacy_names()  # 1.0.5: collegamenti e voce «App installate» col nome tk-iscrizioni
            except Exception:
                pass
            if not need_lnk:
                return
            try:
                ensure_folder_shortcut()
                self.settings.setValue("lnk_root", APP_ROOT)
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    # ---- informazioni e aggiornamenti
    def act_about(self):
        dlg = AboutDialog(self)
        dlg.exec()
        if dlg.check:
            self.check_updates(True)

    def show_update_button(self, version):
        self.update_btn.setVisible(bool(version))
        if version:
            self.update_btn.setText(f"Aggiorna a {version}")

    def check_updates(self, manual):
        if self.check_thread is not None and self.check_thread.isRunning():
            return
        if not manual and time.time() - float(self.settings.value("last_check", 0)) < updater.CHECK_INTERVAL:
            cached = self.settings.value("available", "")
            if cached and updater.is_newer(cached):
                self.show_update_button(cached)
            return
        self.check_thread = Worker(updater.fetch_manifest, self)
        self.check_thread.done.connect(lambda m: self._checked(m, "", manual))
        self.check_thread.failed.connect(lambda err: self._checked(None, err, manual))
        if manual:
            self.statusBar().showMessage("Controllo aggiornamenti…")
        self.check_thread.start()

    def _checked(self, manifest, error, manual):
        if manifest is None:
            if manual:
                tk_warn(self, APP_TITLE, f"Impossibile controllare gli aggiornamenti.\n"
                                         f"Verifica la connessione a internet.\n\n{error}")
            return
        self.settings.setValue("last_check", time.time())
        version = str(manifest["version"])
        if not updater.is_newer(version):
            self.settings.setValue("available", "")
            self.show_update_button(None)
            if manual:
                tk_info(self, APP_TITLE, f"Hai già l'ultima versione di {APP_TITLE} ({VERSION}).", "ok")
            return
        self.manifest = manifest
        self.settings.setValue("available", version)
        self.show_update_button(version)
        if manual or self.settings.value("skip_version", "") != version:
            self.show_update_dialog()

    def show_update_dialog(self):
        m = self.manifest
        if m is None:
            self.check_updates(True)
            return
        dlg = UpdateDialog(self, m)
        dlg.exec()
        if dlg.choice == "skip":
            self.settings.setValue("skip_version", str(m["version"]))
        elif dlg.choice == "go":
            self.start_update()

    def start_update(self):
        asset = updater.asset_for(self.manifest)
        if asset is None:
            tk_info(self, APP_TITLE, "Questa versione non è ancora disponibile per il tuo sistema.")
            return
        if not is_installed():
            tk_info(self, APP_TITLE, "Stai usando la versione di sviluppo: l'aggiornamento automatico "
                                     "funziona solo con la versione installata.")
            return
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.cancel()
            self.scan_thread.wait(10000)
        dest = os.path.join(updater.download_dir(), os.path.basename(asset["url"].split("?")[0]))
        prog = TkProgress(self, "Aggiornamento in corso", f"Scarico {APP_TITLE} {self.manifest['version']}", True)
        prog.show()
        self.dl_thread = t = DownloadThread(asset["url"], dest, asset.get("sha256"), self)

        def on_ok(path):
            prog.bar.setRange(0, 0)
            prog.status.setText("Installazione dell'aggiornamento…")
            try:
                updater.apply_update(path, new_version=str(self.manifest["version"]))
            except Exception as exc:
                prog.close()
                tk_warn(self, APP_TITLE, f"Aggiornamento non riuscito:\n{exc}")
                return
            self.closing_for_update = True
            QTimer.singleShot(300, QApplication.instance().quit)

        def on_fail(msg):
            prog.close()
            if msg:
                tk_warn(self, APP_TITLE, f"Aggiornamento non riuscito:\n{msg}")

        prog.canceled.connect(t.cancel)
        t.progress.connect(lambda d, tot: prog.set_progress(d, tot, f"{human_size(d)} di {human_size(tot)}"))
        t.ok.connect(on_ok)
        t.failed.connect(on_fail)
        t.start()

    def closeEvent(self, e):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.cancel()
            self.scan_thread.wait(8000)
        e.accept()


# ---------------------------------------------------------------- avvio
def cli_update_test(argv):
    url = argv[argv.index("--update-test") + 1]
    log = os.path.join(log_dir(), "update-test.log")

    def write(msg):
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    try:
        m = updater.fetch_manifest(url)
        write(f"manifest {m['version']} (installata {VERSION})")
        if not updater.is_newer(m["version"]):
            write("nessun aggiornamento")
            return 0
        asset = updater.asset_for(m)
        if asset is None:
            write("nessun file firmato per questo sistema nel manifest: aggiornamento rifiutato")
            return 2
        dest = os.path.join(updater.download_dir(), os.path.basename(asset["url"].split("?")[0]))
        updater.download(asset["url"], dest, asset.get("sha256"))
        write(f"scaricato e verificato: {dest}")
        if not is_installed():
            write("versione di sviluppo: aggiornamento non applicato")
            return 3
        updater.apply_update(dest, relaunch="--no-relaunch" not in argv, new_version=m["version"])
        write("installazione avviata")
        return 0
    except Exception as exc:
        write(f"ERRORE: {exc}")
        return 1


def main():
    argv = sys.argv[1:]
    if "--update-test" in argv:
        sys.exit(cli_update_test(argv))
    selftest = argv[argv.index("--selftest") + 1] if "--selftest" in argv else ""
    if selftest:
        import tempfile
        os.environ["TKISCR_DATA"] = tempfile.mkdtemp(prefix="tkiscr-selftest-")
    app = QApplication(sys.argv)
    # licenza prima della finestra: consenso alle statistiche, benvenuto e invito al caffè (niente Pro)
    app.licenza = pro.crea_licenza(VERSION)
    app.setApplicationName(APP_TITLE)
    app.setStyle("Fusion")
    from tkiscrizioni.tk_licenza_qt import stile_caselle_globale
    app.setStyleSheet(STYLE + stile_caselle_globale())
    import PySide6
    from PySide6.QtCore import QLibraryInfo, QTranslator
    tr = QTranslator(app)
    for folder in (os.path.join(os.path.dirname(PySide6.__file__), "translations"),
                   QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
        if tr.load("qtbase_it", folder):
            app.installTranslator(tr)
            break
    if IS_WIN:
        app.setFont(QFont("Segoe UI", 10))
    settings = Settings()
    store = Store()
    if selftest:
        from tkiscrizioni import demo
        demo.fill(store)
        win = MainWindow(settings, store)
        win.resize(1440, 900)
        win.show()
        app.processEvents()
        win.select_domain("zalando.it")

        def shoot():
            win.grab().save(selftest)
            win.act_export(os.path.splitext(selftest)[0] + ".csv")
            app.quit()
        QTimer.singleShot(800, shoot)
        app.exec()
        return
    win = MainWindow(settings, store)
    win.show()

    def primo_avvio():
        # una sola finestra al primo avvio (benvenuto comune con le righe di tk-iscrizioni), poi la rete
        pro.benvenuto(win, BENVENUTO_RIGHE)
        settings.setValue("welcome_ok", True)
        win.avvia_rete()
        pro.invito(win)
    QTimer.singleShot(300, primo_avvio)
    sys.exit(app.exec())
