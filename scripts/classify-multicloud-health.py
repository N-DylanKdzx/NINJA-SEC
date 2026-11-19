"""Classify independent NINJA-SEC health signals without changing either cloud."""

import argparse
import json
import sys


def classify(signals):
    portal = signals.get('aws_portal')
    sql = signals.get('aws_app_sql')
    aws = signals.get('aws_management')
    tunnel = signals.get('wireguard')
    replication = signals.get('replication')

    if aws is False and portal is False:
        return 'aws_access_unavailable'
    if sql is False and aws is True:
        return 'rds_sql_path_unavailable'
    if sql is True and tunnel is False:
        return 'tunnel_unavailable'
    if sql is True and portal is False:
        return 'aws_portal_unavailable'
    if sql is True and tunnel is True and replication is False:
        return 'replication_unavailable'
    if all(value is True for value in (portal, sql, aws, tunnel, replication)):
        return 'healthy'
    return 'inconclusive'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    signals = json.load(sys.stdin)
    known = {'aws_portal', 'aws_app_sql', 'aws_management', 'wireguard', 'replication'}
    if not isinstance(signals, dict) or set(signals) - known:
        parser.error('Supply a JSON object with known health signals')
    if any(value is not None and type(value) is not bool for value in signals.values()):
        parser.error('Health signals must be true, false or null (unknown)')
    print(json.dumps({'classification': classify(signals), 'promotion_authorized': False}))


if __name__ == '__main__':
    main()
