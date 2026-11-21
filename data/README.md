# data/

This folder is **not versioned** (see `.gitignore`). It is filled by the scripts in `scripts/`:

| Subfolder | Content | Created by |
|---|---|---|
| `raw/msha/zips/` | Original MSHA zip files (about 414 MB for the 9 sets used) | `scripts/01_download_msha.py` |
| `raw/msha/<Set>/` | Each zip extracted in its own folder | `scripts/01_download_msha.py` |
| `raw/msha/definiciones/` | MSHA data dictionaries (`*_Definition_File.txt`) | `scripts/01_download_msha.py` |
| `csv/<company>/` | Tables filtered to one company, UTF-8 CSV | `scripts/02_filter_company.py` |
| `load/` | UTF-16, pipe-delimited copies of the CSV files, read by `BULK INSERT` inside the container | `scripts/04_load_sqlserver.py` |
| `manifest.json` | Download date, sizes and row counts of the snapshot | the scripts above |

MSHA replaces its files completely every Friday, so row counts change over time. Tests compare against `manifest.json`, not against fixed numbers.

Source: U.S. Mine Safety and Health Administration (MSHA), Open Government Data Sets. This project is independent and is not affiliated with MSHA or Freeport-McMoRan.
