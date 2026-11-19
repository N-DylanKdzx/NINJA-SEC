"""Publish health of the established NINJA-SEC WireGuard peer."""

from datetime import datetime, timezone
import os
import subprocess

import oci


def main():
    now = datetime.now(timezone.utc)
    peer = subprocess.run(['ping', '-c', '2', '-W', '2', '10.255.254.1'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
    result = subprocess.run(['/usr/local/bin/wg', 'show', 'wg0', 'latest-handshakes'],
                            capture_output=True, text=True, timeout=5)
    fresh = result.returncode == 0 and any(
        0 <= now.timestamp() - int(line.split()[-1]) <= 180 for line in result.stdout.splitlines()
    )
    healthy = int(peer.returncode == 0 and fresh)
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    client = oci.monitoring.MonitoringClient({}, signer=signer, service_endpoint=
                                             'https://telemetry-ingestion.us-ashburn-1.oraclecloud.com', timeout=(5, 10))
    point = oci.monitoring.models.Datapoint(timestamp=now, value=healthy)
    metric = oci.monitoring.models.MetricDataDetails(namespace='ninjasec_connectivity',
                                                    compartment_id=os.environ['NINJASEC_OCI_COMPARTMENT'],
                                                    name='WireGuardPeerHealthy', dimensions={'link': 'oci-aws'},
                                                    datapoints=[point])
    response = client.post_metric_data(oci.monitoring.models.PostMetricDataDetails(metric_data=[metric]))
    if response.data.failed_metrics_count:
        raise RuntimeError('OCI rejected the health sample')
    print(f'WireGuardPeerHealthy={healthy}')


if __name__ == '__main__':
    main()
