# Cross-Check

A calibre **metadata source** that queries several free APIs at once, compares
what they say, and hands the result to the *Download metadata* dialog you
already use.

No API key, no account, no configuration needed to start.

Requires calibre 6 or later. Tested on calibre 9.13 under Windows 11.

## Why

The sources calibre ships answer well for published books and badly for manga,
light novels and web novels. Asked about *Lord of the Mysteries*, Amazon
offers **Love the Food that Loves You Back**, a diet cookbook.

Cross-Check answers:

| | |
|---|---|
| Title | Lord of the Mysteries |
| Original title | 诡秘之主 |
| Author | Ai Qianshui de Wuzei |
| Year | 2020 |
| Tags | Action, Drama, Fantasy, Mystery, Thriller |
| Confirmed by | AniList, MangaDex, Kitsu |

And it does not lose the books calibre already handled: *Le colonel Chabert*
comes back as **Honoré de Balzac**, accent included, confirmed by the BnF and
Open Library.

## The sources

| Source | Covers | On by default |
|---|---|---|
| **AniList** | manga, manhwa, manhua, light novels, web novels — with native titles | yes |
| **MangaDex** | manga and manhwa, many titles per language | yes |
| **Kitsu** | manga and light novels, a useful second opinion | yes |
| **MyAnimeList** (through Jikan) | manga and light novels | no — it frequently answers HTTP 504 |
| **Open Library** | published books: authors, year, publisher, subjects, ISBN | yes |
| **BnF** | the French national library: french editions and small french publishers | yes |

Google Books is deliberately absent: without an API key it answers HTTP 429
from a shared anonymous quota, so it would fail more often than it helps.

## How the cross-check works

All sources are queried in parallel. Answers describing the same work are
grouped, even when they spell it differently — `86: Eighty Six`,
`86—EIGHTY-SIX` and `86 EIGHTY SIX` are one work, and so are `Gu Zhenren` and
`Gu Zhen Ren`.

Within a group:

- **title, author, year, publisher, native title**: the value the most
  sources agree on;
- **tags**: the union of all of them, capped, so you prune rather than hunt;
- **description**: the longest one, being the most informative;
- **language**: voted on rather than merged, so a spanish and a french edition
  in the results do not make a japanese manga trilingual.

Each result carries a line saying who confirmed what:

```
Cross-check: 5 source(s) - AniList, BnF, Kitsu, MangaDex, Open Library.
Agreed on: languages, native_title, title, year.
```

**Nothing is dropped for lack of consensus.** A field a single source knows is
still filled in — you review everything in calibre's dialog anyway. Agreement
only decides which result is offered first and what that line says. The one
exception is noise: a result backed by a single source whose title has almost
nothing in common with what you searched is discarded.

## Usage

1. Install, then restart calibre.
2. **Preferences → Metadata download**, and make sure *Cross-Check* is ticked.
3. Select books, then **Edit metadata → Download metadata**.

calibre queries every enabled source, Cross-Check included, and shows you the
results to compare and pick as usual. Nothing is written to your library
without you choosing it.

The original title appears at the top of the description, so it can be copied
into a column such as `#original_title` — which
[Stylish Cover Generator](../stylish-cover-generator/) reads for its Asian
subtitle.

## Settings

**Preferences → Metadata download → Cross-Check → Configure**: tick the
sources you want, cap the number of tags, and adjust how similar two titles
must be to count as the same work.

## Licence

GPL-3.0, like calibre itself. Internals in [DEVELOPING.md](../DEVELOPING.md).
