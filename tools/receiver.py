"""Tiny local receiver for the trailer renderer: POST a data-URL body to /<filename> and it is saved to OUT_DIR.

usage: python3 tools/receiver.py <out_dir>   (listens on 127.0.0.1:8766)
"""
import base64
import http.server
import os
import sys

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)


class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_POST(self):
        name = os.path.basename(self.path.strip("/"))
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(base64.b64decode(body.split(",", 1)[1]))
        self.send_response(200); self._cors(); self.end_headers(); self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


http.server.HTTPServer(("127.0.0.1", 8766), Handler).serve_forever()
