"""Test cloud backend checks."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice_input.backends import create_backend                    # noqa: E402
from voice_input.backends.cloud_openai import CloudBackend         # noqa: E402

fails = 0


def check(label, cond, detail=""):
    global fails
    if not cond:
        fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {label}{(' — ' + str(detail)) if detail else ''}")


STATE = {"requests": 0, "last_body": b"", "last_headers": {}, "mode": "json"}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        STATE["requests"] += 1
        length = int(self.headers.get("Content-Length", 0))
        STATE["last_body"] = self.rfile.read(length)
        STATE["last_headers"] = dict(self.headers)

        if STATE["mode"] == "401":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"error":"bad key"}')
            return
        if STATE["mode"] == "text":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write("Plain-text result".encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"text": "\u4f60\u597d\u4e16\u754c"}).encode())

    def log_message(self, *args):
        pass


server = HTTPServer(("127.0.0.1", 0), Handler)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}/v1"

print(f"Mock server: {base}")


backend = CloudBackend(base_url=base, api_key="test-key", model="whisper-1",
                       language="zh")
session = backend.open_session()
session.accept(b"\x01\x00" * 16000)
started = time.monotonic()
text = session.finish()
print(f"Result {text!r}({time.monotonic() - started:.2f}s)")

check("Returns the expected text", text == "\u4f60\u597d\u4e16\u754c", text)
body = STATE["last_body"]
check("Multipart includes file", b'name="file"' in body)
check("Multipart includes model", b'name="model"' in body and b"whisper-1" in body)
check("Multipart includes language", b'name="language"' in body)
check("Valid WAV header (RIFF/WAVE)", body.find(b"RIFF") > 0 and b"WAVE" in body)
check("Authorization header is included", STATE["last_headers"].get("Authorization")
      == "Bearer test-key", STATE["last_headers"].get("Authorization"))
check("Correct endpoint", backend.endpoint == f"{base}/audio/transcriptions",
      backend.endpoint)


STATE["mode"] = "text"
backend = CloudBackend(base_url=base, model="whisper-1", language="zh")
_s = backend.open_session()
_s.accept(b"\x00\x00" * 8000)
check("Plain-text responses are supported", _s.finish() == "Plain-text result")


STATE["mode"] = "401"
STATE["requests"] = 0
backend = CloudBackend(base_url=base, api_key="bad", model="whisper-1")
session = backend.open_session()
session.accept(b"\x00\x00" * 8000)
try:
    session.finish()
    check("401 should raise an exception", False)
except RuntimeError as exc:
    message = str(exc)
    check("401 raises a readable error", "401" in message, message)
    check("401 is not retried", STATE["requests"] == 1,
          STATE["requests"])


backend = CloudBackend(base_url="http://127.0.0.1:1/v1", timeout=2)
session = backend.open_session()
session.accept(b"\x00\x00" * 8000)
try:
    session.finish()
    check("Connection failure should raise an exception", False)
except RuntimeError as exc:
    check("Error includes the endpoint", "127.0.0.1:1" in str(exc), str(exc)[:80])


cfg = {"backend": "cloud", "preset": "lan",
       "base_url": base, "model": "whisper-small"}
backend = create_backend(cfg)
check("create_backend uses the base_url override",
      isinstance(backend, CloudBackend) and backend.base_url == base,
      backend.describe())
check("create_backend uses the model override", backend.model == "whisper-small",
      backend.model)


backend = CloudBackend(base_url=base, endpoint=f"http://127.0.0.1:{port}/inference")
check("Endpoint override is applied", backend.endpoint.endswith("/inference"),
      backend.endpoint)

server.shutdown()
print("Results:", "All passed" if fails == 0 else f"{fails} failures")
sys.exit(0 if fails == 0 else 1)
