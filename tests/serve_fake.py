"""Avvia il finto server IMAP su una porta fissa (per i test dell'app per telefono). Uso: python tests/serve_fake.py 14300"""
import os
import socketserver
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fake_imap  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else 14300
srv = socketserver.ThreadingTCPServer(("127.0.0.1", port), fake_imap.Handler)
srv.daemon_threads = True
print(f"finto IMAP su 127.0.0.1:{port}", flush=True)
try:
    srv.serve_forever()
except KeyboardInterrupt:
    pass
