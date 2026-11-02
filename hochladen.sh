#!/bin/bash
# Lädt dieses Add-on-Repository nach GitHub (markus321/ha-doc-addon).
# Aufruf im Terminal:  bash hochladen.sh
set -e
cd "$(dirname "$0")"
[ -d .git ] || git init -b main
git add -A
git commit -m "${1:-HA Doku Add-on}" || echo "Keine Änderungen zum Committen"
git remote get-url origin >/dev/null 2>&1 || git remote add origin https://github.com/markus321/ha-doc-addon.git
git push -u origin main
echo "Fertig. In HA: Add-on-Store → ⋮ → Repositories → https://github.com/markus321/ha-doc-addon"
