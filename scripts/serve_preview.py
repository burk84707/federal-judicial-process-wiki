"""Serve only the generated public payload on loopback; never the repository archive."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    base = "/legal/federal-process/"

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == self.base.rstrip('/'):
            self.send_response(301); self.send_header('Location',self.base); self.end_headers(); return
        if not parsed.path.startswith(self.base):
            self.send_error(404, 'This preview serves only the public reference.'); return
        path = unquote(parsed.path.removeprefix(self.base))
        if '..' in path.split('/') or '\\' in path or any(part.startswith('.') for part in path.split('/') if part):
            self.send_error(400, 'Invalid public path'); return
        self.path = '/' + path + ('?' + parsed.query if parsed.query else '')
        super().do_GET()

    def list_directory(self, path):
        self.send_error(404, 'Directory listing disabled.'); return None

    def log_message(self, fmt, *args):
        print(fmt % args)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8766); args=parser.parse_args()
    site=ROOT/'dist/site'
    if not (site/'manifest.json').is_file(): raise SystemExit('Build the public site first.')
    Handler.base=json.loads((site/'manifest.json').read_text(encoding='utf-8'))['base_path']
    server=ThreadingHTTPServer(('127.0.0.1',args.port),partial(Handler,directory=str(site)))
    print(f'Local preview: http://127.0.0.1:{args.port}{Handler.base}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()
