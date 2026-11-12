#!/usr/bin/env bash
# Re-fetch the NCEI accession 9400033 data folder (Bahia Las Minas / Galeta, Panama 1986 oil spill; MMS 93-0048 files)
# used by Phase C1 (scripts/galeta_description.py). NOT run when written. Licence is unclear (catalogue says CC0 but
# access level "non-public"), so the files are NOT committed (data/raw/ is git-ignored).
# The accession landing page and bulk download returned 503 on 2026-11-12; the directory index below worked
# (path from the index page title). Listed: 25 files, about 7.7 MB. Not fetched: mgrl_m.txt and the grs/rfl/sna/sre sets.
# Usage: scripts/download_galeta.sh [outdir]   (default data/raw/galeta_ncei_9400033/data)
# After the download, sha256 values are compared with those recorded on 2026-11-12 (docs/MANGROVE_INVENTORY.md).
set -euo pipefail
OUT=${1:-data/raw/galeta_ncei_9400033/data}
B=https://www.ncei.noaa.gov/data/oceans/archive/arc0001/9400033/1.1/data/0-data
mkdir -p "$OUT"
for f in mgf.doc mgfd_m.txt mgfl_m.txt mgfs_mx.txt mgft_m.txt mgr.doc mgr_s.txt mgrb_m.txt mgrc_m.txt mgre_m.txt \
         mgrg_m.txt mgrp_m.txt mgrq_m.txt mgrr_m.txt mgrs_m.txt mgrt_m.txt mgrv_m.txt mgrw_m.txt mgrz_m.txt \
         sto.doc stoa_m.txt stob_m.txt stoc_m.txt stod_m.txt stri_os.doc tableofcon; do
  curl -fsS --connect-timeout 30 --max-time 600 -o "$OUT/$f" "$B/$f"; echo "$f"
done
cd "$OUT"
sha256sum -c - <<'SUMS'
450209a9157f0b66887076b94bd5479271e952c96452e66e8f97b823fe5d687a  mgf.doc
c4a333916ffbdaceb7af259130626b0cb3c8a3009b438d00fc5ca1ee62ad0992  mgfd_m.txt
1399bbfdde99180bde980b22d07617b1baa3b7fe65144c98d0a72447321b1bc8  mgfl_m.txt
59270ae2d67ee696f8908091d1894d8ea0ac2658f24ec4db5d744a226b399d8c  mgfs_mx.txt
dc0969abe5c275f3255af5f15a41b9a6788cc955fe98e1ec6b82bcc7c7d36160  mgft_m.txt
3daa9e2a56a4fb60dc92c29bf4a61019f76e034dfad9b4656e02e0c541bdca2f  mgr.doc
1b7e1c201cac7139ceb3f0f91da02adeb34acda014f85de13294111caa2cab69  mgr_s.txt
ec93febe9bb9e5f52fda0e79085ae02a0cdf59e26600741231b2121a95287132  mgrb_m.txt
6dbd4c865eb3c2283af7d4530c62b6d628ef874521882cf3079a1ecd8d291a8d  mgrc_m.txt
d6a29209a9f258594aeb834d2423eda43d1d96ee2c7273107d20977c3a6817e8  mgre_m.txt
03e7460a6fee087b5af41818d6328f555d5b3c653e2c3bd9bf3b95ce45fdf368  mgrg_m.txt
697ea54cee737b9df55fb254ac688c9646afbf045d146d66cefc0927dba39e58  mgrp_m.txt
63096336de7c9ffbfe38a5b5628eb542b3eb7b92265f93b256b503b192f120af  mgrq_m.txt
3b6c30b5e0187c15991548cec1e58529e081c42fcc641cb7e52938f3ddac82bc  mgrr_m.txt
0fa04d94632ce3029e9905570368ec2c80b9a8f20baa6761296007c0268bc477  mgrs_m.txt
36f4193db5d1400e8e25a910fd4d2c3a2e8eafda665126a0fd1af6b2672653a6  mgrt_m.txt
810e43546f7cdd7a9901f3a17a2e836464ef8749e60c49cf01853c3c8ec5bb76  mgrv_m.txt
e8e84416a1d5015fa92cced79139a74b9b6c94374ac00d3fefcc391d0a87df96  mgrw_m.txt
9d360541c4896ff7f4ef89252fd5efbcd7cef4ad4a34a41cec030e285e66f8c9  mgrz_m.txt
79bf262a3741d014871e110195b66e3aa06c0a09c14cdfee3132a596d927645e  sto.doc
f636656bd80ce2fb2cf9060aff37a7f110f42e1d748edf80016ceb0f88737352  stoa_m.txt
eae8cd2c9dd9585dbfd1eea613635b89cb3c7fcaea81f6e7c48e2147750ecbd6  stob_m.txt
ffac165e0cbc712117d67f2278684871f6cfbbb73bd89897da794941442e2285  stoc_m.txt
00856e3b1d75d49de079215636c93799ee56e572a18527059a5a24b11375fb32  stod_m.txt
d8cf26bbfe1bd8d2cf214408be5c7e2e77a5df446b44d2fe00d9196c4a6c8e35  stri_os.doc
38f8261ee42cdfe5821ae7d3e14255ecad5af60737743d9790bde45efc03940a  tableofcon
SUMS
