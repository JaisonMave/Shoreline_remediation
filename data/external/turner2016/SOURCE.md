# Turner et al. island erosion data, Barataria Bay, Breton Sound and Terrebonne Bay

- File: `R4.x264.196.0008_data to Jason islands.2.xlsx` (name as served, copied unchanged).
- Dataset: "Erosion Rates of Islands in Barataria Bay, Breton Sound, and Terrebonne Bay, 1988-2013", GRIIDC,
  doi:10.7266/N72J68WS, UDI R4.x264.196:0008 (GRIIDC dataset id 2486). Authors and publication date: not checked.
- URL: https://data.griidc.org/data/R4.x264.196:0008
- Licence: CC0, from the JSON-LD `license` field on the GRIIDC landing page. The visible licence wording was not
  found on the page; GRIIDC "Terms & Conditions" (https://www.griidc.org/terms-and-conditions) was not fetched.
- Acquired 2026-11-12 (an identical copy had been read earlier). How obtained: https://data.griidc.org/download/dataset/2486
  returned a zip (20,776 bytes, SHA-256 11c944cdd3cec0100c1a3d04d511f07689295db69f4229782a3e56a6fc414fab); the
  single workbook was extracted and copied unchanged. Read with pandas/openpyxl only.
- SHA-256 of the xlsx: 3cb9ffcccb6f710b978d38d9c6f782928c6590b5c11f867c1965c500147aeb06.
- Sheets: Sheet1 (island width, m east-west), Sheet2 (island length, m north-south), Sheet3 (image precision).
- Known problems:
  - Sheet1 has 41 island rows and Sheet2 has 46 (Terrebonne Bay 5 vs 10); not resolved. The landing text says 46 islands.
  - Headers are spread over several rows of text and some labels are truncated; column names need a manual mapping.
  - The SCAT colour column mixes codes and free text; the numeric Category column (1 unoiled, 2 oiled) is cleaner.
  - Latitude/longitude are degrees and minutes in Sheet1 and Sheet2; datum not stated. Rate units (m/y) are taken
    from the landing text, not from the cells.
  - Landing date range 1988-01-01 to 2012-12-31 differs from the title (1988-2013).
