"""Serve the private CloudWatch snapshot to Grafana over local HTTP only."""

from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from urllib.request import urlopen

import oci


def fresh_document(body):
    document = json.loads(body)
    now = datetime.now(timezone.utc)
    if document['source'] != 'AWS/EC2 CPUUtilization':
        raise ValueError('Unexpected source')
    if not now - timedelta(minutes=12) <= datetime.fromisoformat(document['generated_at']) <= now:
        raise ValueError('Stale snapshot')
    document['points'] = [point for point in document['points']
                          if now - timedelta(minutes=15) <= datetime.fromisoformat(point['timestamp']) <= now]
    if not document['points']:
        raise ValueError('No fresh source points')
    return json.dumps(document).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ('/latest.json', '/oci-cpu.json', '/azure-freshness.json'):
            self.send_error(404)
            return
        try:
            if self.path == '/oci-cpu.json':
                body = oci_cpu(self.server.monitoring)
            elif self.path == '/azure-freshness.json':
                body = azure_freshness()
            else:
                obj = self.server.storage.get_object(os.environ['NINJASEC_OCI_NAMESPACE'],
                                                      'ninjasec-grafana-aws-metrics', 'latest.json')
                body = fresh_document(obj.data.content)
        except (OSError, ValueError, KeyError, oci.exceptions.ServiceError):
            self.send_error(503, 'CloudWatch data stale or unavailable')
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def oci_cpu(client):
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=15)
    query = oci.monitoring.models.SummarizeMetricsDataDetails(
        namespace='oci_vmi_resource_utilization', start_time=start, end_time=now,
        query='CpuUtilization[5m]{resourceId="' + os.environ['NINJASEC_OCI_UTILITY_ID'] + '"}.mean()',
    )
    metrics = client.summarize_metrics_data(os.environ['NINJASEC_OCI_COMPARTMENT'], query).data
    points = [{'timestamp': point.timestamp.isoformat(), 'cpu_percent': point.value}
              for metric in metrics for point in metric.aggregated_datapoints if start <= point.timestamp <= now]
    if not points:
        raise ValueError('No fresh OCI samples')
    return json.dumps({'source': 'OCI Monitoring', 'generated_at': now.isoformat(), 'points': points}).encode()


def azure_freshness():
    with urlopen('http://127.0.0.1:8766/latest.json', timeout=8) as response:
        snapshot = json.load(response)
    exported = snapshot['exportedAt']
    # Azure emits seven fractional digits, while older Python accepts up to six.
    stamp = datetime.fromisoformat(exported.rstrip('Z')[:26] + '+00:00')
    hours = (datetime.now(timezone.utc) - stamp).total_seconds() / 3600
    return json.dumps({'points': [{'exported_at': exported, 'age_hours': round(hours, 2),
                                  'state': 'vigente' if 0 <= hours < 26 else 'atrasado'}]}).encode()


if __name__ == '__main__':
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    with HTTPServer(('127.0.0.1', 8767), Handler) as server:
        server.storage = oci.object_storage.ObjectStorageClient({}, signer=signer, timeout=(3, 8),
                                                               retry_strategy=oci.retry.NoneRetryStrategy())
        server.monitoring = oci.monitoring.MonitoringClient({}, signer=signer, timeout=(3, 8),
                                                            retry_strategy=oci.retry.NoneRetryStrategy())
        server.serve_forever()
