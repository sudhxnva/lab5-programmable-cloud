#!/usr/bin/env python3
"""Runs on VM-1 and launches Flask VM-2 using the supplied service account."""

from pathlib import Path

import googleapiclient.discovery
from google.oauth2 import service_account


METADATA_URL = "http://metadata/computeMetadata/v1/instance/attributes/"
HEADERS = {"Metadata-Flavor": "Google"}
NETWORK = "global/networks/default"
IMAGE = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts"


def metadata_value(name):
    import urllib.request

    request = urllib.request.Request(METADATA_URL + name, headers=HEADERS)
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def main():
    base = Path("/srv/part3")
    credentials = service_account.Credentials.from_service_account_file(
        base / "service-credentials.json"
    )
    project = metadata_value("project")
    zone = metadata_value("zone")
    vm2_name = metadata_value("vm2-name")
    machine_type = metadata_value("vm2-machine-type")
    startup_script = (base / "vm2_startup.sh").read_text(encoding="utf-8")
    compute = googleapiclient.discovery.build("compute", "v1", credentials=credentials)
    body = {
        "name": vm2_name,
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
    compute.instances().insert(project=project, zone=zone, body=body).execute()


if __name__ == "__main__":
    main()
