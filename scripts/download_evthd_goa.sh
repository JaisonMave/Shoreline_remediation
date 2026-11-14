#!/usr/bin/env bash
# Download the Exxon Valdez hydrocarbon database (EVTHD, 2014 version) as published on the Gulf of Alaska
# Data Portal / DataONE: "Analysis of hydrocarbons following the Exxon Valdez oil spill, Gulf of Alaska, 1989-2014".
# Metadata PID urn:uuid:3249ada0-afe3-4dd6-875e-0f7928a4c171 (member node urn:node:GOA). Written 14 Nov 2026.
# Public DataONE resolve service only; no login or email. Each file is checked against the SHA-1 DataONE publishes.
# Run from the repository root:  bash scripts/download_evthd_goa.sh      Output: data/external/evthd_goa/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$ROOT/data/external/evthd_goa"; mkdir -p "$D"
fetch() { # pid file sha1
  local pid="$1" f="$D/$2" sha="$3"
  if [ -f "$f" ] && [ "$(sha1sum "$f" | cut -d' ' -f1)" = "$sha" ]; then echo "ok (already here) $2"; return; fi
  local enc; enc="$(python3 -I -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$pid")"
  local n; for n in 1 2 3 4 5; do curl -sSL --fail --max-time 600 -C - -o "$f" "https://cn.dataone.org/cn/v2/resolve/$enc" && break; echo "retry $n"; sleep 3; done
  [ "$(sha1sum "$f" | cut -d' ' -f1)" = "$sha" ] || { echo "SHA-1 MISMATCH $2"; exit 1; }
  echo "downloaded $2"
}
fetch urn:uuid:3249ada0-afe3-4dd6-875e-0f7928a4c171 metadata_EML.xml acd7e08524fff623123c879427c69ee025ef050e
fetch urn:uuid:5cde46ff-2e8e-4f40-97a1-eb4c4851f22f PAH.csv 9d33d7d966314577e4025330dffc6c4c4adcf5eb
fetch urn:uuid:d31ea97c-e061-43f8-af06-62664671f166 Alkane.csv 82afbae4ebec41c7dbece20800699b755af90ebd
fetch urn:uuid:44108e76-405d-4d58-b1b3-fb4b55e3fff9 Total_Aromatic_Alkanes_PWS.csv 53473dd8b5ab7aee559915d55d6ec8ba112c4917
fetch urn:uuid:5f57c5d3-65f2-4d46-83f5-67f8104c62dd Sample.csv b1d5b49a4fdd25fe55859e9e4f3373bc830237f7
fetch urn:uuid:66c416af-84e6-4c7e-92a9-4413cf8acd7b CollectionMethods.csv 7d72ce360e8984e74babf56f8d52e7267bbfc253
fetch urn:uuid:ae595730-172a-43d0-91f8-3173663d7dce Non-EVOS_SINs.csv 9d901148ece56fd1d94bcb342dff62f6e223f033
echo done
