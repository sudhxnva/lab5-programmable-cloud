#!/bin/bash
set -euxo pipefail

metadata() {
    curl -fsS "http://metadata/computeMetadata/v1/instance/attributes/$1" \
        -H "Metadata-Flavor: Google"
}

apt-get update
apt-get install -y python3 python3-pip curl
python3 -m pip install --upgrade google-api-python-client google-auth

mkdir -p /srv/part3
metadata service-credentials > /srv/part3/service-credentials.json
metadata vm1-launch-vm2-code > /srv/part3/vm1_launch_vm2.py
metadata vm2-startup-script > /srv/part3/vm2_startup.sh
chmod 600 /srv/part3/service-credentials.json

python3 /srv/part3/vm1_launch_vm2.py
