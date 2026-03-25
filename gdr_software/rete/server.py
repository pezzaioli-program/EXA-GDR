"""
rete/server.py — WebSocket Server (avviato dal DM)
"""

import asyncio
import json
import websockets
from websockets.server import WebSocketServerProtocol
from config import WS_PORTA, WS_HOST_DEFAULT


class ServerGDR:
    def __init__(self, sessione):
        self.sessione   = sessione
        self.clients:   dict[int, WebSocketServerProtocol] = {}  # utente_id → ws
        self._server    = None

    async def avvia(self, host: str = WS_HOST_DEFAULT, porta: int = WS_PORTA):
        self._server = await websockets.serve(
            self._gestisci_client, host, porta
        )
        print(f"[SERVER] In ascolto su {host}:{porta}")
        await self._server.wait_closed()

    def avvia_in_thread(self, host: str = WS_HOST_DEFAULT, porta: int = WS_PORTA):
        import threading
        def _run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.avvia(host, porta))
        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def ferma(self):
        if self._server:
            self._server.close()

    async def _gestisci_client(self, ws: WebSocketServerProtocol, path: str):
        utente_id = None
        try:
            async for messaggio_raw in ws:
                msg = json.loads(messaggio_raw)
                utente_id = msg.get("utente_id")

                if msg["tipo"] == "connetti":
                    self.clients[utente_id] = ws
                    await self._broadcast({
                        "tipo":     "giocatore_connesso",
                        "username": msg.get("username"),
                    }, escludi=utente_id)
                    await self._invia_stato_completo(ws)

                elif msg["tipo"] == "muovi_token":
                    ok, err = self.sessione.muovi_token(
                        utente_id, msg["q"], msg["r"], utente_id)
                    if ok:
                        await self._broadcast({
                            "tipo":      "token_mosso",
                            "utente_id": utente_id,
                            "q":         msg["q"],
                            "r":         msg["r"],
                        })
                    else:
                        await ws.send(json.dumps({"tipo": "errore", "messaggio": err}))

                elif msg["tipo"] == "dado_lanciato":
                    await self._broadcast({
                        "tipo":        "dado_lanciato",
                        "utente_id":   utente_id,
                        "username":    msg.get("username"),
                        "descrizione": msg.get("descrizione"),
                    })

                elif msg["tipo"] == "fine_turno":
                    if self.sessione.combattimento:
                        self.sessione.combattimento.termina_turno(utente_id)
                        await self._broadcast({
                            "tipo":          "turno_avanzato",
                            "lista_init":    self.sessione.combattimento.lista_iniziativa(),
                            "turno_corrente": self.sessione.combattimento.chi_agisce_ora(),
                        })

                elif msg["tipo"] == "aggiorna_mappa":
                    await self._broadcast(msg, escludi=utente_id)

                elif msg["tipo"] == "ping":
                    await ws.send(json.dumps({"tipo": "pong"}))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if utente_id and utente_id in self.clients:
                del self.clients[utente_id]
                await self._broadcast({
                    "tipo":      "giocatore_disconnesso",
                    "utente_id": utente_id,
                })

    async def _broadcast(self, messaggio: dict, escludi: int = None):
        dati = json.dumps(messaggio, ensure_ascii=False)
        for uid, ws in list(self.clients.items()):
            if uid != escludi:
                try:
                    await ws.send(dati)
                except Exception:
                    pass

    async def invia_a(self, utente_id: int, messaggio: dict):
        ws = self.clients.get(utente_id)
        if ws:
            try:
                await ws.send(json.dumps(messaggio, ensure_ascii=False))
            except Exception:
                pass

    async def _invia_stato_completo(self, ws: WebSocketServerProtocol):
        stato = self.sessione.stato_per_player(0)
        await ws.send(json.dumps({"tipo": "stato_completo", "stato": stato},
                                  ensure_ascii=False))

    async def notifica_combattimento_avviato(self):
        if self.sessione.combattimento:
            await self._broadcast({
                "tipo":       "combattimento_avviato",
                "lista_init": self.sessione.combattimento.lista_iniziativa(),
                "turno":      self.sessione.combattimento.chi_agisce_ora(),
            })

    async def notifica_pf_aggiornati(self, utente_id: int, pf: int):
        await self._broadcast({
            "tipo":      "pf_aggiornati",
            "utente_id": utente_id,
            "pf":        pf,
        })

    async def notifica_morte(self, utente_id: int, nome: str):
        await self._broadcast({
            "tipo":      "personaggio_morto",
            "utente_id": utente_id,
            "nome":      nome,
        })
