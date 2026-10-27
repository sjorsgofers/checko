"""
TV Remote server: bedient een Android TV (zoals de KPN TV+ box) via het
Android TV Remote-protocol v2 en biedt een webpagina als afstandsbediening.

Start:   python server.py
Open:    http://<ip-van-deze-pc>:8080  op je telefoon
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from aiohttp import web
from androidtvremote2 import (
    AndroidTVRemote,
    CannotConnect,
    ConnectionClosed,
    InvalidAuth,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
CERT_FILE = BASE_DIR / "cert.pem"
KEY_FILE = BASE_DIR / "key.pem"
STATIC_DIR = BASE_DIR / "static"

LOGGER = logging.getLogger("tvremote")

DEFAULT_CONFIG = {
    "host": "",
    "port": 8080,
    "client_name": "TV Remote (PC)",
    # Apps die als snelknop in de webpagina verschijnen. Sleutel = naam,
    # waarde = Android package-id of een deeplink.
    "apps": {
        "YouTube": "com.google.android.youtube.tv",
        "Netflix": "com.netflix.ninja",
        "NPO": "nl.uitzendinggemist",
        "Spotify": "com.spotify.tv.android",
        "Disney+": "com.disney.disneyplus",
        "Prime Video": "com.amazon.amazonvideo.livingroom",
    },
}

# Alleen deze toetsen mag de webpagina versturen.
ALLOWED_KEYS = {
    "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT", "DPAD_CENTER",
    "BACK", "HOME", "MENU", "POWER", "TV", "GUIDE", "INFO", "SETTINGS",
    "VOLUME_UP", "VOLUME_DOWN", "VOLUME_MUTE",
    "CHANNEL_UP", "CHANNEL_DOWN",
    "MEDIA_PLAY_PAUSE", "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_STOP",
    "MEDIA_REWIND", "MEDIA_FAST_FORWARD", "MEDIA_PREVIOUS", "MEDIA_NEXT",
    "MEDIA_RECORD", "SEARCH", "ASSIST",
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "PROG_RED", "PROG_GREEN", "PROG_YELLOW", "PROG_BLUE",
    "CAPTIONS", "DEL", "ENTER", "TAB",
}


def load_config() -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_FILE.exists():
        try:
            config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except json.JSONDecodeError as err:
            LOGGER.error("config.json is ongeldig: %s", err)
    return config


def save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


class TVController:
    """Beheert de verbinding met de TV en het koppelproces."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.remote: AndroidTVRemote | None = None
        self.state = "idle"          # idle | connecting | pairing | connected | error
        self.message = ""
        self._task: asyncio.Task | None = None

    # ---- status ---------------------------------------------------------
    def status(self) -> dict:
        r = self.remote
        info = r.device_info if r and self.state == "connected" else None
        vol = r.volume_info if r and self.state == "connected" else None
        return {
            "state": self.state,
            "message": self.message,
            "host": self.config.get("host", ""),
            "is_on": r.is_on if r and self.state == "connected" else None,
            "current_app": r.current_app if r and self.state == "connected" else None,
            "device": dict(info) if info else None,
            "volume": dict(vol) if vol else None,
            "apps": self.config.get("apps", {}),
        }

    # ---- verbinding -----------------------------------------------------
    def _new_remote(self) -> AndroidTVRemote:
        return AndroidTVRemote(
            client_name=self.config.get("client_name", "TV Remote (PC)"),
            certfile=str(CERT_FILE),
            keyfile=str(KEY_FILE),
            host=self.config["host"],
            loop=asyncio.get_running_loop(),
        )

    async def connect(self) -> None:
        """Verbind met de TV. Start het koppelen als de TV ons nog niet kent."""
        await self.disconnect()
        host = self.config.get("host", "").strip()
        if not host:
            self.state = "idle"
            self.message = "Vul eerst het IP-adres van de TV-box in."
            return

        self.state = "connecting"
        self.message = f"Verbinden met {host}..."
        self.remote = self._new_remote()
        await self.remote.async_generate_cert_if_missing()
        try:
            await self.remote.async_connect()
        except InvalidAuth:
            LOGGER.info("Nog niet gekoppeld, koppelcode aanvragen")
            await self._start_pairing()
            return
        except (CannotConnect, OSError) as err:
            self.state = "error"
            self.message = f"Kan geen verbinding maken met {host}: {err}"
            self.remote = None
            return
        self._on_connected()

    async def _start_pairing(self) -> None:
        assert self.remote is not None
        try:
            await self.remote.async_start_pairing()
        except (CannotConnect, ConnectionClosed, OSError) as err:
            self.state = "error"
            self.message = f"Koppelen mislukt: {err}"
            self.remote = None
            return
        self.state = "pairing"
        self.message = "Er staat nu een code op je TV. Voer die hier in."

    async def finish_pairing(self, code: str) -> None:
        if self.state != "pairing" or self.remote is None:
            raise web.HTTPBadRequest(text="Er loopt geen koppelproces.")
        try:
            await self.remote.async_finish_pairing(code.strip().upper())
        except InvalidAuth:
            self.state = "error"
            self.message = "Onjuiste code. Probeer opnieuw te verbinden."
            self.remote = None
            return
        except (CannotConnect, ConnectionClosed, OSError) as err:
            self.state = "error"
            self.message = f"Koppelen mislukt: {err}"
            self.remote = None
            return
        self.message = "Gekoppeld, verbinden..."
        try:
            await self.remote.async_connect()
        except (InvalidAuth, CannotConnect, OSError) as err:
            self.state = "error"
            self.message = f"Verbinden na koppelen mislukt: {err}"
            self.remote = None
            return
        self._on_connected()

    def _on_connected(self) -> None:
        assert self.remote is not None
        self.state = "connected"
        self.message = "Verbonden"
        self.remote.keep_reconnecting(self._on_invalid_auth)
        self.remote.add_is_available_updated_callback(self._on_available)
        LOGGER.info("Verbonden met %s", self.remote.device_info)

    def _on_invalid_auth(self) -> None:
        self.state = "error"
        self.message = "De TV kent deze PC niet meer. Verbind opnieuw om te koppelen."

    def _on_available(self, available: bool) -> None:
        if self.state in ("connected", "error") and self.remote is not None:
            self.state = "connected" if available else "error"
            self.message = "Verbonden" if available else "Verbinding verbroken, opnieuw proberen..."

    async def disconnect(self) -> None:
        if self.remote is not None:
            self.remote.disconnect()
            self.remote = None
        self.state = "idle"
        self.message = ""

    # ---- commando's -----------------------------------------------------
    def _require_connected(self) -> AndroidTVRemote:
        if self.remote is None or self.state != "connected":
            raise web.HTTPConflict(text="Niet verbonden met de TV.")
        return self.remote

    def send_key(self, key: str, direction: str = "SHORT") -> None:
        if key not in ALLOWED_KEYS:
            raise web.HTTPBadRequest(text=f"Onbekende toets: {key}")
        if direction not in ("SHORT", "START_LONG", "END_LONG"):
            raise web.HTTPBadRequest(text=f"Onbekende richting: {direction}")
        self._require_connected().send_key_command(key, direction)

    def send_text(self, text: str) -> None:
        self._require_connected().send_text(text)

    def launch_app(self, app: str) -> None:
        self._require_connected().send_launch_app_command(app)


# ---- HTTP-routes ----------------------------------------------------------

def make_app(controller: TVController) -> web.Application:
    app = web.Application()

    async def index(_: web.Request) -> web.FileResponse:
        return web.FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})

    async def status(_: web.Request) -> web.Response:
        return web.json_response(controller.status())

    async def connect(request: web.Request) -> web.Response:
        data = await request.json() if request.can_read_body else {}
        host = (data.get("host") or controller.config.get("host", "")).strip()
        if host != controller.config.get("host"):
            controller.config["host"] = host
            save_config(controller.config)
        await controller.connect()
        return web.json_response(controller.status())

    async def pair(request: web.Request) -> web.Response:
        data = await request.json()
        await controller.finish_pairing(str(data.get("code", "")))
        return web.json_response(controller.status())

    async def disconnect(_: web.Request) -> web.Response:
        await controller.disconnect()
        return web.json_response(controller.status())

    async def key(request: web.Request) -> web.Response:
        data = await request.json()
        try:
            controller.send_key(str(data.get("key", "")), str(data.get("direction", "SHORT")))
        except ConnectionClosed:
            raise web.HTTPConflict(text="Verbinding met de TV is weggevallen.")
        return web.json_response({"ok": True})

    async def text(request: web.Request) -> web.Response:
        data = await request.json()
        value = str(data.get("text", ""))
        if not value:
            raise web.HTTPBadRequest(text="Geen tekst opgegeven.")
        try:
            controller.send_text(value)
        except ConnectionClosed:
            raise web.HTTPConflict(text="Verbinding met de TV is weggevallen.")
        return web.json_response({"ok": True})

    async def launch(request: web.Request) -> web.Response:
        data = await request.json()
        target = str(data.get("app", ""))
        if not target:
            raise web.HTTPBadRequest(text="Geen app opgegeven.")
        try:
            controller.launch_app(target)
        except ConnectionClosed:
            raise web.HTTPConflict(text="Verbinding met de TV is weggevallen.")
        return web.json_response({"ok": True})

    app.router.add_get("/", index)
    app.router.add_get("/api/status", status)
    app.router.add_post("/api/connect", connect)
    app.router.add_post("/api/pair", pair)
    app.router.add_post("/api/disconnect", disconnect)
    app.router.add_post("/api/key", key)
    app.router.add_post("/api/text", text)
    app.router.add_post("/api/launch", launch)
    app.router.add_static("/static", STATIC_DIR)

    async def on_startup(_: web.Application) -> None:
        if controller.config.get("host"):
            asyncio.create_task(controller.connect())

    async def on_cleanup(_: web.Application) -> None:
        await controller.disconnect()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    if not CONFIG_FILE.exists():
        save_config(config)
    port = int(os.environ.get("TVREMOTE_PORT", config.get("port", 8080)))
    controller = TVController(config)
    print(f"TV Remote draait op http://0.0.0.0:{port}  (open dit adres met het IP van deze PC)")
    web.run_app(make_app(controller), host="0.0.0.0", port=port, print=None)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    main()
