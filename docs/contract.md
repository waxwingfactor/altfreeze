# Supported contract — v1

This contract is deliberately small. An editor remains responsible for the meaning, language and usefulness of descriptions and for the final publication's accessibility. Byte equality is evidence about recorded source inputs, not proof of unchanged meaning across an entire book.

## Inputs

A regular-file EPUB ZIP with exactly one `container.xml` package, package version `3.0`, title, unique publication identifier and one valid unrefined UTC `dcterms:modified`. The spine contains unique manifest-declared XHTML documents. Every manifest XHTML document is inspected, including non-spine navigation content. UTF-8 XML only; predefined XML escapes are supported, DTD/entity declarations are rejected.

The workflow reviews XHTML `img` occurrences in document body. The resource must be a manifest-declared local PNG/JPEG with valid signature and decodable pixels. The same raster used twice creates two independent occurrence decisions. Ordinary manifest comments are accepted and preserved; XML comments and processing instructions are excluded from displayed prose.

Unsupported inputs fail as a whole: EPUB 2; multiple renditions; fixed layout; DRM, encryption, signatures and rights XML; remote manifest/image resources; queried/fragmented image references; `xml:base`; scripts/event attributes; iframe/object/embed/canvas/picture/SVG/audio/video/template content; `srcset`, image maps and extended-description attributes. An image with explicit role, title, ARIA attributes, tabindex/accesskey/contenteditable, or a role/name override on an ancestor is outside the safe alt-only contract. Hidden, inert, editable, linked and native functional image contexts are rejected. CSS is retained and fingerprinted, never executed or interpreted by the review page. CSS background images and other mechanisms are outside the reviewed occurrence inventory.

The supplied HTML shows extracted text and raster pixels, without the book's layout, CSS, language-specific typography or reading-system behavior. Review chapter context and the original publication in your normal reading tools when needed. Complex descriptions, accessible mathematics, tables, SVG and long-description structure need separate authoring tools. Do not force a complex image into the short-alt workflow.

## Resource boundaries

| Boundary | Limit |
| --- | --- |
| Archive file | 64 MiB |
| Expanded member contents | 128 MiB total |
| Individual ZIP member | 8 MiB |
| XML document | 2 MiB |
| ZIP entries | 2,000; resource entries only, no explicit directory entries |
| Image occurrences | 200 |
| Decoded raster pixels | 25 million per unique image; 100 million total |
| Raster frames | One; animated/multiframe input rejected |
| Preview source bytes counted per occurrence | 24 MiB total |
| Context text counted per occurrence | 4 MiB total |
| JSON input | 16 MiB; browser decision import 8 MiB |
| Replacement/reviewer/note | 2,000 / 120 / 4,000 Unicode code points |

These limits bound local memory/work, not processing-time guarantees. Repeated previews/context count again toward packet limits. A limit failure writes no successful packet. Use trusted output parent directories and ordinary files on a local filesystem. Hostile concurrent filesystem replacement, crash durability and network filesystems are outside the atomic-write guarantee. Named pipes/devices are rejected before reading on platforms with nonblocking file open support.

## Review packet and decisions

`export` atomically publishes a new directory containing `snapshot.json`, `decisions.json`, `review.html`. Keep the exact source EPUB separately. The snapshot uses `altfreeze.snapshot.v1`; its SHA-256 binds canonical UTF-8 JSON fields. Occurrence IDs hash the document path, NUL and one-based image index. They identify a position inside a bound chapter, not a persistent cross-edition semantic identity.

Returned decision JSON has exactly these fields:

```json
{
  "format": "altfreeze.decisions.v1",
  "snapshot_sha256": "<the matching snapshot SHA-256>",
  "items": [
    {"id": "<occurrence ID>", "action": "replace", "alt": "A brief description.", "reviewer": "Editor", "note": "Reviewed with author."}
  ]
}
```

Exactly one decision per occurrence is required. Unknown/duplicate IDs, unknown fields, duplicate JSON object keys, wrong versions, nonfinite numbers, invalid XML characters and mixed snapshots are rejected by the CLI. Row order may differ. Browser validation is helpful guidance; the CLI is the final gate.

| Action | Meaning and requirements |
| --- | --- |
| `pending` | Review unfinished. Cannot apply. |
| `needs-work` | Explicit editorial question remains. Cannot apply. |
| `keep` | Approve existing nonblank alt. Reviewer required; `alt` must be empty in decision row. |
| `replace` | Approve nonblank replacement. Reviewer required. Whitespace/Unicode are preserved. |
| `decorative` | Write empty alt. Reviewer and rationale required. `alt` must be empty in decision row. |

The packet, decision records and receipts are editable files. Hashes detect mixed/stale/corrupt inputs through recomputation against the source. They are not signatures, tamper-proof ledgers or authenticated reviewer identities. Names are self-reported. Store source, decisions and receipts in your institution's trusted records system if authenticated provenance is required. Packets contain book content; use your normal rights/privacy controls.

## Exact-source application

`check` reconstructs the snapshot from the actual EPUB and compares canonical JSON bytes, including JSON types. `apply` first completes the same validation and requires every decision to be approved. It writes changes into a sibling staging directory and publishes it only on success. Existing output directories are refused. Source files are never overwritten; ordinary failure removes staging files. No success or partial EPUB is returned for an unsupported or unresolved input.

Only `alt` attributes and the package's modification timestamp change logically. Changed XML documents are serialized as UTF-8 XML, preserving comments/PIs but potentially normalizing prefixes, quotes and empty-element syntax. Untouched entry contents remain byte-identical; compressed archive bytes, ZIP metadata fidelity and digital signatures are not promised. Packaging keeps `mimetype` first, stored and without extra fields. Modification time updates when alt changes. All-Keep output preserves its package timestamp.

The output receipt binds canonical decisions, input/output archives and post-apply snapshot hashes. `review/` is a newly bound baseline: completed replacements become Keep, decorative decisions remain Decorative, and reviewer/note attribution persists. Reconcile this baseline against the next vendor return. The old pre-application source packet will intentionally reject the changed output.

## Conservative reconciliation

`reconcile OLD.epub PACKET NEW.epub --out NEXT` validates the exact old source and partial/complete decisions before examining the new publication. Different publication identifiers fail. Every new document/index occurrence is reported; removed old occurrences remain in `reconciliation.json` with their previous decisions.

A decision is retained only when all three boundaries match:

1. Identical complete XHTML bytes at the same document path and occurrence index.
2. Identical referenced image path and bytes.
3. Identical shared context: every archive entry except manifest XHTML, with a narrow package exception described below. Thus any raster, CSS, font, unlisted resource, container or substantive package change reopens every decision. This covers rasters used through CSS without interpreting the CSS cascade.

The only ignored package change is the validated, unrefined `dcterms:modified` text value. The rest of the parsed XML and declared namespace mappings remain bound. Package whitespace/structure changes can still reopen everything. ZIP timestamp/compression changes do not alone reopen decisions because comparisons use member content, though they change the exact-source hash for application.

Changed chapters reopen all their occurrences, even when the edit is only whitespace or alt text. New/invalidated decisions become Pending with empty replacement/reviewer/note. Prior decisions are preserved only in the reconciliation ledger. Retained unfinished decisions stay unfinished. Reports count records, not certified/approved images. New/removed statuses refer to document/index positions; insertion can shift several identities and is intentionally not guessed or merged.

Changes in another XHTML document can alter cross-references or interpretation without changing the reviewed chapter. Editors must reopen such decisions manually. This is a deliberate chapter boundary, not semantic dependency inference. There is no fuzzy matching, rename detection or automatic merge of edited descriptions.

## Recovery

On a stale-source error, locate the exact EPUB used for the packet and reconcile onto the revision. Do not hand-edit hashes. On an unsupported-markup error, remediate in a proper EPUB authoring tool or use another workflow; do not remove meaningful semantics merely to satisfy this tool. On an output-exists error, choose a new output directory. On a review/browser interruption, reload the last downloaded JSON; unsaved work has no recovery guarantee. Keep every released output alongside its receipt and next baseline.

EPUBCheck and Ace are external complementary checks. altfreeze's structural inspection is not a complete EPUB conformance validator, and successful processing does not establish WCAG/EPUB accessibility conformance.
