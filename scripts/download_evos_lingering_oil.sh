#!/usr/bin/env bash
# Download the Exxon Valdez lingering-oil data (Gulf Watch Alaska / Research Workspace, DataONE).
# Written 14 Nov 2026. Uses only the public DataONE coordinating-node resolve service (no login, no email).
#
# Small files (CSV tables, metadata, SOP PDFs)  -> data/external/evos_lingering_oil/...   (committed)
# Large files (photo PDFs, GIS geodatabase)     -> data/raw/evos_lingering_oil/...        (git-ignored)
# Every file is checked against the MD5 that DataONE publishes for it; a mismatch stops the script.
#
# Run from the repository root:   bash scripts/download_evos_lingering_oil.sh
# Add "small" as the first argument to skip the large files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SMALL="$ROOT/data/external/evos_lingering_oil"
BIG="$ROOT/data/raw/evos_lingering_oil"
ONLY_SMALL="${1:-}"
mkdir -p "$SMALL/2015_survey" "$SMALL/synthesis_2015_2025" "$BIG/2015_photos" "$BIG/synthesis_2015_2025"

fetch() {  # fetch <dataone id> <dest file> <md5>
  local id="$1" dest="$2" md5="$3"
  if [ -f "$dest" ] && [ "$(md5sum "$dest" | cut -d' ' -f1)" = "$md5" ]; then echo "ok (already here) $dest"; return; fi
  local enc; enc="$(python3 -I -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$id")"
  # up to 5 tries; -C - resumes a transfer that was cut off
  local n; for n in 1 2 3 4 5; do
    curl -sSL --fail --max-time 900 -C - -o "$dest" "https://cn.dataone.org/cn/v2/resolve/$enc" && break
    echo "retry $n for $dest"; sleep 3
  done
  local got; got="$(md5sum "$dest" | cut -d' ' -f1)"
  if [ "$got" != "$md5" ]; then echo "MD5 MISMATCH for $dest (got $got, expected $md5)"; exit 1; fi
  echo "downloaded $dest"
}

# --- Dataset 1: doi:10.24431/rw1k1h  (2015 survey, Prince William Sound) ---
D="$SMALL/2015_survey"
fetch 10.24431/rw1k1h                          "$D/metadata_ISO19115_rw1k1h.xml"            7033a7bc9c5b9373518d05f641494771
fetch b26917e2-ac6c-459f-afa3-b3c10d9cf942     "$D/2015_LingeringOil_Survey_Data_final.csv"  65c781f2e4e8650ab73353342354625d
fetch c1365f46-0dfc-4643-bff1-6815d1d766a1     "$D/2015_LingeringOil_Site-Info.csv"          dcd7a8093336f5235de5c52c92831258
fetch 65856b47-4822-4e45-b850-210ff47b0942     "$D/2015_LingeringOil_Gravimetric_Data_final.csv" a55c126690cceae6f7a4c064cefa3a16
fetch c931a689-4050-4017-825e-9e68024ccbfb     "$D/2015_LingeringOil_OilComposition-MDLfiltered.csv" dd2290001256e55ab3dcab5c4486cb46
fetch e251a982-4c12-49cd-8535-f147525f280c     "$D/2015_LingeringOil_ChainOfCustody_samples.csv" 4e3706028bf301dddacfcc3660ddc03a
fetch 704f1c17-25c8-4877-9ee8-f9b4f37a7e39     "$D/Lingering_oil_survey_SOP_January_2017.pdf" 8539b53cb1f10013627b26bee7457462
fetch 1e363b23-0321-4bd3-9044-8d9b740e5c44     "$D/Analysis_of_Petroleum_Hydrocarbons_SOP_May_2016.pdf" 9f26547e71ae0aff8624e7a8bc499304

# --- Dataset 2: 10.24431/rw1kaio  (2015-2025 synthesis: test-pit status of beach segments) ---
S="$SMALL/synthesis_2015_2025"
fetch 10.24431_rw1kaio_20260611T235727Z        "$S/metadata_rw1kaio_20260611.xml"            fcdc22b1d49102a8c1de0786e4ab36e0
fetch 3e9888dd-5f06-4266-9dac-2e36f89b63e2     "$S/EVOS_2026_Lingering_Oil_Status.csv"       158bd8fc5dbe5cf0ae7faa2de96c3b4c
fetch fff522b6-8257-4be6-bad0-1e3cfcdbaba2     "$S/Data_Dictionary_rw1kaio.xml"              675382e9302b3ac230382da8929616d1
fetch 4ea3b298-a3b6-43c1-928d-d941282e41ce     "$S/EVOS_GIS_Package_Description.pdf"         52e32ec8483503a1db798d8ab8650600
fetch b5ec88d8-0013-476a-9c92-a6631a9cf0a9     "$S/Technical_Approach_Lingering_Oil_June_2025.pdf" a2e09e83928045426ac0139dbbf30621
fetch d17b9547-710d-443d-b8e9-15d7d5964e26     "$S/Listing_Methodology_Lingering_Oil_June_2025.pdf" 267f151c03b7143505d25853cb610342
fetch 62e628af-f47b-4d07-bc78-f2e05c283198     "$S/Public-Notice-Version-26IR-cat-4b-EVOS.pdf" b07130020d360cf0eb8046db6927c3cc

[ "$ONLY_SMALL" = "small" ] && { echo "small files done"; exit 0; }

# --- Large files, kept out of git ---
fetch 3197ddff-5fcb-4fb4-9a17-89cada00259f     "$BIG/synthesis_2015_2025/EVOS_GIS_LM_Public_Notice_Version.gdb.zip" d930aeca7ebea036cc890ba0a6aa9654
P="$BIG/2015_photos"
fetch b968f7c0-7128-404e-b311-364bb69d4176 "$P/2015_GR103B_photos.pdf"   696872c5156271af7bf7d4abe2db23eb
fetch 1f531da8-896e-4865-8d47-eb6dec32df2a "$P/2015_KN0114A_photos.pdf"  7c0ee375168f9266744df12c8d0507b9
fetch 19fa2c18-111e-4a85-a0ac-e3f2e2a84044 "$P/2015_SM006B_photos.pdf"  e8f4286fccbd20344381260fb3d1aae3
fetch c15fa2d3-39c4-40b0-a251-63c2444240ab "$P/2015_LA018A-1_photos.pdf" 763b231c838f507e55ec4c48b414237e
fetch 3d9f6233-664b-481e-b5c7-5cbcbcae823c "$P/2015_EV039A_photos.pdf"  5256980848928cc52d4cce9937b29b63
fetch 08565be4-e1ef-44a5-8ca7-e32475302b19 "$P/2015_EL058B_photos.pdf"  7ef0d6f7885aaca0d16c790c62ea2ccc
fetch 3192416c-01e9-4192-9993-302400dc3c2c "$P/2015_EL056C_photos.pdf"  9287699253ea354755b00cccd84c707a
fetch d27c55e2-f8b7-4bb6-8c88-e3b17ed1b91e "$P/2015_KN0506A_photos.pdf" 82e17cf6b4e287844b4f4a334b8813d6
fetch ce62b066-295e-4246-9c75-2c67491acd06 "$P/2015_KN0300A-2_photos.pdf" 234b8811fa43bc3612ecdecef1b7bf22
echo "all done"
