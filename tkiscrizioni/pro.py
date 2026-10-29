"""Licenza di tk-iscrizioni: software libero (AGPL-3.0), tutte le funzioni per tutti.

Resta solo ciò che serve alla libreria comune (tk_licenza): consenso alle statistiche, benvenuto,
invito al caffè e pulsante «Offrimi un caffè». Niente chiavi, niente Pro.
"""
import os
import sys

from PySide6.QtWidgets import QApplication


def crea_licenza(versione):
    """La licenza sta nella cartella dell'utente, non accanto al programma: tk-iscrizioni gira anche da pennetta."""
    try:
        from tkiscrizioni.tk_licenza import Licenza
        if os.environ.get("TKISCR_DATA"):
            base = os.environ["TKISCR_DATA"]
        elif sys.platform == "darwin":
            base = os.path.expanduser("~/Library/Application Support")
        elif sys.platform.startswith("linux"):
            from tkiscrizioni import tk_linux
            base = tk_linux.xdg_data_home()  # ~/.local/share/tk-iscrizioni, la stessa cartella dei dati
        else:
            base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return Licenza("tk-iscrizioni", versione, os.path.join(base, "tk-iscrizioni"))
    except Exception:
        return None


def licenza():
    return getattr(QApplication.instance(), "licenza", None)


def _logo():
    from tkiscrizioni.app import render_icon
    return render_icon(104)


def benvenuto(parent=None, righe_extra=()):
    """Prima apertura (una volta sola): software libero, privacy e consenso alle statistiche."""
    try:
        from tkiscrizioni import URL_SORGENTE
        from tkiscrizioni.tk_licenza_qt import benvenuto as mostra
        mostra(licenza(), "tk-iscrizioni", URL_SORGENTE, parent=parent, logo=_logo(), righe_extra=righe_extra)
    except Exception:
        pass


def invito(parent=None, puo_mostrare=None):
    """Invito al caffè all'avvio: la prima volta e poi al massimo una volta al mese (vedi tk_licenza_qt)."""
    try:
        from tkiscrizioni.tk_licenza_qt import invito_caffe
        invito_caffe(licenza(), "tk-iscrizioni", parent, _logo(), puo_mostrare)
    except Exception:
        pass


def pulsante_caffe(nome_oggetto=""):
    from tkiscrizioni.tk_licenza_qt import pulsante_caffe as crea
    return crea(licenza(), nome_oggetto=nome_oggetto)


def casella_statistiche():
    from tkiscrizioni.tk_licenza_qt import casella_statistiche as crea
    return crea(licenza())
