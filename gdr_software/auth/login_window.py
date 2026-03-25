"""
auth/login_window.py — Finestra di login e registrazione
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
from lingua.gestore import t


class LoginWindow(QDialog):

    login_riuscito = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("app_titolo") + " — " + t("login_titolo"))
        self.setMinimumWidth(380)
        self.setModal(True)
        self._costruisci_ui()

    def _costruisci_ui(self):
        layout_principale = QVBoxLayout(self)
        layout_principale.setSpacing(12)
        layout_principale.setContentsMargins(20, 20, 20, 20)

        titolo = QLabel(t("app_titolo"))
        titolo.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        titolo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_principale.addWidget(titolo)

        self.tabs = QTabWidget()
        layout_principale.addWidget(self.tabs)

        self.tabs.addTab(self._crea_scheda_login(), t("accedi"))
        self.tabs.addTab(self._crea_scheda_registrazione(), t("registrati"))

    def _crea_scheda_login(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel(t("username") + ":"))
        self.campo_username_login = QLineEdit()
        self.campo_username_login.setPlaceholderText(t("username"))
        layout.addWidget(self.campo_username_login)

        layout.addWidget(QLabel(t("password") + ":"))
        self.campo_password_login = QLineEdit()
        self.campo_password_login.setPlaceholderText(t("password"))
        self.campo_password_login.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.campo_password_login)

        btn_accedi = QPushButton(t("accedi"))
        btn_accedi.setMinimumHeight(36)
        btn_accedi.clicked.connect(self._gestisci_login)
        layout.addWidget(btn_accedi)

        self.campo_password_login.returnPressed.connect(self._gestisci_login)

        layout.addStretch()
        return widget

    def _crea_scheda_registrazione(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel(t("username") + ":"))
        self.campo_username_reg = QLineEdit()
        self.campo_username_reg.setPlaceholderText(t("username"))
        layout.addWidget(self.campo_username_reg)

        layout.addWidget(QLabel(t("password") + ":"))
        self.campo_password_reg = QLineEdit()
        self.campo_password_reg.setPlaceholderText(t("password"))
        self.campo_password_reg.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.campo_password_reg)

        layout.addWidget(QLabel(t("conferma_password") + ":"))
        self.campo_conferma = QLineEdit()
        self.campo_conferma.setPlaceholderText(t("conferma_password"))
        self.campo_conferma.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.campo_conferma)

        layout.addWidget(QLabel(t("ruolo") + ":"))
        self.combo_ruolo = QComboBox()
        self.combo_ruolo.addItem(t("ruolo_player"), userData="player")
        self.combo_ruolo.addItem(t("ruolo_dm"),     userData="dm")
        layout.addWidget(self.combo_ruolo)

        nota_dm = QLabel("ℹ️ " + t("ruolo_dm") + ".")
        nota_dm.setWordWrap(True)
        nota_dm.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(nota_dm)

        btn_registrati = QPushButton(t("crea_account"))
        btn_registrati.setMinimumHeight(36)
        btn_registrati.clicked.connect(self._gestisci_registrazione)
        layout.addWidget(btn_registrati)

        layout.addStretch()
        return widget

    def _gestisci_login(self):
        username = self.campo_username_login.text()
        password = self.campo_password_login.text()

        if not username or not password:
            self._mostra_errore(t("campo_obbligatorio"))
            return

        successo, messaggio, dati_utente = login(username, password)

        if not successo:
            self._mostra_errore(messaggio)
            self.campo_password_login.clear()
            return

        imposta_utente_corrente(dati_utente)
        self.login_riuscito.emit(dati_utente)
        self.accept()

    def _gestisci_registrazione(self):
        username = self.campo_username_reg.text()
        password = self.campo_password_reg.text()
        conferma = self.campo_conferma.text()
        ruolo    = self.combo_ruolo.currentData()

        if password != conferma:
            self._mostra_errore(t("password_non_coincidono"))
            self.campo_conferma.clear()
            return

        successo, messaggio = registra_utente(username, password, ruolo)

        if not successo:
            self._mostra_errore(messaggio)
            return

        QMessageBox.information(
            self,
            t("account_creato"),
            t("account_creato_msg").format(u=username)
        )

        self.campo_username_login.setText(username)
        self.campo_password_login.setFocus()
        self.tabs.setCurrentIndex(0)

        self.campo_username_reg.clear()
        self.campo_password_reg.clear()
        self.campo_conferma.clear()

    def _mostra_errore(self, messaggio: str):
        QMessageBox.warning(self, t("errore"), messaggio)
