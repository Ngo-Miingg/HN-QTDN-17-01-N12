param(
    [string]$Database = "ttdn_n6_dev",
    [int]$HttpPort = 8071
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Set-Location -LiteralPath $root

$existingContainer = docker ps -a --filter "name=^/postgres_odoo-base-15-01$" --format "{{.Names}}"
if ($existingContainer) {
    docker start postgres_odoo-base-15-01 | Out-Null
} else {
    docker compose up -d postgres-odoo-base-15-01
}

python odoo-bin.py -c odoo.conf -d $Database --http-port $HttpPort -u nhan_su,quan_ly_van_ban,event_meeting_room_extended,dnu_meeting_asset --stop-after-init
python odoo-bin.py -c odoo.conf -d $Database --http-port $HttpPort
