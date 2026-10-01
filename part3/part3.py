#!/usr/bin/env python3
"""Create VM-1, which uses service-account credentials to create Flask VM-2."""

import argparse
import time
from pathlib import Path

import googleapiclient.discovery
from google.oauth2 import service_account


PART3_DIR = Path(__file__).parent
CREDENTIALS_PATH = PART3_DIR / "service-credentials.json"
VM1_STARTUP_PATH = PART3_DIR / "vm1_startup.sh"
VM1_LAUNCHER_PATH = PART3_DIR / "vm1_launch_vm2.py"
VM2_STARTUP_PATH = PART3_DIR / "vm2_startup.sh"
NETWORK = "global/networks/default"
IMAGE = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"


def build_vm2_body(instance_name, zone, startup_script, machine_type):
    return {
        "name": instance_name,
        "machineType": f"zones/{zone}/machineTypes/{machine_type}",
        "disks": [
            {
                "boot": True,
                "autoDelete": True,
                "initializeParams": {"sourceImage": IMAGE},
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
        "tags": {"items": ["allow-5000"]},
        "metadata": {
            "items": [{"key": "startup-script", "value": startup_script}]
        },
    }


def build_vm1_body(instance_name, zone, startup_script, metadata, machine_type):
    items = [{"key": "startup-script", "value": startup_script}]
    items.extend({"key": key, "value": value} for key, value in metadata.items())
    return {
        "name": instance_name,
        "machineType": f"zones/{zone}/machineTypes/{machine_type}",
        "disks": [
            {
                "boot": True,
                "autoDelete": True,
                "initializeParams": {"sourceImage": IMAGE},
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
        "metadata": {"items": items},
    }


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


def parse_args():
    parser = argparse.ArgumentParser(description="Create VM-1 to launch Flask VM-2.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--vm1-name", default="part3-vm1-launcher")
    parser.add_argument("--vm2-name", default="part3-vm2-flask")
    parser.add_argument("--machine-type", default="e2-micro")
    return parser.parse_args()


def main():
    args = parse_args()
    if not CREDENTIALS_PATH.is_file():
        raise FileNotFoundError(f"Missing service-account key: {CREDENTIALS_PATH}")

    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH
    )
    compute = googleapiclient.discovery.build("compute", "v1", credentials=credentials)
    metadata = {
        "service-credentials": CREDENTIALS_PATH.read_text(encoding="utf-8"),
        "vm1-launch-vm2-code": VM1_LAUNCHER_PATH.read_text(encoding="utf-8"),
        "vm2-startup-script": VM2_STARTUP_PATH.read_text(encoding="utf-8"),
        "project": args.project,
        "zone": args.zone,
        "vm2-name": args.vm2_name,
        "vm2-machine-type": args.machine_type,
    }
    vm1_startup = VM1_STARTUP_PATH.read_text(encoding="utf-8")
    operation = compute.instances().insert(
        project=args.project,
        zone=args.zone,
        body=build_vm1_body(
            args.vm1_name, args.zone, vm1_startup, metadata, args.machine_type
        ),
    ).execute()
    wait_for_zone_operation(compute, args.project, args.zone, operation["name"])
    print(f"VM-1 {args.vm1_name} is running and will launch VM-2 {args.vm2_name}.")


if __name__ == "__main__":
    main()
