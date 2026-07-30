# Source snapshots

`manifest.json` is the machine-readable source contract.

## Canonical inputs

### ISTAT

`snapshots/istat/Elenco-comuni-italiani-2026-02-21.xlsx`

- URL: <https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx>
- reference date: 2026-02-21
- SHA-256:
  `83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5`
- attribution: ISTAT, CC BY 4.0

### GeoNames

`snapshots/geonames/IT-2026-07-30.zip`

- URL: <https://download.geonames.org/export/zip/IT.zip>
- download index/README: <https://download.geonames.org/export/zip/>
- acquired: 2026-07-30T09:36:42Z
- source Last-Modified: 2026-07-30T01:44:40Z
- SHA-256:
  `08cf5625f70952ba9c0a126b0af20a048a0e4dad8f6ca60deda5b612d100e7bc`
- attribution: GeoNames, <https://www.geonames.org/>, CC BY 4.0
- format: `IT.txt`, 12 tab-separated UTF-8 fields, plus `readme.txt`

The pipeline reads the ZIP directly after checksum verification. Do not
replace the dated snapshot in place.

GeoNames is not Poste Italiane. Its README says coordinates can be determined
or estimated algorithmically and the data is provided without warranty.

## Auxiliary geographic input

`cache/Limiti01012026_g.zip` is the checksum-pinned ISTAT generalized
administrative-boundary archive dated 2026-01-01. It is not a canonical
dataset input: it only rebuilds `site/assets/italy-regions.geojson`. The
archive is committed so CI can prove the web map is reproducible without
silently skipping the source rebuild.

## Withdrawn historical material

Pre-clean-room material with unresolved provenance and redistribution rights
has been removed. It is not declared by the manifest and must not be restored
as an input, baseline, report fixture or release asset.

## Update procedure

Download a new snapshot to a new dated path, record headers/timestamps and
SHA-256, update `manifest.json`, regenerate all outputs and review the
deterministic reports. Never edit a snapshot or generated output manually.
