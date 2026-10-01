#!/bin/bash
set -euxo pipefail

apt-get update
apt-get install -y python3 python3-pip git
git clone https://github.com/cu-csci-4253-datacenter/flask-tutorial.git /opt/flask-tutorial
cd /opt/flask-tutorial
python3 setup.py install
pip3 install -e .
export FLASK_APP=flaskr
flask init-db
nohup flask run --host=0.0.0.0 > /var/log/flask.log 2>&1 &
