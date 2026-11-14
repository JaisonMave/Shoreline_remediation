# Exxon Valdez lingering oil data (Gulf Watch Alaska, Research Workspace via DataONE)

Fetched 14 Nov 2026 by `scripts/download_evos_lingering_oil.sh` (public DataONE resolve service, no login, no email).
Every file was checked against the MD5 that DataONE publishes. Licence: not stated on the DataONE records read here;
public data of the Exxon Valdez Oil Spill Trustee Council Gulf Watch Alaska programme (state/federal funded). Cite the DOIs below.
Not read or cleaned by this agent: the files are as downloaded. How read: DataONE Solr query on the resource map to list members, then resolve each PID.

## Dataset 1: DOI 10.24431/rw1k1h (folder `2015_survey/`)
"Lingering Oil Measurements, Site, Sample, and Photographic Data from Prince William Sound, 2015, Gulf Watch Alaska Lingering Oil Component".
Survey/pit table, site info, gravimetric oiling, oil composition (MDL filtered), chain of custody, two SOPs. The nine per-site photo PDFs
(about 78 MB) are in git-ignored `data/raw/evos_lingering_oil/2015_photos/`. The DOI landing page is a JavaScript viewer; the CSV files come only via the REST resolve call.
The earlier 2001/2003/2005 pit surveys are NOT in this record (compared inside the Lindeberg 2018 report, `docs/reference/literature/`).

## Dataset 2: DOI 10.24431/rw1kaio, version of 11 Jun 2026 (folder `synthesis_2015_2025/`)
"Lingering Oil Assessment Methodology for Prince William Sound Beach Segments, 2015-2025" (Alaska DEC listing methodology; synthesis of test-pit data from published and agency projects,
segment status CSV, data dictionary, methodology PDFs). The 16 MB geodatabase zip is in `data/raw/evos_lingering_oil/synthesis_2015_2025/`. The record says a public comment period was due in spring 2026: treat as DRAFT agency analysis.

## Committed files (SHA-256)
| file | bytes | sha256 |
| --- | --- | --- |
| `2015_survey/2015_LingeringOil_ChainOfCustody_samples.csv` | 14,702 | `d98be21c34dedc43ea8339c7d15af075a24370f0c3a72cb58e63e42ba56d9b83` |
| `2015_survey/2015_LingeringOil_Gravimetric_Data_final.csv` | 5,451 | `5bb8e05203c4a2f75056d247c55a5a62bd565624fbedce9eafc0a58089e3d5e9` |
| `2015_survey/2015_LingeringOil_OilComposition-MDLfiltered.csv` | 26,680 | `f74e6de3b2fa85ea925b12106d213a26c2614b4d3d02377f80015245a6a3e807` |
| `2015_survey/2015_LingeringOil_Site-Info.csv` | 1,381 | `4200eba4e770889a0dc520cbcc27b28d7ee6337e7b20adfc6e26627ea66e8997` |
| `2015_survey/2015_LingeringOil_Survey_Data_final.csv` | 23,060 | `8bfedfae6db60b0b159163392c0997f2739963100e5da4e2ae9645d904d68ca9` |
| `2015_survey/Analysis_of_Petroleum_Hydrocarbons_SOP_May_2016.pdf` | 2,228,067 | `356675ff2b41bf9df2e257b6c7a521ebbe464eaf6c700f0c3e0904ace6e13045` |
| `2015_survey/Lingering_oil_survey_SOP_January_2017.pdf` | 5,493,570 | `f8ec058deb4e4fde91391fe08b759718eba03bcebc44020243172b145d11e718` |
| `2015_survey/metadata_ISO19115_rw1k1h.xml` | 75,739 | `01f5c515466f0af1cfc04d560c70ff7c0230461d7d0a12848ee3532e987042f1` |
| `synthesis_2015_2025/Data_Dictionary_rw1kaio.xml` | 17,669 | `caee5015c7c3ab6b7a19dc1817804c6e0f247b31d68dead9941af14e1971d403` |
| `synthesis_2015_2025/EVOS_2026_Lingering_Oil_Status.csv` | 135,043 | `15d73e8c6430ae436faf842bea91b565880a5ee1431da2541d8a2ff918ba63af` |
| `synthesis_2015_2025/EVOS_GIS_Package_Description.pdf` | 343,195 | `4d6704522837a144af2eccc9b2fc4964c5e7d76918f639c95c94f172cf30ec03` |
| `synthesis_2015_2025/Listing_Methodology_Lingering_Oil_June_2025.pdf` | 394,596 | `56e0ffdf6e2c2e2a63e3ede7008a5977bc2f7b2e6440f77829160ff00053f86d` |
| `synthesis_2015_2025/Public-Notice-Version-26IR-cat-4b-EVOS.pdf` | 1,993,947 | `30d1db2c8fb2e8a4fb57b77d657cbbad023e479e8d7722898797c237ae1cfd04` |
| `synthesis_2015_2025/Technical_Approach_Lingering_Oil_June_2025.pdf` | 875,082 | `e5ae543c749c8c28382f7f12777a1ead3074d7c7fc4e3a9377130fb463c4ec19` |
| `synthesis_2015_2025/metadata_rw1kaio_20260611.xml` | 29,327 | `0d7eb6af6bb15356575132d7f4a5446f0af5ea2e65f7cb57b94e4a87f7e7bc5d` |

## Git-ignored files in data/raw/evos_lingering_oil/ (SHA-256)
| file | bytes | sha256 |
| --- | --- | --- |
| `2015_photos/2015_EL056C_photos.pdf` | 19,527,987 | `1904e79e00ee0dbe5507db567172c2a9d4b5d42a741ba2959e1e8bc8344433db` |
| `2015_photos/2015_EL058B_photos.pdf` | 9,077,022 | `24b167d219b0d32268ef8432ceb8d59b304ac1e86b8f5ba9890a369cd730c9fa` |
| `2015_photos/2015_EV039A_photos.pdf` | 8,192,996 | `fe1113f677a1fc33f7b16807634b94ca8ee981730450712bb9fcc5c22c0a12ff` |
| `2015_photos/2015_GR103B_photos.pdf` | 10,765,264 | `da360e4d05310290d25eb27069e559b09a2fa9b3cc17a2f8bc2454ed84540909` |
| `2015_photos/2015_KN0114A_photos.pdf` | 11,338,283 | `520fd84789183b6839f6451388efe46272503a4fb62aea1bc4973bb5ec59d695` |
| `2015_photos/2015_KN0300A-2_photos.pdf` | 2,230,678 | `7ce2c8064d8be36efe1581b2377d18cab94a503a31e8bba9e1538e4d5ba9c25a` |
| `2015_photos/2015_KN0506A_photos.pdf` | 5,213,044 | `c42975498c95d1a41475c6a0722dfeb821ee88e2a25411661e56d5a3c5d0f1cb` |
| `2015_photos/2015_LA018A-1_photos.pdf` | 3,905,610 | `1287162dd569725689e09548c86f41b7f712886569c8312f84e1d76583bf6287` |
| `2015_photos/2015_SM006B_photos.pdf` | 8,481,618 | `33560dc251cdea8dc32e263701004fa19970d91eab0689296ef194e53c15e9d3` |
| `synthesis_2015_2025/EVOS_GIS_LM_Public_Notice_Version.gdb.zip` | 16,263,348 | `2fe5dffcce61f12896d6d21ae5b9b0379cc6ff4b9e8d000b6c9e9daa86f80f52` |
