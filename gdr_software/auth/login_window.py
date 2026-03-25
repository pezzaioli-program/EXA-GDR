"""
auth/login_window.py — Finestra di login e registrazione
=========================================================
Questo file sa COME mostrare il form di login/registrazione.
NON sa come verificare le credenziali (quello è registro.py).
NON sa cosa fare dopo il login (quello è main.py).

Sa solo: costruire la UI, raccogliere l'input, chiamare registro.py
e comunicare il risultato a chi l'ha aperta.

Tecnologia: PyQt6
  - QDialog: finestra modale (blocca le altre finestre mentre è aperta)
  - QLineEdit: campo di testo
  - QPushButton: pulsante
  - QLabel: testo statico
  - Signal/Slot: sistema di eventi di PyQt
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton,
    QComboBox, QMessageBox, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from auth.registro import login, registra_utente
from auth.sessione_utente import imposta_utente_corrente


class LoginWindow(QDialog):
    """
    Finestra di login/registrazione.

    Usa QTabWidget per avere due schede: "Accedi" e "Registrati".
    Così l'utente non deve navigare tra finestre diverse.

    Signal login_riuscito: viene emesso quando il login va a buon fine.
    main.py è in ascolto su questo signal e sa cosa fare dopo.

    Perché un signal invece di chiamare direttamente main.py?
    Perché LoginWindow non deve sapere cosa c'è "fuori" di lei.
    Il signal è un modo per dire "è successa una cosa" senza sapere
    chi la gestirà. Questo rende LoginWindow riutilizzabile e testabile.
    """

    # Definizione del signal: trasporta un dizionario con i dati utente
    # pyqtSignal(dict) significa "questo signal porta con sé un dizionario"
    login_riuscito = pyqtSignal(dict)

    def __init__(self, parent=None):
        # super().__init__(parent) inizializza la classe padre QDialog.
        # Devi sempre chiamarla prima di fare qualsiasi altra cosa in __init__.
        super().__init__(parent)

        self.setWindowTitle("GDR Map Creator — Accesso")
        self.setMinimumWidth(380)
        self.setModal(True)   # blocca le altre finestre mentre è aperta

        self._costruisci_ui()

    # ── Costruzione UI ─────────────────────────────────────────────────────────

    def _costruisci_ui(self):
        """
        Costruisce l'interfaccia grafica.

        Layout in PyQt: i widget non hanno una posizione fissa in pixel.
        Si usano i "layout" che li dispongono automaticamente.
          QVBoxLayout → impila i widget verticalmente (V = Vertical)
          QHBoxLayout → affianca i widget orizzontalmente (H = Horizontal)

        I layout si annidano: puoi mettere un HLayout dentro un VLayout.
        """
        layout_principale = QVBoxLayout(self)
        layout_principale.setSpacing(12)
        layout_principale.setContentsMargins(20, 20, 20, 20)

        # Titolo in cima
        titolo = QLabel("GDR Map Creator")
        titolo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principale.addWidget(titolo)

        # QTabWidget: il contenitore con le schede "Accedi" / "Registrati"
        self.tabs = QTabWidget()
        layout_principale.addWidget(self.tabs)

        # Aggiungiamo le due schede
        self.tabs.addTab(self._crea_scheda_login(), "Accedi")
        self.tabs.addTab(self._crea_scheda_registrazione(), "Registrati")

    def _crea_scheda_login(self) -> QWidget:
        """
        Crea il contenuto della scheda 'Accedi'.
        Restituisce un QWidget che verrà inserito nel tab.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Campo username
        layout.addWidget(QLabel("Nome utente:"))
        self.campo_username_login = QLineEdit()
        self.campo_username_login.setPlaceholderText("Inserisci il tuo nome utente")
        layout.addWidget(self.campo_username_login)

        # Campo password
        layout.addWidget(QLabel("Password:"))
        self.campo_password_login = QLineEdit()
        self.campo_password_login.setPlaceholderText("Inserisci la tua password")
        # setEchoMode(Password): mostra *** invece dei caratteri
        self.campo_password_login.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.campo_password_login)

        # Pulsante accedi
        btn_accedi = QPushButton("Accedi")
        btn_accedi.setMinimumHeight(36)
        # .clicked è il signal, .connect(self._gestisci_login) è lo slot
        btn_accedi.clicked.connect(self._gestisci_login)
        layout.addWidget(btn_accedi)

        # Premere Invio nel campo password = click su "Accedi"
        # returnPressed è un signal emesso quando si preme Invio
        self.campo_password_login.returnPressed.connect(self._gestisci_login)

        layout.addStretch()   # spazio elastico in fondo (spinge tutto in alto)
        return widget

    def _crea_scheda_registrazione(self) -> QWidget:
        """Crea il contenuto della scheda 'Registrati'."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Campo username
        layout.addWidget(QLabel("Nome utente:"))
        self.campo_username_reg = QLineEdit()
        self.campo_username_reg.setPlaceholderText("Scegli un nome utente (min. 3 caratteri)")
        layout.addWidget(self.campo_username_reg)

        # Campo password
        layout.addWidget(QLabel("Password:"))
        self.campo_password_reg = QLineEdit()
        self.campo_password_reg.setPlaceholderText("Scegli una password (min. 8 caratteri)")
        self.campo_password_reg.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.campo_password_reg)

        # Campo conferma password
        layout.addWidget(QLabel("Conferma password:"))
        self.campo_conferma = QLineEdit()
        self.campo_conferma.setPlaceholderText("Ripeti la password")
        self.campo_conferma.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.campo_conferma)

        # Selezione ruolo
        layout.addWidget(QLabel("Ruolo:"))
        self.combo_ruolo = QComboBox()
        # addItem(testo_visibile, dato_interno)
        # Il dato interno (userData) è quello che usiamo nel codice
        # Il testo visibile è quello che vede l'utente
        self.combo_ruolo.addItem("Player (gratuito)", userData="player")
        self.combo_ruolo.addItem("Dungeon Master (abbonamento richiesto)", userData="dm")
        layout.addWidget(self.combo_ruolo)

        # Nota informativa per il DM
        nota_dm = QLabel(
            "ℹ️ Il ruolo DM richiede un abbonamento attivo.\n"
            "Potrai attivarlo dopo la registrazione."
        )
        nota_dm.setWordWrap(True)
        nota_dm.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(nota_dm)

        # Pulsante registrati
        btn_registrati = QPushButton("Crea account")
        btn_registrati.setMinimumHeight(36)
        btn_registrati.clicked.connect(self._gestisci_registrazione)
        layout.addWidget(btn_registrati)

        layout.addStretch()
        return widget

    # ── Gestione eventi ────────────────────────────────────────────────────────

    def _gestisci_login(self):
        """
        Chiamata quando l'utente clicca 'Accedi' o preme Invio.

        Flusso:
          1. Legge i campi
          2. Chiama registro.login()
          3. Se ok → imposta utente corrente → emette signal → chiude
          4. Se errore → mostra messaggio
        """
        username = self.campo_username_login.text()
        password = self.campo_password_login.text()

        # Validazione minima lato UI: non mandare richieste vuote
        if not username or not password:
            self._mostra_errore("Inserisci nome utente e password.")
            return

        successo, messaggio, dati_utente = login(username, password)

        if not successo:
            self._mostra_errore(messaggio)
            # Pulisci il campo password per sicurezza
            self.campo_password_login.clear()
            return

        # Login riuscito:
        # 1. Salva l'utente nello stato globale
        imposta_utente_corrente(dati_utente)

        # 2. Emetti il signal — main.py lo riceverà e aprirà la dashboard
        self.login_riuscito.emit(dati_utente)

        # 3. Chiudi la finestra di login
        self.accept()   # accept() chiude un QDialog con esito positivo

    def _gestisci_registrazione(self):
        """
        Chiamata quando l'utente clicca 'Crea account'.

        Flusso:
          1. Legge e valida i campi lato UI (le password coincidono?)
          2. Chiama registro.registra_utente()
          3. Se ok → mostra conferma → passa alla scheda login
          4. Se errore → mostra messaggio
        """
        username = self.campo_username_reg.text()
        password = self.campo_password_reg.text()
        conferma = self.campo_conferma.text()

        # currentData() restituisce il dato interno della voce selezionata
        # cioè "player" o "dm" — non il testo visibile
        ruolo = self.combo_ruolo.currentData()

        # Validazione lato UI: le password coincidono?
        # Questo controllo è fatto qui e non in registro.py perché
        # "le password coincidono" è un concetto di UI, non di business logic.
        # registro.py non sa che ci sono due campi password nel form.
        if password != conferma:
            self._mostra_errore("Le password non coincidono.")
            self.campo_conferma.clear()
            return

        successo, messaggio = registra_utente(username, password, ruolo)

        if not successo:
            self._mostra_errore(messaggio)
            return

        # Registrazione riuscita: mostra conferma e vai alla scheda login
        QMessageBox.information(
            self,
            "Account creato",
            f"Account '{username}' creato con successo!\nAccedi con le tue credenziali."
        )

        # Precompila il campo username nel login con quello appena registrato
        self.campo_username_login.setText(username)
        self.campo_password_login.setFocus()

        # Torna alla scheda "Accedi" (indice 0)
        self.tabs.setCurrentIndex(0)

        # Pulisci i campi di registrazione
        self.campo_username_reg.clear()
        self.campo_password_reg.clear()
        self.campo_conferma.clear()

    # ── Utilità ────────────────────────────────────────────────────────────────

    def _mostra_errore(self, messaggio: str):
        """
        Mostra una finestra di dialogo con il messaggio di errore.
        QMessageBox.warning = finestra con icona di avviso.
        """
        QMessageBox.warning(self, "Errore", messaggio)
