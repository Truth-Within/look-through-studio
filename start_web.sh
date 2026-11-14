#!/bin/sh
# Start The Look Through Studio web UI.
# Binds 0.0.0.0 by default, so it is reachable as http://127.0.0.1:8080 on this
# machine AND as http://<LAN-IP>:8080 from the phone (Android app / Chrome).
# Pass --host 127.0.0.1 to restrict to this machine only.
cd "$(dirname "$0")"
exec python3 webapp.py "$@"
