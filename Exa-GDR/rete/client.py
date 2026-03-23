"""
rete/client.py — WebSocket Client (usato da Player e DM)
"""

import asyncio
import json
import threading
import websockets
from PyQt6.QtCore import QObject, pyqtSignal
from config import WS_PORTA, WS_HOST_DEFAULT, WS_TIMEOUT, WS_PING_INTERVALLO


class ClientGDR(QObject):
    """
    Client WebSocket che gira in un thread separato.
    Emette signal PyQt quando arrivano messaggi dal server —
    così la UI può aggiornarsi in modo sicuro dal thread principale.
    """

    # Signal emessi quando arrivano messaggi dal server
    connesso            = pyqtSignal()
    disconnesso         = pyqtSignal()
    errore_connessione  = pyqtSignal(str)
    token_mosso         = pyqtSignal(int, int, int)          # utente_id, q, r
    dado_lanciato       = pyqtSignal(str, str)               # username, descrizione
    turno_avanzato      = pyqtSignal(list, dict)             # lista_init, turno_corrente
    combattimento_avviato = pyqtSignal(list, dict)           # lista_init, turno
    pf_aggiornati       = pyqtSignal(int, int)               # utente_id, pf
    personaggio_morto   = pyqtSignal(int, str)               # utente_id, nome
    stato_ricevuto      = pyqtSignal(dict)                   # stato completo
    giocatore_connesso  = pyqtSignal(str)                    # username
    giocatore_disconnesso = pyqtSignal(int)                  # utente_id
    mappa_aggiornata    = pyqtSignal(dict)                   # dati mappa

    def __init__(self, utente_id: int, username: str, parent=None):
        super().__init__(parent)
        self.utente_id  = utente_id
        self.username   = username
        self._ws        = None
        self._loop      = None
        self._thread    = None
        self._connesso  = False

    # ── Connessione ───────────────────────────────────────────────────────────

    def connetti(self, host: str = WS_HOST_DEFAULT, porta: int = WS_PORTA):
        self._loop   = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_until_complete,
            args=(self._loop_principale(host, porta),),
            daemon=True,
        )
        self._thread.start()

    def disconnetti(self):
        if self._ws and self._loop:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)

    # ── Loop principale ───────────────────────────────────────────────────────

    async def _loop_principale(self, host: str, porta: int):
        uri = f"ws://{host}:{porta}"
        try:
            async with websockets.connect(uri, open_timeout=WS_TIMEOUT) as ws:
                self._ws       = ws
                self._connesso = True
                self.connesso.emit()

                # Registra il client sul server
                await self._invia({"tipo": "connetti",
                                   "utente_id": self.utente_id,
                                   "username":  self.username})

                # Avvia il ping periodico
                asyncio.ensure_future(self._loop_ping())

                # Ascolta i messaggi in arrivo
                async for raw in ws:
                    await self._gestisci_messaggio(json.loads(raw))

        except (OSError, websockets.exceptions.WebSocketException) as e:
            self.errore_connessione.emit(str(e))
        finally:
            self._connesso = False
            self.disconnesso.emit()

    async def _loop_ping(self):
        while self._connesso and self._ws:
            await asyncio.sleep(WS_PING_INTERVALLO)
            try:
                await self._invia({"tipo": "ping"})
            except Exception:
                break

    # ── Ricezione messaggi ────────────────────────────────────────────────────

    async def _gestisci_messaggio(self, msg: dict):
        tipo = msg.get("tipo")

        if tipo == "token_mosso":
            self.token_mosso.emit(msg["utente_id"], msg["q"], msg["r"])

        elif tipo == "dado_lanciato":
            self.dado_lanciato.emit(msg["username"], msg["descrizione"])

        elif tipo == "turno_avanzato":
            self.turno_avanzato.emit(msg["lista_init"], msg["turno_corrente"])

        elif tipo == "combattimento_avviato":
            self.combattimento_avviato.emit(msg["lista_init"], msg["turno"])

        elif tipo == "pf_aggiornati":
            self.pf_aggiornati.emit(msg["utente_id"], msg["pf"])

        elif tipo == "personaggio_morto":
            self.personaggio_morto.emit(msg["utente_id"], msg["nome"])

        elif tipo == "stato_completo":
            self.stato_ricevuto.emit(msg["stato"])

        elif tipo == "giocatore_connesso":
            self.giocatore_connesso.emit(msg["username"])

        elif tipo == "giocatore_disconnesso":
            self.giocatore_disconnesso.emit(msg["utente_id"])

        elif tipo == "aggiorna_mappa":
            self.mappa_aggiornata.emit(msg)

        elif tipo == "errore":
            self.errore_connessione.emit(msg.get("messaggio", "Errore sconosciuto"))

    # ── Invio messaggi ────────────────────────────────────────────────────────

    def _invia_sync(self, messaggio: dict):
        if self._loop and self._connesso:
            asyncio.run_coroutine_threadsafe(
                self._invia(messaggio), self._loop)

    async def _invia(self, messaggio: dict):
        if self._ws:
            await self._ws.send(json.dumps(messaggio, ensure_ascii=False))

    def invia_movimento(self, q: int, r: int):
        self._invia_sync({"tipo": "muovi_token",
                          "utente_id": self.utente_id, "q": q, "r": r})

    def invia_dado(self, descrizione: str):
        self._invia_sync({"tipo": "dado_lanciato",
                          "utente_id": self.utente_id,
                          "username":  self.username,
                          "descrizione": descrizione})

    def invia_fine_turno(self):
        self._invia_sync({"tipo": "fine_turno",
                          "utente_id": self.utente_id})

    def invia_aggiornamento_mappa(self, dati: dict):
        dati["tipo"]      = "aggiorna_mappa"
        dati["utente_id"] = self.utente_id
        self._invia_sync(dati)

    @property
    def e_connesso(self) -> bool:
        return self._connesso
