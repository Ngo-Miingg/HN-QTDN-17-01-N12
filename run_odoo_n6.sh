#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f "odoo.conf" ]; then
  cp odoo.conf.template odoo.conf
  echo "Created odoo.conf from odoo.conf.template"
fi

python3 odoo-bin.py -c odoo.conf -d "${ODOO_DB:-ttdn_n6_dev}" --http-port "${ODOO_HTTP_PORT:-8071}"
