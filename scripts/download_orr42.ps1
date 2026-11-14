# Download NOAA TM NOS OR&R 42 (Zengel and Michel 2013). About 17 MB.
# The NOAA Institutional Repository returned HTTP 403 to curl from this host on
# 14 Nov 2026; the HTML landing page opened in a browser. Run this in an
# interactive session, or download the PDF by hand from the landing page.
# Usage: powershell -File scripts/download_orr42.ps1 [outdir]
param([string]$OutDir = "data\external\dwh_treatment")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$dest = Join-Path $OutDir "NOAA_TM_NOS_ORR_42.pdf"
$url = "https://repository.library.noaa.gov/view/noaa/380/noaa_380_DS1.pdf"
$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
Write-Host "GET $url"
& curl.exe -L -A $ua -e "https://repository.library.noaa.gov/view/noaa/380" --max-time 180 -o $dest $url
if (-not (Test-Path $dest)) { throw "download failed" }
$len = (Get-Item $dest).Length
if ($len -lt 1000000) { throw "file too small ($len bytes); NOAA IR likely returned 403 HTML" }
Write-Host "saved $dest ($len bytes)"
Write-Host "expected about 17713154 bytes; landing-page sha-512 is in data/external/dwh_treatment/SOURCE.md"
