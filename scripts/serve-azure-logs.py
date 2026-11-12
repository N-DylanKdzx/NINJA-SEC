"""Serve the private Azure audit snapshot to Grafana on loopback."""

import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import oci


class Snapshot:
    def __init__(self):
        self.namespace = os.environ["NINJASEC_OCI_NAMESPACE"]
        self.client = oci.object_storage.ObjectStorageClient(
            {},
            signer=oci.auth.signers.InstancePrincipalsSecurityTokenSigner(),
            timeout=(3, 8),
        )
        self.expires = 0.0
        self.body = b""

    def read(self):
        if time.monotonic() >= self.expires:
            response = self.client.get_object(
                self.namespace,
                "ninjasec-grafana-azure-logs",
                "latest.json",
                retry_strategy=oci.retry.NoneRetryStrategy(),
            )
            body = response.data.content
            document = json.loads(body)
            if document["table"] != "NINJASECOCIAudit_CL" or not isinstance(document["events"], list):
                raise ValueError("Unexpected snapshot format")
            self.body = body
            self.expires = time.monotonic() + 60
        return self.body


class SnapshotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/latest.json":
            self.send_error(404)
            return
        try:
            body = self.server.snapshot.read()
        except (oci.exceptions.ServiceError, ValueError, KeyError, OSError) as error:
            self.log_error("Could not read snapshot: %s", type(error).__name__)
            self.send_error(502, "Snapshot unavailable")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8766), SnapshotHandler) as server:
        server.snapshot = Snapshot()
        server.serve_forever()
