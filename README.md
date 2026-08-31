# calibre-plugins

My [calibre](https://calibre-ebook.com/) plugins. One folder per plugin, one
installable ZIP per plugin.

## Stylish Cover Generator

Builds real webnovel / dark fantasy covers out of the artwork a book already
has and its metadata, and saves the result as the book cover.

![The four presets of Stylish Cover Generator](stylish-cover-generator/docs/presets-comparison.jpg)

<sub>The same illustration and the same metadata run through the four presets,
with no manual tweaking.</sub>

Four presets, automatic typography, automatic contrast behind the text, full
chinese / korean / japanese support, batch mode and one-click restore of the
previous cover.

**[Documentation and installation →](stylish-cover-generator/)**

## Metadata Tidy

Pulls the series name and the volume number out of titles that carry them
(`La guerre du pavot T1`, `Vagabond part 02`, `Vol. 1: Subtitle`) and fills the
Series and Series index fields, so sorting, grouping and cover generation have
something to work with.

Every change is shown in a preview table before anything is written, rows can
be unticked or corrected by hand, and one menu entry undoes the whole run. It
refuses to guess: a title without a volume marker is left strictly alone.

**[Documentation and installation →](metadata-tidy/)**

## Kobo Cover Pusher

Writes the covers from your calibre library straight into the thumbnail cache
of a connected Kobo, without resending the book files — so a cover change no
longer costs you your reading position, bookmarks and annotations.

A Kobo never reads the cover out of the EPUB: it shows thumbnails it generated
once, which is why a new cover in calibre changes nothing on the device until
something rewrites them.

**[Documentation and installation →](kobo-cover-pusher/)**

---

Requires calibre 6 or later. Tested on calibre 9.13 under Windows 11.
Licensed GPL-3.0, like calibre itself.
