"""
main.py — Punto di ingresso dell'applicazione GDR
==================================================
Questo è il primo file che viene eseguito.
"""

import sys
import os

# Garantisce che il working directory sia sempre la cartella del progetto
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (QApplication, QMessageBox, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config import APP_TITOLO, APP_VERSIONE
from database.db import inizializza_db
from auth.login_window import LoginWindow
from auth.sessione_utente import utente_corrente, e_dm, logout

def mostra_scelta_lingua() -> str:
    """
    Mostra la finestra di scelta lingua al primo avvio.
    """
    from database.db import leggi_uno, esegui

    # Controlla se c'è già una preferenza salvata
    riga = leggi_uno("SELECT valore FROM impostazioni WHERE chiave='lingua'")
    if riga:
        return riga["valore"]

    # Prima volta: mostra la finestra di scelta
    dialog = QDialog()
    dialog.setWindowTitle("Language / Lingua")
    dialog.setFixedSize(360, 220)
    # Nasconde il pulsante X
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

    layout = QVBoxLayout(dialog)
    layout.setSpacing(16)
    layout.setContentsMargins(30, 30, 30, 30)

    lbl = QLabel("Scegli la lingua / Choose your language")
    lbl.setFont(QFont("Arial", 13, QFont.Weight.Bold))
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)

    lingua_scelta = ["it"]

    riga_btn = QHBoxLayout()
    riga_btn.setSpacing(12)
    
    btn_it = QPushButton("🇮🇹  Italiano")
    btn_it.setMinimumHeight(48)
    btn_it.setFont(QFont("Arial", 13))
    btn_it.setStyleSheet("background-color: #5a5a90; border-radius: 6px;")

    btn_en = QPushButton("🇬🇧  English")
    btn_en.setMinimumHeight(48)
    btn_en.setFont(QFont("Arial", 13))

    def scegli(codice):
        lingua_scelta[0] = codice
        if codice == "it":
            btn_it.setStyleSheet("background-color: #5a5a90; border-radius: 6px;")
            btn_en.setStyleSheet("")
        else:
            btn_en.setStyleSheet("background-color: #5a5a90; border-radius: 6px;")
            btn_it.setStyleSheet("")

    btn_it.clicked.connect(lambda: scegli("it"))
    btn_en.clicked.connect(lambda: scegli("en"))
    
    riga_btn.addWidget(btn_it)
    riga_btn.addWidget(btn_en)
    layout.addLayout(riga_btn)

    btn_ok = QPushButton("Continua / Continue")
    btn_ok.setMinimumHeight(36)
    btn_ok.clicked.connect(dialog.accept)
    layout.addWidget(btn_ok)

    dialog.exec()

    codice = lingua_scelta[0]
    esegui("INSERT OR REPLACE INTO impostazioni (chiave, valore) VALUES (?,?)", ("lingua", codice))
    return codice


def avvia_dashboard(dati_utente: dict, app: QApplication):
    """Apre la dashboard giusta in base al ruolo dell'utente."""
    if e_dm():
        from dashboard.dashboard_dm import DashboardDM
        finestra = DashboardDM()
    else:
        from dashboard.dashboard_player import DashboardPlayer
        finestra = DashboardPlayer()

    finestra.show()
    finestra.logout_richiesto.connect(lambda: gestisci_logout(finestra, app))


def gestisci_logout(finestra_corrente, app: QApplication):
    """Gestisce il logout dell'utente."""
    logout()
    finestra_corrente.close()
    mostra_login(app)


def mostra_login(app: QApplication):
    """Crea e mostra la finestra di login."""
    login_window = LoginWindow()
    login_window.login_riuscito.connect(
        lambda dati: avvia_dashboard(dati, app)
    )
    login_window.exec()


def main():
    """Funzione principale dell'applicazione."""
    
    # 1. Inizializza il database
    try:
        inizializza_db()
    except Exception as e:
        print(f"[ERRORE CRITICO] Impossibile inizializzare il database: {e}")
        sys.exit(1)

    # 2. Crea l'applicazione PyQt
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITOLO)
    app.setApplicationVersion(APP_VERSIONE)

    # Gestione Lingua
    from lingua.gestore import imposta_lingua
    codice_lingua = mostra_scelta_lingua()
    imposta_lingua(codice_lingua)

    # Font e Stile
    font = QFont("Arial", 11)
    app.setFont(font)
    app.setStyleSheet("""
        QWidget {
            background-color: #282832;
            color: #ffffff;
            font-family: Arial;
        }
        QLineEdit, QTextEdit, QComboBox {
            background-color: #3a3a4a;
            border: 1px solid #555570;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
        }
        QPushButton {
            background-color: #5a5a90;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            color: #ffffff;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #6a6aa0;
        }
        QTabBar::tab:selected {
            background-color: #5a5a90;
        }
        QLabel {
            color: #cccccc;
        }
    """)

    # 3. Mostra il login
    mostra_login(app)

    # 4. Loop eventi
    codice_uscita = app.exec()
    print(f"[APP] Chiusura con codice {codice_uscita}")
    sys.exit(codice_uscita)


if __name__ == "__main__":
    main()
