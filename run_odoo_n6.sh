#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
/mnt/d/Work/HocKy3/Enterprise_software_integration_and_management/Business-Internship/venv/bin/python odoo-bin.py -c odoo.conf -d ttdn_n6_dev
