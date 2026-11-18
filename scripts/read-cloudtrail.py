"""Read CloudTrail gzip objects into a deterministic batch for downstream export."""

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile

import boto3
from botocore.config import Config


MAX_OBJECT_BYTES = 128 * 1024 * 1024


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def object_keys(s3, bucket, keys, prefix):
    if keys:
        return sorted(set(keys))
    selected = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        selected.extend(item["Key"] for item in page.get("Contents", []) if item["Key"].endswith(".json.gz"))
    return sorted(set(selected))


def read_batch(s3, bucket, keys):
    events = {}
    sources = []
    duplicates = 0
    for key in keys:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response["Body"]
        try:
            compressed = body.read(MAX_OBJECT_BYTES + 1)
        finally:
            body.close()
        if len(compressed) > MAX_OBJECT_BYTES:
            raise ValueError(f"Object exceeds supported size: {key}")
        with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as stream:
            decoded = stream.read(MAX_OBJECT_BYTES + 1)
        if len(decoded) > MAX_OBJECT_BYTES:
            raise ValueError(f"Decompressed object exceeds supported size: {key}")
        document = json.loads(decoded)
        if not isinstance(document, dict) or not isinstance(document.get("Records"), list):
            raise ValueError(f"Expected a CloudTrail Records array: {key}")
        for record in document["Records"]:
            if not isinstance(record, dict):
                raise ValueError(f"Invalid CloudTrail record: {key}")
            event_id = record.get("eventID")
            if not isinstance(event_id, str) or not event_id:
                raise ValueError(f"Missing CloudTrail eventID: {key}")
            if event_id in events:
                if events[event_id] != record:
                    raise ValueError(f"Conflicting records for eventID {event_id}")
                duplicates += 1
            events[event_id] = record
        sources.append({
            "bucket": bucket,
            "key": key,
            "versionId": response.get("VersionId"),
            "sha256": hashlib.sha256(compressed).hexdigest(),
            "recordCount": len(document["Records"]),
            "encryption": response.get("ServerSideEncryption"),
            "kmsKeyId": response.get("SSEKMSKeyId"),
        })
    return {
        "schemaVersion": 1,
        "sources": sources,
        "duplicateCount": duplicates,
        "Records": [events[event_id] for event_id in sorted(events)],
    }


def write_batch(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--key", action="append", help="Repeat for several objects.")
    selection.add_argument("--prefix", help="Use a dated CloudTrail prefix, excluding CloudTrail-Digest.")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--profile", help="Omit to use the default SDK credential chain.")
    parser.add_argument("--output", type=Path, required=True, help="Local batch JSON; keep outside Git.")
    parser.add_argument("--expect-event", help="Fail without replacing output if this eventID is missing.")
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    s3 = session.client("s3", config=Config(retries={"mode": "standard", "max_attempts": 5}))
    keys = object_keys(s3, args.bucket, args.key, args.prefix)
    if not keys:
        raise ValueError("No CloudTrail gzip objects matched the selection.")
    batch = read_batch(s3, args.bucket, keys)
    matched = any(event["eventID"] == args.expect_event for event in batch["Records"])
    if args.expect_event and not matched:
        raise ValueError("Expected eventID is absent from the batch.")
    payload = canonical_bytes(batch)
    write_batch(args.output, payload)
    print(json.dumps({
        "objects": len(keys),
        "events": len(batch["Records"]),
        "duplicates": batch["duplicateCount"],
        "batchSha256": hashlib.sha256(payload).hexdigest(),
        "expectedEventFound": matched if args.expect_event else None,
    }))


if __name__ == "__main__":
    main()
