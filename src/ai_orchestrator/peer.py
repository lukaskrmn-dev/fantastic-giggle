"""
peer.py
Hardened peer implementation with:
- token-verified handshake (against registry)
- ACL enforcement per-peer
- discovery via watchdog or polling
- message size limits and timeouts
- optional TLS support for TCP
Protocol: newline-delimited JSON messages (simple JSON-RPC-lite)
"""
import asyncio
import json
import os
import socket
import sys
import uuid
import ssl
import time
from typing import Callable, Dict, Optional

from ai_orchestrator.registry import publish_peer, remove_peer, list_peers, load_peer, REGISTRY_DIR

# Limits and timeouts
MAX_MSG_BYTES = 256 * 1024  # 256 KB per message
READ_TIMEOUT = 10.0  # seconds for reads during handshake/response
CALL_TIMEOUT = 10.0
DISCOVERY_POLL_INTERVAL = 1.0


def supports_uds() -> bool:
    return hasattr(socket, "AF_UNIX") and sys.platform != "win32"

class DiscoveryWatcher:
    """
    Minimal cross-platform watcher: uses watchdog if available, otherwise polling.
    Emits callback when registry directory changes.
    """
    def __init__(self, on_change: Callable):
        self.on_change = on_change
        self._running = False
        self._task = None
        self._last_snapshot = None
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            self._use_watchdog = True
            class _Handler(FileSystemEventHandler):
                def __init__(self, cb):
                    super().__init__()
                    self.cb = cb
                def on_any_event(self, event):
                    # coalesce events
                    self.cb()
            self._Handler = _Handler
            self.Observer = Observer
        except Exception:
            self._use_watchdog = False

    async def start(self):
        self._running = True
        if self._use_watchdog:
            handler = self._Handler(self.on_change)
            obs = self.Observer()
            obs.schedule(handler, str(REGISTRY_DIR), recursive=False)
            obs.start()
            self._obs = obs
        else:
            # polling
            self._last_snapshot = self._snapshot()
            self._task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        self._running = False
        if self._use_watchdog:
            try:
                self._obs.stop()
                self._obs.join()
            except Exception:
                pass
        else:
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except Exception:
                    pass

    def _snapshot(self):
        try:
            return {p.name: p.stat().st_mtime for p in REGISTRY_DIR.glob("*.json")}
        except Exception:
            return {}

    async def _poll_loop(self):
        while self._running:
            cur = self._snapshot()
            if cur != self._last_snapshot:
                self._last_snapshot = cur
                self.on_change()
            await asyncio.sleep(DISCOVERY_POLL_INTERVAL)

class Peer:
    def __init__(self, name: str, loop=None, ssl_context: Optional[ssl.SSLContext] = None):
        self.name = name
        self.id = name + "-" + uuid.uuid4().hex[:8]
        self.loop = loop or asyncio.get_event_loop()
        self.server = None
        self.connections: Dict[str, asyncio.StreamWriter] = {}
        self.pending: Dict[str, asyncio.Future] = {}
        self.handlers: Dict[str, Callable] = {}
        self.token = uuid.uuid4().hex  # local token
        self.peer_acls: Dict[str, Dict] = {}  # peer_id -> metadata (including allowed_methods)
        self.discovery = DiscoveryWatcher(self._on_registry_change)
        self.ssl_context = ssl_context

    async def start(self, host=None, port=None):
        """
        Start the peer: open server (UDS or TCP), publish registry entry, and start discovery.
        Returns published metadata.
        """
        if supports_uds():
            socket_path = os.path.join(str(REGISTRY_DIR), f"sock-{self.id}.sock")
            try:
                os.unlink(socket_path)
            except Exception:
                pass
            self.server = await asyncio.start_unix_server(self._handle_client, path=socket_path)
            addr = {"type": "unix", "path": socket_path}
        else:
            server = await asyncio.start_server(self._handle_client, host or "127.0.0.1", port or 0, ssl=self.ssl_context)
            sock = next(iter(server.sockets))
            sockname = sock.getsockname()
            addr = {"type": "tcp", "host": sockname[0], "port": sockname[1], "ssl": bool(self.ssl_context)}
            self.server = server

        metadata = {
            "id": self.id,
            "name": self.name,
            "addr": addr,
            "token": self.token,
            # optional ACL: by default allow common methods; consumers can modify metadata file to tighten
            "allowed_methods": ["greet", "announce", "generate"],
            "published_at": time.time(),
        }
        publish_peer(self.id, metadata)
        # start discovery
        await self.discovery.start()
        # initial discovery pass
        self.loop.create_task(self._discovery_loop())
        return metadata

    async def stop(self):
        remove_peer(self.id)
        try:
            await self.discovery.stop()
        except Exception:
            pass
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        for w in list(self.connections.values()):
            try:
                w.close()
                await w.wait_closed()
            except Exception:
                pass

    def _on_registry_change(self):
        # wake up discovery loop faster
        # the discovery loop rescan will handle connections
        pass

    async def _discovery_loop(self):
        """
        Periodically scan registry and attempt connection to new peers.
        Using discovery watcher to trigger proactive scans would be an improvement.
        """
        while True:
            peers = list_peers()
            for pid, meta in peers.items():
                if pid == self.id:
                    continue
                if pid in self.connections:
                    continue
                try:
                    await self._connect_to_peer(pid, meta)
                except Exception:
                    # ignore connect failures; they'll be retried later
                    pass
            await asyncio.sleep(DISCOVERY_POLL_INTERVAL)

    async def _connect_to_peer(self, peer_id, meta):
        addr = meta.get("addr")
        if not addr:
            return
        if addr["type"] == "unix":
            reader, writer = await asyncio.open_unix_connection(path=addr["path"])
        else:
            # TCP
            reader, writer = await asyncio.open_connection(addr["host"], addr["port"], ssl=self.ssl_context if addr.get("ssl") else None)
        # handshake: send hello with token
        hello = {"id": None, "type": "event", "method": "hello", "params": {"id": self.id, "token": self.token, "name": self.name}}
        writer.write((json.dumps(hello) + "\n").encode())
        await writer.drain()
        # wait for ack or handshake response
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=READ_TIMEOUT)
        except Exception:
            writer.close()
            await writer.wait_closed()
            raise ConnectionError("handshake_timeout")
        if not line:
            writer.close()
            await writer.wait_closed()
            raise ConnectionError("no_handshake_reply")
        try:
            msg = json.loads(line.decode(errors="ignore"))
        except Exception:
            writer.close()
            await writer.wait_closed()
            raise ConnectionError("invalid_handshake_reply")
        if msg.get("method") == "hello_ack":
            # store writer
            self.connections[peer_id] = writer
            # optionally store peer ACL from published meta
            self.peer_acls[peer_id] = meta
            # start reader loop
            self.loop.create_task(self._reader_loop(peer_id, reader, writer))
        else:
            writer.close()
            await writer.wait_closed()
            raise ConnectionError("handshake_rejected")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """
        Handle inbound client connections. Enforce handshake: client must send hello with id+token.
        Verify token against registry metadata.
        """
        peer_id = None
        try:
            # read first line with timeout
            line = await asyncio.wait_for(reader.readline(), timeout=READ_TIMEOUT)
            if not line:
                writer.close()
                await writer.wait_closed()
                return
            if len(line) > MAX_MSG_BYTES:
                writer.close()
                await writer.wait_closed()
                return
            msg = json.loads(line.decode(errors="ignore"))
            if msg.get("method") == "hello":
                info = msg.get("params", {})
                pid = info.get("id")
                token = info.get("token")
                if not pid or not token:
                    # reject
                    rej = {"id": None, "type": "response", "error": {"message": "handshake_missing_fields"}}
                    writer.write((json.dumps(rej) + "\n").encode())
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    return
                # verify token against registry entry
                meta = load_peer(pid)
                if not meta or meta.get("token") != token:
                    rej = {"id": None, "type": "response", "error": {"message": "handshake_token_mismatch"}}
                    writer.write((json.dumps(rej) + "\n").encode())
                    await writer.drain()
                    writer.close()
                    await writer.wait_closed()
                    return
                peer_id = pid
                self.connections[peer_id] = writer
                self.peer_acls[peer_id] = meta
                # ack
                ack = {"id": None, "type": "event", "method": "hello_ack", "params": {"id": self.id, "name": self.name}}
                writer.write((json.dumps(ack) + "\n").encode())
                await writer.drain()
            else:
                # no hello — reject
                writer.close()
                await writer.wait_closed()
                return
            await self._reader_loop(peer_id, reader, writer)
        except Exception:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _reader_loop(self, peer_id, reader, writer):
        while True:
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=None)
            except asyncio.CancelledError:
                break
            except Exception:
                # on error, close
                break
            if not line:
                # connection closed
                if peer_id and peer_id in self.connections:
                    del self.connections[peer_id]
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass
                break
            if len(line) > MAX_MSG_BYTES:
                # ignore/optionally send error
                continue
            try:
                msg = json.loads(line.decode(errors="ignore"))
            except Exception:
                continue
            # process message asynchronously
            self.loop.create_task(self._handle_message(peer_id, msg, writer))

    async def _handle_message(self, peer_id, msg, writer):
        mtype = msg.get("type")
        mid = msg.get("id")
        if mtype == "request":
            method = msg.get("method")
            params = msg.get("params", {})
            # ACL check: if peer published allowed_methods, enforce it
            allowed = None
            if peer_id:
                meta = self.peer_acls.get(peer_id) or {}
                allowed = meta.get("allowed_methods")
            if allowed is not None and method not in allowed:
                resp = {"id": mid, "type": "response", "error": {"message": "unauthorized_method"}}
                writer.write((json.dumps(resp) + "\n").encode())
                await writer.drain()
                return
            handler = self.handlers.get(method)
            if handler:
                try:
                    # call handler; allow both sync and async
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(params, peer_id)
                    else:
                        result = handler(params, peer_id)
                    resp = {"id": mid, "type": "response", "result": result}
                except Exception as e:
                    resp = {"id": mid, "type": "response", "error": {"message": str(e)}}
            else:
                resp = {"id": mid, "type": "response", "error": {"message": "method_not_found"}}
            writer.write((json.dumps(resp) + "\n").encode())
            await writer.drain()
        elif mtype == "response":
            fut = self.pending.pop(mid, None)
            if fut:
                if "error" in msg:
                    fut.set_exception(Exception(msg["error"].get("message", "error")))
                else:
                    fut.set_result(msg.get("result"))
        elif mtype == "event":
            method = msg.get("method")
            handler = self.handlers.get(method)
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(msg.get("params", {}), peer_id)
                    else:
                        handler(msg.get("params", {}), peer_id)
                except Exception:
                    pass

    def register_method(self, name: str, func: Callable):
        self.handlers[name] = func

    async def call_peer(self, peer_id: str, method: str, params: dict, timeout: float = CALL_TIMEOUT):
        writer = self.connections.get(peer_id)
        if not writer:
            raise ConnectionError("peer_not_connected")
        mid = uuid.uuid4().hex
        req = {"id": mid, "type": "request", "method": method, "params": params}
        fut = self.loop.create_future()
        self.pending[mid] = fut
        writer.write((json.dumps(req) + "\n").encode())
        await writer.drain()
        return await asyncio.wait_for(fut, timeout)

    async def broadcast_event(self, method: str, params: dict):
        ev = {"id": None, "type": "event", "method": method, "params": params}
        for peer_id, w in list(self.connections.items()):
            try:
                w.write((json.dumps(ev) + "\n").encode())
                await w.drain()
            except Exception:
                pass
