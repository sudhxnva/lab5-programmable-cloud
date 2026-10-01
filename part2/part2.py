#!/usr/bin/env python3
"""Snapshot a Flask VM disk and time the creation of three clones."""

import argparse
import time
from pathlib import Path

import google.auth
import googleapiclient.discovery


NETWORK = "global/networks/default"
TIMING_PATH = Path(__file__).with_name("TIMING.md")


def snapshot_name(instance_name):
    return f"base-snapshot-{instance_name}"


def build_clone_body(instance_name, zone, snapshot, machine_type):
    return {
        "name": instance_name,
        "machineType": f"zones/{zone}/machineTypes/{machine_type}",
        "disks": [
            {
                "boot": True,
                "autoDelete": True,
                "initializeParams": {
                    "sourceSnapshot": f"global/snapshots/{snapshot}"
                },
            }
        ],
        "networkInterfaces": [
            {
                "network": NETWORK,
                "accessConfigs": [
                    {"name": "External NAT", "type": "ONE_TO_ONE_NAT"}
                ],
            }
        ],
    }


def timing_markdown(timings):
    rows = [
        "# Part 2 VM Creation Timing",
        "",
        "| Instance | Creation time (seconds) |",
        "| --- | ---: |",
    ]
    rows.extend(f"| {name} | {seconds:.3f} |" for name, seconds in timings)
    return "\n".join(rows) + "\n"


def wait_for_zone_operation(compute, project, zone, operation_name):
    while True:
        result = compute.zoneOperations().get(
            project=project, zone=zone, operation=operation_name
        ).execute()
        if result.get("status") == "DONE":
            if "error" in result:
                raise RuntimeError(f"Operation {operation_name} failed: {result['error']}")
            return
        time.sleep(1)


def source_boot_disk(compute, project, zone, instance_name):
    instance = compute.instances().get(
        project=project, zone=zone, instance=instance_name
    ).execute()
    for disk in instance.get("disks", []):
        if disk.get("boot"):
            return disk["source"].rsplit("/", maxsplit=1)[-1]
    raise ValueError(f"Instance {instance_name} has no boot disk")


def create_snapshot(compute, project, zone, disk, name):
    operation = compute.disks().createSnapshot(
        project=project, zone=zone, disk=disk, body={"name": name}
    ).execute()
    wait_for_zone_operation(compute, project, zone, operation["name"])


def create_and_time_clone(compute, project, zone, instance_name, snapshot, machine_type):
    started = time.perf_counter()
    operation = compute.instances().insert(
        project=project,
        zone=zone,
        body=build_clone_body(instance_name, zone, snapshot, machine_type),
    ).execute()
    wait_for_zone_operation(compute, project, zone, operation["name"])
    return time.perf_counter() - started


def parse_args():
    parser = argparse.ArgumentParser(
        description="Snapshot a VM disk and create three timed clones."
    )
    parser.add_argument("--project", help="Google Cloud project ID")
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--source-instance", default="flask-tutorial-vm")
    parser.add_argument("--clone-prefix", default="flask-clone")
    parser.add_argument("--machine-type", default="e2-micro")
    return parser.parse_args()


def main():
    args = parse_args()
    credentials, default_project = google.auth.default()
    project = args.project or default_project
    if not project:
        raise ValueError("Set --project or configure a Google Cloud default project.")

    compute = googleapiclient.discovery.build(
        "compute", "v1", credentials=credentials
    )
    disk = source_boot_disk(compute, project, args.zone, args.source_instance)
    snapshot = snapshot_name(args.source_instance)
    print(f"Creating snapshot {snapshot} from disk {disk}...")
    create_snapshot(compute, project, args.zone, disk, snapshot)

    timings = []
    for number in range(1, 4):
        clone_name = f"{args.clone_prefix}-{number}"
        print(f"Creating {clone_name}...")
        duration = create_and_time_clone(
            compute,
            project,
            args.zone,
            clone_name,
            snapshot,
            args.machine_type,
        )
        timings.append((clone_name, duration))
        print(f"{clone_name} created in {duration:.3f} seconds.")

    TIMING_PATH.write_text(timing_markdown(timings), encoding="utf-8")
    print(f"Wrote timing results to {TIMING_PATH}")


if __name__ == "__main__":
    main()
