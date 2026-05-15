from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time


STARTED_AT = time.time()


def response_payload(status):
    return {
        "service": "edge-agent",
        "status": status,
        "factory_id": os.getenv("AEGIS_FACTORY_ID", "factory-a"),
        "uptime_seconds": int(time.time() - STARTED_AT),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AegisEdgeAgent/0.1"

    def do_GET(self):
        if self.path in ("/", "/healthz", "/readyz"):
            self.write_json(200, response_payload("ok"))
            return

        self.write_json(404, response_payload("not_found"))

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def write_json(self, status_code, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.getenv("AEGIS_HTTP_PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"edge-agent listening on :{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

