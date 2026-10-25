"""Screenshot di schermata vuota e finestre (per controllo visivo). Uso: python tests/shots.py <cartella>"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["TKISCR_DATA"] = tempfile.mkdtemp(prefix="tkiscr-shots-")
out = sys.argv[1]

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from tkiscrizioni import URL_SORGENTE, VERSION, app as A, pro  # noqa: E402
from tkiscrizioni.store import Store  # noqa: E402
from tkiscrizioni.tk_licenza_qt import BenvenutoDialog, InformazioniDialog, LicenzeDialog  # noqa: E402
from tkiscrizioni.util import Settings, cartella_licenze  # noqa: E402

qa = QApplication(sys.argv)
qa.licenza = pro.crea_licenza(VERSION)
qa.setStyle("Fusion")
qa.setStyleSheet(A.STYLE)
qa.setFont(QFont("Segoe UI", 10))
win = A.MainWindow(Settings(), Store())
win.show()
qa.processEvents()


def go():
    win.grab().save(os.path.join(out, "vuota.png"))
    for name, mk, setup in (
            ("aggiungi-gmail", lambda: A.AccountDialog(win, win.store), lambda d: d.email.setText("pietro@gmail.com")),
            ("aggiungi-outlook", lambda: A.AccountDialog(win, win.store), lambda d: d.email.setText("pietro@hotmail.it")),
            ("aggiungi-altro", lambda: A.AccountDialog(win, win.store), lambda d: d.email.setText("info@miaditta.it")),
            ("benvenuto", lambda: BenvenutoDialog(qa.licenza, "tk-iscrizioni", URL_SORGENTE, win, A.render_icon(104),
                                                  A.BENVENUTO_RIGHE), lambda d: None),
            ("informazioni", lambda: InformazioniDialog(qa.licenza, "tk-iscrizioni", VERSION, "A cosa sei iscritto",
                                                        A.render_icon(136), "#7c3aed", url_sorgente=URL_SORGENTE,
                                                        cartella_licenze=cartella_licenze(), parent=win),
             lambda d: None),
            ("licenze", lambda: LicenzeDialog("tk-iscrizioni", VERSION, URL_SORGENTE, cartella_licenze(), win),
             lambda d: None)):
        d = mk()
        setup(d)
        d.show()
        qa.processEvents()
        d.adjustSize()
        qa.processEvents()
        d.grab().save(os.path.join(out, name + ".png"))
        d.close()
    qa.quit()


QTimer.singleShot(600, go)
qa.exec()
print("fatto")
