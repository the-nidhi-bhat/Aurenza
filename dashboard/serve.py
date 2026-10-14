"""Serve the Aurenza dashboard from the repository root (standard library only).

Usage (from the repository root):
    python dashboard/serve.py
    python dashboard/serve.py --port 8080

Then open http://127.0.0.1:8000/dashboard/

The repository root is served so the static dashboard page can fetch the
committed engine outputs at /demo/result.json and /demo/evaluation.json using
relative paths. The dashboard imports no engine code (contract §10).
"""

import argparse
import functools
import http.server
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(http.server.SimpleHTTPRequestHandler):
    """Static handler that disables caching so refreshed JSON is always read."""

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):  # keep the console quiet but useful
        print(f'  {self.address_string()} - {fmt % args}')


def main(argv=None):
    ap = argparse.ArgumentParser(description='Aurenza dashboard server')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8000)
    args = ap.parse_args(argv)

    handler = functools.partial(Handler, directory=ROOT)
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        print(f'Aurenza dashboard:  http://{args.host}:{args.port}/dashboard/')
        print('Serving repository root. Press Ctrl+C to stop.')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nStopped.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
