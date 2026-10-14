#!/usr/bin/env python3
"""PlumeTrace relay: the dashboard and its live data on ONE port, safe to expose through a tunnel.

    python3 tools/relay.py [--port 8090] [--gateway ws://localhost:8765] [--bind 127.0.0.1]

http://<host>:<port>/      the dashboard (the files in web/)
ws://<host>:<port>/ws      live data, relayed from the PlumeTrace gateway

Viewers are view-only: their commands are answered with a rejected ack and never reach the gateway.
A viewer whose page URL carries ?key=<value of PLUMETRACE_RELAY_KEY> may send commands (off when unset).
The relay keeps the last message of each type, so a viewer who joins late sees the current state.
Expose the port with any HTTPS tunnel or reverse proxy that passes WebSockets; nothing else is needed,
because page and data share one origin. Needs the Python package websockets >= 13.
"""
import argparse
import asyncio
import hmac
import json
import mimetypes
import os
import time
from urllib.parse import parse_qs, urlsplit

try:
    from websockets.asyncio.client import connect
    from websockets.asyncio.server import serve
    from websockets.datastructures import Headers
    from websockets.http11 import Response
except ImportError as e:  # pragma: no cover
    raise SystemExit(f'relay.py needs websockets >= 13 (pip install --user websockets): {e}')

WEB = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web'))
STICKY = ('hello', 'mission', 'posterior', 'obstacles', 'sync', 'plume_points', 'plume_true', 'pose', 'sample',
          'alert', 'event', 'battery')  # replayed to late joiners
RELAY_CONFIG = b"\n// added by tools/relay.py: live data comes from this same origin\nwindow.PLUMETRACE_CONFIG.wsUrl = 'auto';\n"


class Relay:
    def __init__(self, gateway, key):
        self.gateway = gateway
        self.key = key
        self.viewers = set()
        self.last = {}
        self.up = None

    # --- static files ------------------------------------------------------------
    def http(self, connection, request):
        url = urlsplit(request.path)
        if url.path == '/ws':
            return None  # continue with the WebSocket handshake
        rel = 'index.html' if url.path in ('', '/') else url.path.lstrip('/')
        path = os.path.realpath(os.path.join(WEB, rel))
        if not (path == WEB or path.startswith(WEB + os.sep)) or not os.path.isfile(path):
            return self.reply(404, b'not found\n', 'text/plain')
        with open(path, 'rb') as f:
            body = f.read()
        if rel == 'config.js':
            body += RELAY_CONFIG
        return self.reply(200, body, mimetypes.guess_type(path)[0] or 'application/octet-stream')

    @staticmethod
    def reply(status, body, ctype):
        reason = {200: 'OK', 404: 'Not Found'}[status]
        return Response(status, reason, Headers([('Content-Type', ctype), ('Content-Length', str(len(body))),
                                                 ('Cache-Control', 'no-store')]), body)

    # --- viewers -------------------------------------------------------------------
    async def viewer(self, ws):
        query = parse_qs(urlsplit(ws.request.path).query)
        given = (query.get('key') or [''])[0]
        control = bool(self.key) and hmac.compare_digest(given, self.key)
        self.viewers.add(ws)
        try:
            for t in STICKY:
                if t in self.last:
                    await ws.send(self.last[t])
            async for raw in ws:
                if control and self.up is not None:
                    await self.up.send(raw)
                else:
                    await ws.send(json.dumps(dict(type='ack', command=None, ok=False, t=round(time.time(), 3),
                                                  detail='view only' if not control else 'gateway offline')))
        except Exception:
            pass
        finally:
            self.viewers.discard(ws)

    async def broadcast(self, raw):
        for v in list(self.viewers):
            try:
                await v.send(raw)
            except Exception:
                self.viewers.discard(v)

    # --- gateway side --------------------------------------------------------------
    async def upstream(self):
        while True:
            try:
                async with connect(self.gateway, max_size=2 ** 22) as up:
                    self.up = up
                    print(f'relay: connected to gateway {self.gateway}', flush=True)
                    async for raw in up:
                        try:
                            t = json.loads(raw).get('type')
                        except ValueError:
                            continue
                        if t in STICKY:
                            self.last[t] = raw
                        await self.broadcast(raw)
            except Exception as e:
                print(f'relay: gateway not reachable ({type(e).__name__}); retrying', flush=True)
            self.up = None
            await asyncio.sleep(2.0)


async def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--port', type=int, default=8090)
    ap.add_argument('--bind', default='127.0.0.1', help='0.0.0.0 to serve the local network directly')
    ap.add_argument('--gateway', default='ws://localhost:8765')
    a = ap.parse_args()
    relay = Relay(a.gateway, os.environ.get('PLUMETRACE_RELAY_KEY', ''))
    async with serve(relay.viewer, a.bind, a.port, process_request=relay.http, max_size=2 ** 20):
        print(f'relay: dashboard on http://{a.bind}:{a.port}/  (commands: '
              f'{"with ?key=..." if relay.key else "disabled, view only"})', flush=True)
        await relay.upstream()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
