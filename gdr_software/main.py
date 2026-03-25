"""
main.py — Punto di ingresso dell'applicazione GDR
==================================================
Questo è il primo file che viene eseguito.
Ha UNA responsabilità: orchestrare l'avvio.

Cosa fa:
  1. Inizializza il database (crea le tabelle se non esistono)
  2. Crea l'applicazione PyQt
  3. Mostra la finestra di login
  4. Quando il login riesce, apre la dashboard giusta (DM o Player)
  5. Gestisce la chiusura pulita

Cosa NON fa:
  - Non contiene logica di autenticazione (quella è in auth/)
  - Non costruisce UI (quella è in dashboard/ e auth/)
  - Non tocca il database direttamente (quello è in database/)

Perché è così corto?
  Un main.py lungo è un segnale che la logica è nel posto sbagliato.
  Se hai bisogno di capire "come funziona il login", non guardi qui —
  guardi auth/. main.py dice solo QUANDO e in CHE ORDINE le cose accadono.
"""

import sys
import os

# Garantisce che il working directory sia sempre la cartella del progetto,
# indipendentemente da dove viene lanciato lo script su Windows.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont

from config import APP_TITOLO, APP_VERSIONE
from database.db import inizializza_db
from auth.login_window import LoginWindow
from auth.sessione_utente import utente_corrente, e_dm, logout


def avvia_dashboard(dati_utente: dict, app: QApplication):
    """
    Apre la dashboard giusta in base al ruolo dell'utente.

    Viene chiamata dal signal login_riuscito di LoginWindow.
    Riceve i dati utente direttamente dal signal.

    Perché importiamo le dashboard QUI e non in cima al file?
    Import ritardato: le dashboard importano molti moduli (PyQt, pygame...).
    Importarle solo quando servono velocizza l'avvio — durante il login
    non hai ancora bisogno della dashboard. Su progetti piccoli non fa
    differenza, ma è un'abitudine utile da sviluppare.
    """
    if e_dm():
        from dashboard.dashboard_dm import DashboardDM
        finestra = DashboardDM()
    else:
        from dashboard.dashboard_player import DashboardPlayer
        finestra = DashboardPlayer()

    finestra.show()

    # Collega il signal di logout della dashboard alla funzione di cleanup.
    # Quando il DM o il Player clicca "Esci", la dashboard emette logout_richiesto.
    # Noi rispondiamo cancellando la sessione e mostrando di nuovo il login.
    finestra.logout_richiesto.connect(lambda: gestisci_logout(finestra, app))


def gestisci_logout(finestra_corrente, app: QApplication):
    """
    Gestisce il logout dell'utente.

    Flusso:
      1. Cancella i dati dell'utente corrente
      2. Chiude la dashboard
      3. Mostra di nuovo il login

    Perché non chiudiamo l'app e la riavviamo?
    Perché sarebbe un'esperienza utente pessima. L'utente si aspetta
    di poter fare login con un altro account senza riaprire il programma.
    Distruggere e ricreare le finestre è il modo corretto in PyQt.
    """
    logout()                    # cancella utente_corrente
    finestra_corrente.close()   # chiude dashboard
    mostra_login(app)           # riapre il login


def mostra_login(app: QApplication):
    """
    Crea e mostra la finestra di login.
    Può essere chiamata sia all'avvio che dopo un logout.
    """
    login_window = LoginWindow()

    # Quando il login riesce, chiama avvia_dashboard.
    # La lambda serve per passare anche 'app' come argomento aggiuntivo,
    # perché il signal porta solo dati_utente ma avvia_dashboard ha bisogno
    # anche di app.
    login_window.login_riuscito.connect(
        lambda dati: avvia_dashboard(dati, app)
    )

    login_window.exec()   # exec() per i QDialog = mostra e aspetta che si chiuda


def main():
    """
    Funzione principale — punto di partenza dell'esecuzione.

    Convenzione Python: il codice "reale" va dentro main(), non a livello
    del modulo. Questo permette di importare main.py da altri file
    (es. per i test) senza eseguire tutto il programma.
    """

    # ── 1. Inizializza il database ───────────────────────────────────────────
    # Crea le tabelle se non esistono. Sicuro da chiamare ogni volta —
    # usa "CREATE TABLE IF NOT EXISTS" quindi non sovrascrive dati esistenti.
    try:
        inizializza_db()
    except Exception as e:
        # Se il database non si inizializza, non possiamo andare avanti.
        # Mostriamo un errore PRIMA di creare la QApplication non funziona,
        # quindi usiamo print e usciamo.
        print(f"[ERRORE CRITICO] Impossibile inizializzare il database: {e}")
        sys.exit(1)   # codice 1 = uscita con errore

    # ── 2. Crea l'applicazione PyQt ──────────────────────────────────────────
    # QApplication deve essere creata UNA SOLA VOLTA prima di qualsiasi
    # widget. Gestisce il loop eventi, i font, il tema grafico.
    # sys.argv passa gli argomenti da riga di comando a PyQt
    # (es. per opzioni di debug).
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITOLO)
    app.setApplicationVersion(APP_VERSIONE)

    # Font di default per tutta l'applicazione
    font = QFont("Arial", 11)
    app.setFont(font)

    # Tema scuro minimale tramite stylesheet CSS
    # PyQt accetta CSS (quasi) standard per lo stile dei widget.
    # Questo è un tema base — in futuro puoi caricare un file .qss esterno.
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
        QLineEdit:focus, QTextEdit:focus {
            border-color: #8080c0;
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
        QPushButton:pressed {
            background-color: #4a4a80;
        }
        QTabWidget::pane {
            border: 1px solid #555570;
        }
        QTabBar::tab {
            background-color: #3a3a4a;
            padding: 8px 20px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #5a5a90;
        }
        QLabel {
            color: #cccccc;
        }
        QMessageBox {
            background-color: #282832;
        }
    """)

    # ── 3. Mostra il login ───────────────────────────────────────────────────
    mostra_login(app)

    # ── 4. Avvia il loop eventi PyQt ─────────────────────────────────────────
    # app.exec() blocca qui finché tutte le finestre sono chiuse.
    # Restituisce 0 se tutto è andato bene, altro in caso di errore.
    codice_uscita = app.exec()

    # ── 5. Cleanup e uscita ──────────────────────────────────────────────────
    print(f"[APP] Chiusura con codice {codice_uscita}")
    sys.exit(codice_uscita)


# ── Entry point ───────────────────────────────────────────────────────────────
# Questa è la convenzione Python per dire "esegui main() solo se questo
# file viene eseguito direttamente, non se viene importato".
#
# Perché serve? Se un altro file fa "import main", Python esegue tutto
# il codice a livello di modulo. Senza questo if, avvierebbe l'intera
# app ogni volta che qualcuno importa main.py — un disastro.
#
# Con if __name__ == "__main__": il codice dentro viene eseguito SOLO
# quando scrivi "python main.py" nel terminale.
if __name__ == "__main__":
    main()
