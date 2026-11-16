# Licensed historical demonstration dataset

The included JSON contains real historical observations and explicitly derived metrics for France and Croatia at the 2018 World Cup: 42 players, 12 national teams, 13 matches and 195 appearance records. Two late-substitution samples are omitted because they have no reconstructable regulation minutes. This is a subset, not a current football database.

Source: Pappalardo et al. (2019), *A public data set of spatio-temporal match events in soccer competitions*, Scientific Data 6, 236. [Paper](https://doi.org/10.1038/s41597-019-0247-7). [Figshare collection](https://doi.org/10.6084/m9.figshare.c.4415000). Players, Teams, Matches and Events articles are licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Retain this attribution, license link, source manifest and transformation notes when redistributing the subset.

Transformations: select matches involving France or Croatia; include their reconstructable played appearances; calculate age at 15 July 2018; map broad source roles to FW/CM/CB/GK; derive minutes from lineups/substitutions capped at 90 or 120, excluding added time; exclude shoot-outs; count shot/penalty/free-kick-shot events and goal tags; use known formation assist values; count pass events and accuracy tags. Tackles and progressive actions stay null. Goals agree with every available numeric formation goal field. Names are decoded from source Unicode escapes. Unused personal fields are discarded. Team labels are historical national teams, not current professional clubs. Membership intervals represent the demo tournament window and do not claim transfer dates.

`manifest.json` records raw file checksums/DOIs, the subset SHA-256, counts and validation. Definitions differ from commercial providers; no independent official-statistics reconciliation is claimed. Preserve missing-data and small-sample limitations in any presentation.

To reproduce the subset, run `python demo/fetch_sources.py --destination /safe/raw-source`, then `python demo/build_demo.py --source-dir /safe/raw-source`. This explicitly downloads about 80 MB from the public Figshare articles and checks their declared license and checksums. Raw files are not bundled in ScoutIQ.

## Load safely

Create a new empty PostgreSQL database named `scoutiq_demo*`. Set its DATABASE_URL in the process environment. Run Alembic through `python ops/migrate.py`, then create its administrator with `python ops/create_admin.py --username YOUR_NAME --email YOUR_EMAIL`. Its password is entered twice through a hidden terminal prompt. Finally run:

```sh
python ops/load_demo.py --actor YOUR_ADMIN_USERNAME
```

The loader refuses development/production database names and any target containing player or match data. It checks the dataset digest and validates player, match and appearance schemas. An advisory lock and one transaction cover the entire load. It never deletes or overwrites existing records. No account password is bundled. Configure the frontend dataset label as `World Cup 2018 demo · historical national teams · age as of 15 Jul 2018`.

Do not run this loader against the existing development database. The original five records have unspecified redistribution rights and are not included in this demo.
