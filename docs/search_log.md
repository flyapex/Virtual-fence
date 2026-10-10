# Literature-search log

Status: **draft strings prepared; no database search claimed as completed.**
Populate one row per executed search with the exact query copied from the source
interface, database/platform, coverage, date/time, filters, result count and
export file/checksum. Do not replace a live query with a paraphrase.

| ID | Database/platform | Exact draft search string | Planned fields/limits | Executed? | Results | Export/checksum |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Scopus | `TITLE-ABS-KEY((cattle OR cow OR cows OR bovine OR "beef cattle" OR "dairy cattle") AND ("virtual fenc*" OR "virtual boundar*" OR geofenc* OR "GNSS collar" OR "GPS collar" OR "containment system") AND (learn* OR train* OR conditioning OR "associative learning" OR "audio cue*" OR acoustic OR "warning cue" OR "electric pulse" OR stimulus))` | Title/abstract/keywords; inception to search date; no language filter initially | No | — | — |
| S2 | Web of Science | `TS=((cattle OR cow OR cows OR bovine OR "beef cattle" OR "dairy cattle") AND ("virtual fenc*" OR "virtual boundar*" OR geofenc* OR "GNSS collar" OR "GPS collar") AND (learn* OR train* OR conditioning OR "audio cue*" OR acoustic OR "electric pulse"))` | Topic; inception to search date; record indexes searched | No | — | — |
| S3 | CAB Abstracts | `((cattle OR cow OR cows OR bovine) AND ("virtual fenc*" OR geofenc* OR "GNSS collar" OR "virtual boundar*") AND (learn* OR train* OR conditioning OR acoustic OR "audio cue*" OR "electric pulse"))` | Translate syntax in platform; inception to search date | No | — | — |
| S4 | PubMed | `((cattle[Title/Abstract] OR cow[Title/Abstract] OR bovine[Title/Abstract]) AND ("virtual fence"[Title/Abstract] OR geofence[Title/Abstract] OR "GNSS collar"[Title/Abstract] OR "virtual boundary"[Title/Abstract]) AND (learning[Title/Abstract] OR training[Title/Abstract] OR conditioning[Title/Abstract] OR acoustic[Title/Abstract] OR "audio cue"[Title/Abstract] OR "electric pulse"[Title/Abstract]))` | Title/abstract; inception to search date | No | — | — |
| S5 | Scopus (transfer focus) | `TITLE-ABS-KEY((cattle OR cow OR bovine) AND ("virtual fenc*" OR "GNSS collar" OR "virtual boundar*") AND (transfer OR generalisation OR generalization OR pretrain* OR pre-expos* OR "virtual environment" OR immersive OR projection OR "mock pen" OR simulation))` | Title/abstract/keywords; inception to search date | No | — | — |
| S6 | Google Scholar | `cattle "virtual fence" audio pulse learning social facilitation` | Record first 200 sorted-by-relevance results, date, browser and citations checked | No | — | — |
| S7 | Citation chasing | Included-record backward/forward citations, including papers named in the brief | Name seed record and tool/date for each chain | No | — | — |

The user-supplied citations (de Avila et al. 2025; Verdon et al. 2020; Hamidi
et al. 2024; Keshavarzi et al. 2020; Schreiber et al. 2026) are **leads, not
verified bibliography entries** in this repository. Verify title, authors,
journal, year, volume/pages and DOI from the publisher/Crossref before adding
them to `references.bib` or citing them in the thesis.

