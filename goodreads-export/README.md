# Goodreads Export

A calibre plugin that writes a CSV **Goodreads' import page accepts** — the
exact columns it expects, with the conversions it needs.

Requires calibre 6 or later. Tested on calibre 9.13 under Windows 11.

## Why not just use calibre's catalogue?

calibre exports CSV on its own (*Convert → Create catalogue*), and that gets
you the data. It does not get you an import, because Goodreads is picky in
ways that are easy to miss:

| | calibre gives | Goodreads wants |
|---|---|---|
| Headers | `title`, `authors`, `rating`, `tags` | `Title`, `Author`, `My Rating`, `Bookshelves` |
| Authors | `Takehiko Inoue & Eiji Yoshikawa & Steve Dutro` | one author it can match on |
| Ratings | 0 to 10, half a star each | 1 to 5 whole stars |
| Dates | `1999-01-01T01:00:00+01:00` | `1999-01-01` |
| Undefined dates | year `101` | empty |
| Shelves | tags joined by commas, inside a comma separated file | shelf names without commas |
| Read status | no such field | one exclusive shelf per book |

This plugin does those conversions. Its column names are checked against the
sample file Goodreads publishes on its import page, by a test that fails if
they ever drift apart.

## Usage

Select some books, then the **Goodreads Export** toolbar button:

| Menu entry | What it does |
|---|---|
| **Export the selected books…** | writes a CSV for the current selection |
| **Export the whole library…** | writes a CSV for every book |
| **Settings…** | shelves, columns and what goes in the file |

Then go to [goodreads.com/review/import](https://www.goodreads.com/review/import)
and upload the file.

The file is written as UTF-8 with a BOM, so accented authors survive both
Goodreads and Excel.

## Shelves

Goodreads keeps **one exclusive shelf** per book — `read`,
`currently-reading` or `to-read` — plus any number of ordinary shelves.

- a tag spelled like one of those three sets the exclusive shelf;
- a **read status column** wins over the tags when you have one. It
  understands a yes/no column, and text like `read`, `lu`, `finished`,
  `reading`, `to-read`;
- every other tag becomes an ordinary shelf, lowercased, spaces hyphenated,
  commas and quotes removed, because Goodreads shelf names cannot hold them;
- when nothing says otherwise, the shelf from the settings is used
  (`to-read` by default).

## Settings

| Option | Default | Effect |
|---|---|---|
| Shelf when nothing says otherwise | `to-read` | the exclusive shelf for books with no read status |
| Read status column | — | a custom column such as `#read` |
| Date read column | — | a date column such as `#date_read` |
| Original publication year | — | a column for the first edition's year |
| Turn tags into shelves | on | off exports no shelves at all |
| Maximum shelves per book | 12 | keeps a heavily tagged library readable |
| Binding | — | `Paperback`, `Kindle Edition`… written on every row |
| Export the comments as your review | off | the description becomes *My Review*, markup stripped |
| Trim reviews to | no limit | cuts long descriptions at a word boundary |
| Skip books that have no ISBN | off | Goodreads matches best on ISBN |

## What it will not do

- **It cannot invent an ISBN.** Without one, Goodreads falls back to title and
  author, which is where webnovels and fan translations usually fail to match.
  Run the import, then check what Goodreads says it could not place.
- **Co-authors are dropped.** The import format has a single Author column,
  so only the first is written rather than a joined string Goodreads would
  fail to match.
- **It does not talk to Goodreads.** No account, no API key, nothing leaves
  your machine — Goodreads stopped issuing API keys in December 2020, and this
  plugin never needed one.

## Licence

GPL-3.0, like calibre itself. Internals in [DEVELOPING.md](../DEVELOPING.md).
