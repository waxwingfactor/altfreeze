# altfreeze

**Keep EPUB image-description approvals attached to the source that was reviewed.**

altfreeze helps small university-press production editors coordinate human review of short image descriptions in vendor-delivered EPUB 3 files. Export a private, self-contained review page; get attributed decisions back; apply them to the exact source; then reconcile the next vendor revision into an explicit re-review queue.

A chapter-only correction reopens that chapter's decisions. A changed raster or shared resource reopens all decisions. A valid publication modification timestamp alone does not reopen them. These conservative rules avoid filename-based or fuzzy approval matching.

This is an editorial workflow tool. It does not generate descriptions, certify accessibility, or replace EPUBCheck, Ace, expert description writing, or reading-system checks. [Supported scope and limits](docs/contract.md) are part of the product.

## Install

Requires Python 3.10–3.14. Download the wheel and `SHA256SUMS` from the [public release](https://github.com/waxwingfactor/altfreeze/releases/latest), verify the checksum, then:

```sh
python -m venv .venv
# Activate .venv using your platform's normal activation command.
python -m pip install ./altfreeze-1.0.0-py3-none-any.whl
altfreeze --version
```

Use the environment's `python -m pip` after activation. Installation obtains Pillow from the Python package index. All review, validation, application and reconciliation operate locally without a server or network after installation. There is no hosted account or paid API. The source distribution includes examples, docs and tests.

## Review and apply

```sh
altfreeze export book.epub --out review
```

Open `review/review.html` directly in Chrome or Edge. It contains raster previews, captions, extracted nearby prose, expandable full chapter text and a decision form. It is an editorial proof sheet, not a rendered EPUB. Keep the source EPUB and `snapshot.json`; send the HTML file to the reviewer using your normal approved file-transfer process.

For each occurrence, choose Keep, Replace, Decorative, or Needs work. Keep requires existing nonblank text. Replace requires new text. Decorative requires an explanation. Approved decisions need a reviewer name. Save partial work as Pending or Needs work. There is **no autosave**: use **Save decisions JSON**, check the download, and load that JSON to resume. The page cannot know whether the browser completed a download.

```sh
altfreeze check book.epub review --decisions returned.json
altfreeze apply book.epub review --decisions returned.json --out final
```

`check` and `apply` refuse unresolved decisions. Use `check --allow-incomplete` only to validate a saved draft. Every output directory must be new, with an existing parent.

A successful apply writes:

- `final/publication.epub`: the separately written publication.
- `final/receipt.json`: input/output hashes, exact human decisions and changed entries.
- `final/review/`: a complete review baseline bound to the **output** EPUB, ready for the next vendor round.

Run EPUBCheck, Ace and your usual reader/editorial QA on the output. Editing XHTML reserializes changed documents and can normalize namespace prefixes, quotes and empty-element syntax. Untouched entry contents stay identical. The archive is rewritten; ZIP bytes and signatures are not preserved. Signed/encrypted inputs are rejected.

## Reconcile a vendor correction

If review is still in progress against the original:

```sh
altfreeze reconcile book.epub review vendor-revised.epub \
  --decisions returned.json --out next-review
```

After application, use the new baseline:

```sh
altfreeze reconcile final/publication.epub final/review vendor-revised.epub \
  --out next-review
```

`next-review/reconciliation.json` records retained, invalidated, new and removed occurrence decisions. Invalidated/new items return to Pending. Prior text is retained in the ledger for inspection, never silently approved. Open `next-review/review.html`, finish review, and apply it to `vendor-revised.epub`. Unchanged pending decisions remain pending.

Reconciliation requires the same publication identifier. It compares document path and occurrence index, complete chapter bytes, image bytes and conservative shared context. A harmless whitespace change can reopen an entire chapter. A reordered/replaced image never receives another occurrence's approval merely because its filename matches. Cross-chapter meaning still requires editorial judgment.

## Try the included example

The [CC0 synthetic orchard example](examples/README.md) demonstrates two uses of one raster in different contexts, a vendor prose correction and an updated modification timestamp. Source releases contain the EPUBs and generator.

```sh
python examples/make_demo.py demo
altfreeze export demo/orchard.epub --out demo/review
```

## Scope and evidence

The supported scope is single-rendition, reflowable EPUB 3 with ordinary, local PNG/JPEG XHTML `img` occurrences, within bounded file/pixel limits. Ambiguous image roles, names, linked/functional images, extended-description attributes, SVG, responsive images, active media, DRM and fixed layout fail clearly. An empty image inventory means no supported `img` occurrences; it is not an accessibility pass.

- [Exact input/output contract, limits and recovery](docs/contract.md)
- [Dated research, alternatives, positioning and constructed scenarios](docs/research.md)
- [Adversarial competition assessment](docs/competition.md)
- [Independent AI reviews and validation evidence](docs/validation.md)
- [Public issues](https://github.com/waxwingfactor/altfreeze/issues)

The opportunity is an informed hypothesis based on documented human publishing QA and proof cycles. No customer interviews, reference customers, adoption or measured savings are claimed. Tools including SIDD, InDesign, Sigil, Fido, HoloPress and ATAR are credible alternatives.

## Development

```sh
python -m pip install -e . pytest build
python -m pytest -q
python -m build
```

The CLI prints one JSON result. Success is exit 0; input, unsupported-scope and operational failures are exit 2. `python -m altfreeze` provides the same interface. Library entry points are in `altfreeze.core`; `Error` represents invalid or unsupported content, while filesystem failures may raise `OSError`.

MIT licensed. The generated orchard artwork/text are CC0; third-party sample EPUBs used in validation remain under their publishers' licenses and are not redistributed here.
