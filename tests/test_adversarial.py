"""Independent acceptance/security checks for the deliberately narrow EPUB contract.

Fixtures are produced here rather than using the application's own EPUB writer.
"""

import hashlib
import json
import os
import struct
import subprocess
import sys
import warnings
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from altfreeze.core import Error, apply, export_packet, inspect_epub, reconcile, validate


def _png(rgb):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00" + bytes(rgb)))
        + chunk(b"IEND", b"")
    )


PNG = _png((255, 255, 255))
PNG_CHANGED = _png((0, 0, 0))


def _chapter(body, *, head="", root_attributes=""):
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en" '
        + root_attributes
        + '><head><title>Chapter</title>'
        + head
        + '</head><body><h1>Chapter</h1>'
        + body
        + '</body></html>'
    ).encode("utf-8")


def _members(*, docs=None, images=None, version="3.0", metadata=""):
    if docs is None:
        docs = {
            "one.xhtml": _chapter(
                '<p>The first context discusses the river.</p>'
                '<figure><img src="../images/one.png" alt="A river."/>'
                '<figcaption>Figure 1. River at dusk.</figcaption></figure>'
                '<p>Following prose explains the location.</p>'
            ),
            "two.xhtml": _chapter(
                '<p>The second context discusses image reuse.</p>'
                '<img src="../images/one.png" alt="A reused photograph."/>'
            ),
        }
    if images is None:
        images = {"one.png": PNG}
    manifest = [
        '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    ]
    spine = []
    for i, name in enumerate(docs):
        manifest.append(
            f'<item id="ch{i}" href="text/{escape(name)}" media-type="application/xhtml+xml"/>'
        )
        spine.append(f'<itemref idref="ch{i}"/>')
    for i, name in enumerate(images):
        media = "image/jpeg" if name.endswith((".jpg", ".jpeg")) else "image/png"
        if name.endswith(".svg"):
            media = "image/svg+xml"
        manifest.append(
            f'<item id="im{i}" href="images/{escape(name)}" media-type="{media}"/>'
        )
    opf = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<package xmlns="http://www.idpf.org/2007/opf" version="{version}" unique-identifier="uid">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:identifier id="uid">urn:uuid:altfreeze-independent-fixture</dc:identifier>'
        '<dc:title>Independent acceptance fixture</dc:title><dc:language>en</dc:language>'
        '<meta property="dcterms:modified">2026-01-01T00:00:00Z</meta>'
        + metadata
        + '</metadata><manifest>'
        + "".join(manifest)
        + '</manifest><spine>'
        + "".join(spine)
        + '</spine></package>'
    ).encode()
    nav = _chapter(
        '<nav epub:type="toc" id="toc"><h2>Contents</h2><ol>'
        + "".join(
            f'<li><a href="text/{escape(name)}">Chapter {i + 1}</a></li>'
            for i, name in enumerate(docs)
        )
        + '</ol></nav>'
    )
    result = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": (
            '<?xml version="1.0"?>'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">'
            '<rootfiles><rootfile full-path="EPUB/package.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>'
        ).encode(),
        "EPUB/package.opf": opf,
        "EPUB/nav.xhtml": nav,
    }
    result.update({f"EPUB/text/{k}": v for k, v in docs.items()})
    result.update({f"EPUB/images/{k}": v for k, v in images.items()})
    return result


def _write_epub(path, members=None, *, extra=(), compression=zipfile.ZIP_DEFLATED):
    members = _members() if members is None else members
    with zipfile.ZipFile(path, "w") as archive:
        for name, value in members.items():
            archive.writestr(
                name,
                value,
                compress_type=zipfile.ZIP_STORED if name == "mimetype" else compression,
            )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            for name, value in extra:
                archive.writestr(name, value, compress_type=compression)
    return Path(path)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _approve(packet, *, action="keep", alt=""):
    path = Path(packet) / "decisions.json"
    decisions = _read_json(path)
    for item in decisions["items"]:
        item.update(action=action, alt=alt, reviewer="Independent editor", note="Reviewed in context.")
    _write_json(path, decisions)
    return decisions


@pytest.fixture
def publication(tmp_path):
    return _write_epub(tmp_path / "source.epub")


@pytest.fixture
def packet(publication, tmp_path):
    path = tmp_path / "packet"
    export_packet(publication, path)
    return path


def test_repeated_raster_occurrences_have_distinct_decisions(publication):
    first = inspect_epub(publication).snapshot
    second = inspect_epub(publication).snapshot
    assert first == second
    items = first["items"]
    assert len(items) == 2
    assert items[0]["image_sha256"] == items[1]["image_sha256"]
    assert items[0]["id"] != items[1]["id"]
    assert items[0]["current_alt"] != items[1]["current_alt"]
    assert all(item["chapter_text"] for item in items)


def test_review_context_excludes_xml_comments_and_processing_instructions(tmp_path):
    body = (
        '<p>Visible context before.</p><!-- EDITORIAL_COMMENT_MUST_NOT_BECOME_PROSE -->'
        '<?production INTERNAL_PROCESSING_INSTRUCTION?>'
        '<figure><img src="../images/one.png" alt="A river."/>'
        '<figcaption>Visible caption.<!-- PRIVATE_CAPTION_COMMENT --></figcaption></figure>'
    )
    epub = _write_epub(tmp_path / "commented.epub", _members(docs={"one.xhtml": _chapter(body)}))
    item = inspect_epub(epub).snapshot["items"][0]
    for field in ("chapter_text", "caption", "near_text"):
        assert "EDITORIAL_COMMENT" not in item[field]
        assert "INTERNAL_PROCESSING_INSTRUCTION" not in item[field]
        assert "PRIVATE_CAPTION_COMMENT" not in item[field]
    assert "Visible context before." in item["chapter_text"]
    assert "Visible caption." in item["caption"]


def test_export_provides_complete_offline_packet(packet):
    assert {"snapshot.json", "decisions.json", "review.html"} <= {
        child.name for child in packet.iterdir()
    }
    decisions = _read_json(packet / "decisions.json")
    assert decisions["format"] == "altfreeze.decisions.v1"
    assert all(item["action"] == "pending" for item in decisions["items"])
    assert decisions["snapshot_sha256"]


def test_pending_decisions_can_be_checked_but_cannot_be_applied(publication, packet, tmp_path):
    validate(publication, packet, complete=False)
    original = publication.read_bytes()
    destination = tmp_path / "unresolved"
    with pytest.raises(Error):
        apply(publication, packet, destination)
    assert not destination.exists()
    assert publication.read_bytes() == original


def test_independent_replace_round_trip_and_postapply_lineage(publication, packet, tmp_path):
    before = inspect_epub(publication)
    _approve(packet, action="replace", alt='River & bridge, "north" bank. <水> مرحبا')
    original_bytes = publication.read_bytes()
    out = tmp_path / "applied"
    apply(publication, packet, out)
    result = out / "publication.epub"
    assert result.is_file()
    assert (out / "receipt.json").is_file()
    after = inspect_epub(result)
    assert all(
        item["current_alt"] == 'River & bridge, "north" bank. <水> مرحبا'
        for item in after.snapshot["items"]
    )
    for name, value in before.entries.items():
        if name not in {"EPUB/text/one.xhtml", "EPUB/text/two.xhtml", "EPUB/package.opf"}:
            assert after.entries[name] == value
    validate(result, out / "review")
    assert publication.read_bytes() == original_bytes
    with zipfile.ZipFile(result) as archive:
        first = archive.infolist()[0]
        assert first.filename == "mimetype"
        assert first.compress_type == zipfile.ZIP_STORED
        assert first.extra == b""
        assert archive.read("mimetype") == b"application/epub+zip"


def test_decorative_is_explicit_and_survives_round_trip(publication, packet, tmp_path):
    _approve(packet, action="decorative")
    out = tmp_path / "decorative"
    apply(publication, packet, out)
    items = inspect_epub(out / "publication.epub").snapshot["items"]
    assert all(item["current_alt"] == "" for item in items)


def test_inspection_hash_and_entries_come_from_one_source_read(publication, tmp_path, monkeypatch):
    original_bytes = publication.read_bytes()
    revised_members = _members()
    revised_members["EPUB/text/one.xhtml"] = revised_members["EPUB/text/one.xhtml"].replace(
        b'A river.', b'A new vendor alt.'
    )
    other = _write_epub(tmp_path / "race-revision.epub", revised_members)
    revised_bytes = other.read_bytes()
    real_open = Path.open
    real_fdopen = os.fdopen
    original_stat = publication.stat()
    read_requests = []
    replaced = False

    class ChangingSource:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, *args):
            nonlocal replaced
            read_requests.append(args)
            data = self.stream.read(*args)
            if not replaced:
                replaced = True
                with real_open(publication, "wb") as writer:
                    writer.write(revised_bytes)
            return data

    def source_changes_after_read(descriptor, *args, **kwargs):
        stream = real_fdopen(descriptor, *args, **kwargs)
        stream_stat = os.fstat(stream.fileno())
        if (stream_stat.st_dev, stream_stat.st_ino) == (original_stat.st_dev, original_stat.st_ino) and not replaced:
            return ChangingSource(stream)
        return stream

    monkeypatch.setattr(os, "fdopen", source_changes_after_read)
    inspected = inspect_epub(publication)
    assert replaced
    assert read_requests == [(64 * 1024 * 1024 + 1,)]
    assert inspected.snapshot["source_sha256"] == hashlib.sha256(original_bytes).hexdigest()
    assert inspected.snapshot["items"][0]["current_alt"] == "A river."


@pytest.mark.parametrize("action", ["pending", "needs-work", "invented"])
def test_unresolved_or_unknown_action_cannot_produce_epub(publication, packet, tmp_path, action):
    _approve(packet, action=action)
    out = tmp_path / "blocked"
    with pytest.raises(Error):
        apply(publication, packet, out)
    assert not out.exists()


@pytest.mark.parametrize("alt", ["", " \t\n", "a\x00b", "a\x01b"])
def test_invalid_replacement_is_rejected_before_output(publication, packet, tmp_path, alt):
    _approve(packet, action="replace", alt=alt)
    out = tmp_path / "invalid-text"
    with pytest.raises(Error):
        apply(publication, packet, out)
    assert not out.exists()


@pytest.mark.parametrize("field,value", [("reviewer", ""), ("reviewer", "a" * 121), ("note", "a" * 4001)])
def test_approved_decision_metadata_limits(publication, packet, field, value):
    decisions = _approve(packet)
    decisions["items"][0][field] = value
    _write_json(packet / "decisions.json", decisions)
    with pytest.raises(Error):
        validate(publication, packet)


def test_decorative_decision_requires_reason(publication, packet):
    decisions = _approve(packet, action="decorative")
    decisions["items"][0]["note"] = ""
    _write_json(packet / "decisions.json", decisions)
    with pytest.raises(Error):
        validate(publication, packet)


@pytest.mark.parametrize("alt_attribute", ["", ' alt=""', ' alt="   "'])
def test_missing_or_blank_alt_cannot_be_implicitly_kept(tmp_path, alt_attribute):
    epub = _write_epub(
        tmp_path / "blank.epub",
        _members(docs={"one.xhtml": _chapter(f'<img src="../images/one.png"{alt_attribute}/>')}),
    )
    packet = tmp_path / "blank-review"
    export_packet(epub, packet)
    _approve(packet)
    with pytest.raises(Error):
        validate(epub, packet)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "foreign", "bad-digest", "bad-format"])
def test_decision_identity_schema_errors_fail_closed(publication, packet, mutation):
    decisions = _approve(packet)
    if mutation == "duplicate":
        decisions["items"].append(dict(decisions["items"][0]))
    elif mutation == "missing":
        decisions["items"].pop()
    elif mutation == "foreign":
        decisions["items"][0]["id"] = "not-an-occurrence-id"
    elif mutation == "bad-digest":
        decisions["snapshot_sha256"] = "0" * 64
    else:
        decisions["format"] = "altfreeze.decisions.v999"
    _write_json(packet / "decisions.json", decisions)
    with pytest.raises(Error):
        validate(publication, packet)


def test_snapshot_tampering_fails_closed(publication, packet):
    _approve(packet)
    snapshot = _read_json(packet / "snapshot.json")
    snapshot["items"][0]["current_alt"] = "Altered after export"
    _write_json(packet / "snapshot.json", snapshot)
    with pytest.raises(Error):
        validate(publication, packet)


@pytest.mark.parametrize("replacement", [True, 1.0])
def test_snapshot_binding_distinguishes_json_numeric_types(publication, packet, replacement):
    _approve(packet, action="replace", alt="A reviewed replacement.")
    snapshot = _read_json(packet / "snapshot.json")
    snapshot["items"][0]["index"] = replacement
    _write_json(packet / "snapshot.json", snapshot)
    with pytest.raises(Error):
        validate(publication, packet)


@pytest.mark.parametrize("location", ["root", "item"])
def test_unknown_decision_fields_are_rejected(publication, packet, location):
    decisions = _approve(packet)
    target = decisions if location == "root" else decisions["items"][0]
    target["unrecognized_field"] = "must not silently ignore"
    _write_json(packet / "decisions.json", decisions)
    with pytest.raises(Error):
        validate(publication, packet)


def test_duplicate_json_keys_are_rejected_even_if_values_match(publication, packet):
    decisions = _approve(packet)
    encoded = json.dumps(decisions)
    key = '"format": "altfreeze.decisions.v1"'
    assert key in encoded
    (packet / "decisions.json").write_text(encoded.replace(key, key + ", " + key, 1))
    with pytest.raises(Error):
        validate(publication, packet)


def test_truncated_decision_json_uses_the_public_error_contract(publication, packet):
    (packet / "decisions.json").write_text('{"format":')
    with pytest.raises(Error):
        validate(publication, packet)


def test_other_publication_cannot_use_old_packet(publication, packet, tmp_path):
    _approve(packet)
    members = _members()
    members["EPUB/text/one.xhtml"] = members["EPUB/text/one.xhtml"].replace(b"river", b"stream")
    revised = _write_epub(tmp_path / "different.epub", members)
    with pytest.raises(Error):
        validate(revised, packet)


def test_existing_output_is_never_overwritten(publication, packet, tmp_path):
    _approve(packet)
    out = tmp_path / "already-there"
    out.mkdir()
    sentinel = out / "important.txt"
    sentinel.write_text("Do not replace")
    with pytest.raises(Error):
        apply(publication, packet, out)
    assert sentinel.read_text() == "Do not replace"
    assert list(out.iterdir()) == [sentinel]


def test_failure_after_epub_write_removes_all_staged_outputs(publication, packet, tmp_path, monkeypatch):
    from altfreeze import review

    _approve(packet, action="replace", alt="A newly reviewed description.")
    original_bytes = publication.read_bytes()

    def rendering_fails(*_args, **_kwargs):
        raise Error("Injected renderer failure after the staged EPUB was written")

    monkeypatch.setattr(review, "render_review", rendering_fails)
    out = tmp_path / "failed-transaction"
    with pytest.raises(Error):
        apply(publication, packet, out)
    assert not out.exists()
    assert not list(tmp_path.glob(".altfreeze-*"))
    assert publication.read_bytes() == original_bytes


def test_reconcile_carries_unchanged_chapter_only(publication, packet, tmp_path):
    _approve(packet)
    members = _members()
    members["EPUB/text/two.xhtml"] = members["EPUB/text/two.xhtml"].replace(b"second", b"revised")
    revised = _write_epub(tmp_path / "revised.epub", members)
    out = tmp_path / "reconciled"
    reconcile(publication, packet, revised, out)
    snapshot = _read_json(out / "snapshot.json")
    decisions = _read_json(out / "decisions.json")
    by_id = {item["id"]: item for item in decisions["items"]}
    for item in snapshot["items"]:
        action = by_id[item["id"]]["action"]
        assert action == ("keep" if item["document"].endswith("one.xhtml") else "pending")
    report = _read_json(out / "reconciliation.json")
    assert report["format"] == "altfreeze.reconciliation.v1"
    assert report["summary"] == {"retained": 1, "invalidated": 1, "removed": 0, "new": 0}
    assert {item["status"] for item in report["items"]} == {"retained", "invalidated"}


@pytest.mark.parametrize("chapter_changed", [False, True])
def test_vendor_revision_timestamp_does_not_invalidate_untouched_chapters(publication, packet, tmp_path, chapter_changed):
    _approve(packet)
    members = _members()
    members["EPUB/package.opf"] = members["EPUB/package.opf"].replace(
        b"2026-01-01T00:00:00Z", b"2026-10-15T18:00:00Z"
    )
    if chapter_changed:
        members["EPUB/text/two.xhtml"] = members["EPUB/text/two.xhtml"].replace(
            b"second context", b"corrected context"
        )
    revised = _write_epub(tmp_path / "dated-vendor-revision.epub", members)
    out = tmp_path / "dated-revision-review"
    report = reconcile(publication, packet, revised, out)
    assert report["summary"] == {
        "retained": 1 if chapter_changed else 2,
        "invalidated": 1 if chapter_changed else 0,
        "removed": 0,
        "new": 0,
    }
    snapshot = _read_json(out / "snapshot.json")
    decisions = {item["id"]: item for item in _read_json(out / "decisions.json")["items"]}
    for item in snapshot["items"]:
        expected = "pending" if chapter_changed and item["document"].endswith("two.xhtml") else "keep"
        assert decisions[item["id"]]["action"] == expected


def test_changed_pixels_invalidate_all_uses_of_that_raster(publication, packet, tmp_path):
    _approve(packet)
    members = _members(images={"one.png": PNG_CHANGED})
    revised = _write_epub(tmp_path / "pixels.epub", members)
    out = tmp_path / "pixels-review"
    reconcile(publication, packet, revised, out)
    decisions = _read_json(out / "decisions.json")
    assert all(item["action"] == "pending" for item in decisions["items"])
    report = _read_json(out / "reconciliation.json")
    assert report["summary"] == {"retained": 0, "invalidated": 2, "removed": 0, "new": 0}


def test_reconcile_reports_removed_and_new_occurrences(publication, packet, tmp_path):
    _approve(packet)
    revised = _write_epub(
        tmp_path / "replacement.epub",
        _members(docs={"new.xhtml": _chapter('<p>New chapter.</p><img src="../images/one.png" alt="New alt."/>')}),
    )
    out = tmp_path / "replacement-review"
    reconcile(publication, packet, revised, out)
    decisions = _read_json(out / "decisions.json")
    assert len(decisions["items"]) == 1
    assert decisions["items"][0]["action"] == "pending"
    report = _read_json(out / "reconciliation.json")
    assert report["summary"] == {"retained": 0, "invalidated": 0, "removed": 2, "new": 1}
    assert {item["status"] for item in report["items"]} == {"removed", "new"}


def test_vendor_returns_approved_output_without_losing_lineage(publication, packet, tmp_path):
    _approve(packet, action="replace", alt="Approved wording.")
    applied = tmp_path / "applied-lineage"
    apply(publication, packet, applied)
    vendor_return = tmp_path / "vendor-return.epub"
    vendor_return.write_bytes((applied / "publication.epub").read_bytes())
    out = tmp_path / "vendor-return-review"
    report = reconcile(applied / "publication.epub", applied / "review", vendor_return, out)
    assert report["summary"] == {"retained": 2, "invalidated": 0, "removed": 0, "new": 0}
    validate(vendor_return, out)


def test_stylesheet_changes_invalidate_all_chapter_approvals(tmp_path):
    members = _members()
    members["EPUB/package.opf"] = members["EPUB/package.opf"].replace(
        b"</manifest>",
        b'<item id="css" href="styles.css" media-type="text/css"/></manifest>',
    )
    for name in ("EPUB/text/one.xhtml", "EPUB/text/two.xhtml"):
        members[name] = members[name].replace(
            b"</head>", b'<link rel="stylesheet" href="../styles.css"/></head>'
        )
    members["EPUB/styles.css"] = b"p { display: block; }"
    source = _write_epub(tmp_path / "styled.epub", members)
    packet = tmp_path / "styled-review"
    export_packet(source, packet)
    _approve(packet)
    members["EPUB/styles.css"] = b"p { display: none; }"
    revised = _write_epub(tmp_path / "restyled.epub", members)
    out = tmp_path / "restyled-review"
    report = reconcile(source, packet, revised, out)
    assert report["summary"] == {"retained": 0, "invalidated": 2, "removed": 0, "new": 0}
    assert all(item["action"] == "pending" for item in _read_json(out / "decisions.json")["items"])


@pytest.mark.parametrize(
    "body",
    [
        '<img src="../images/one.png" alt="x" aria-label="override"/>',
        '<img src="../images/one.png" alt="x" aria-labelledby="caption"/><p id="caption">Name</p>',
        '<img src="../images/one.png" alt="x" aria-hidden="true"/>',
        '<img src="../images/one.png" alt="x" hidden="hidden"/>',
        '<img src="../images/one.png" alt="x" role="presentation"/>',
        '<img src="../images/one.png" alt="x" role="none"/>',
        '<div aria-hidden="true"><img src="../images/one.png" alt="x"/></div>',
        '<div hidden="hidden"><img src="../images/one.png" alt="x"/></div>',
        '<a href="https://example.org"><img src="../images/one.png" alt="x"/></a>',
        '<picture><img src="../images/one.png" alt="x"/></picture>',
        '<img src="../images/one.png" srcset="../images/one.png 2x" alt="x"/>',
        '<object data="../images/one.png"/>',
        '<canvas/>',
        '<script>throw new Error("do not execute");</script>',
        '<audio/>',
        '<video/>',
        '<img src="https://example.org/private.png" alt="x"/>',
        '<img src="//example.org/private.png" alt="x"/>',
        '<img src="data:image/png;base64,AAAA" alt="x"/>',
        '<div xml:base="https://example.org/"><img src="../images/one.png" alt="x"/></div>',
    ],
)
def test_unsupported_or_ambiguous_content_is_rejected(tmp_path, body):
    epub = _write_epub(tmp_path / "unsupported.epub", _members(docs={"one.xhtml": _chapter(body)}))
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("special", ["epub2", "fixed", "encrypted", "signed", "svg"])
def test_unsupported_publication_profiles_are_rejected(tmp_path, special):
    if special == "epub2":
        members = _members(version="2.0")
    elif special == "fixed":
        members = _members(metadata='<meta property="rendition:layout">pre-paginated</meta>')
    elif special == "svg":
        members = _members(
            docs={"one.xhtml": _chapter('<img src="../images/vector.svg" alt="vector"/>')},
            images={"vector.svg": b'<svg xmlns="http://www.w3.org/2000/svg"/>'},
        )
    else:
        members = _members()
        members[f"META-INF/{'encryption' if special == 'encrypted' else 'signatures'}.xml"] = b"<unsupported/>"
    epub = _write_epub(tmp_path / "profile.epub", members)
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("name,data", [("broken.png", b"\x89PNG\r\n\x1a\n"), ("broken.jpg", b"\xff\xd8\xff")])
def test_image_signature_alone_does_not_make_a_reviewable_raster(tmp_path, name, data):
    epub = _write_epub(
        tmp_path / "broken-image.epub",
        _members(
            docs={"one.xhtml": _chapter(f'<img src="../images/{name}" alt="Unavailable pixels."/>')},
            images={name: data},
        ),
    )
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("name", ["../escape", "/absolute", "EPUB/../../escape", "EPUB\\text\\one.xhtml"])
def test_unsafe_archive_paths_are_rejected_without_extraction(tmp_path, name):
    epub = _write_epub(tmp_path / "paths.epub", extra=[(name, b"untrusted")])
    with pytest.raises(Error):
        inspect_epub(epub)
    assert not (tmp_path / "escape").exists()


def test_duplicate_zip_members_are_rejected(tmp_path):
    epub = _write_epub(tmp_path / "duplicate.epub", extra=[("EPUB/text/one.xhtml", b"different")])
    with pytest.raises(Error):
        inspect_epub(epub)


def test_non_epub_zip_compression_is_rejected(tmp_path):
    epub = _write_epub(tmp_path / "compression.epub", compression=zipfile.ZIP_BZIP2)
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("member", ["mimetype", "EPUB/text/one.xhtml", "EPUB/images/one.png"])
@pytest.mark.parametrize("field", ["compression", "encryption"])
def test_local_header_cannot_disagree_with_central_directory(tmp_path, member, field):
    epub = _write_epub(tmp_path / "conflicting-headers.epub")
    with zipfile.ZipFile(epub) as archive:
        info = archive.getinfo(member)
    data = bytearray(epub.read_bytes())
    start = info.header_offset
    assert data[start : start + 4] == b"PK\x03\x04"
    if field == "compression":
        value = zipfile.ZIP_DEFLATED if info.compress_type == zipfile.ZIP_STORED else zipfile.ZIP_STORED
        struct.pack_into("<H", data, start + 8, value)
    else:
        struct.pack_into("<H", data, start + 6, info.flag_bits | 1)
    epub.write_bytes(data)
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("namespace", ["", "urn:unsupported-foreign-namespace"])
def test_foreign_namespace_img_cannot_be_silently_omitted(tmp_path, namespace):
    body = f'<img xmlns="{namespace}" src="../images/one.png" alt="Unreviewed image."/>'
    epub = _write_epub(tmp_path / "foreign-image.epub", _members(docs={"one.xhtml": _chapter(body)}))
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("reference", ["https://[", "//["])
def test_malformed_resource_url_uses_public_error_contract(tmp_path, reference):
    body = f'<img src="{reference}" alt="Unsupported resource."/>'
    epub = _write_epub(tmp_path / "malformed-reference.epub", _members(docs={"one.xhtml": _chapter(body)}))
    with pytest.raises(Error):
        inspect_epub(epub)


@pytest.mark.parametrize("role", ["img", "button", "link"])
def test_semantic_container_does_not_bypass_image_review_scope(tmp_path, role):
    body = f'<div role="{role}"><img src="../images/one.png" alt="Context-dependent name."/></div>'
    epub = _write_epub(tmp_path / "semantic-wrapper.epub", _members(docs={"one.xhtml": _chapter(body)}))
    with pytest.raises(Error):
        inspect_epub(epub)


def test_external_entities_are_rejected_without_reading_host_files(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("SHOULD-NEVER-APPEAR")
    xml = (
        '<?xml version="1.0"?><!DOCTYPE html [<!ENTITY leak SYSTEM "'
        + secret.as_uri()
        + '">]><html xmlns="http://www.w3.org/1999/xhtml"><head><title>x</title></head>'
        '<body><p>&leak;</p><img src="../images/one.png" alt="x"/></body></html>'
    ).encode()
    epub = _write_epub(tmp_path / "entities.epub", _members(docs={"one.xhtml": xml}))
    with pytest.raises(Error):
        inspect_epub(epub)


def test_archive_member_limit_rejects_compressed_bomb(tmp_path):
    epub = _write_epub(tmp_path / "oversized.epub", extra=[("EPUB/huge.bin", b"x" * (8 * 1024 * 1024 + 1))])
    with pytest.raises(Error):
        inspect_epub(epub)


def test_xml_size_limit_is_independent_of_zip_member_limit(tmp_path):
    xml = _chapter('<p>' + "x" * (2 * 1024 * 1024) + '</p>')
    epub = _write_epub(tmp_path / "huge-xml.epub", _members(docs={"one.xhtml": xml}))
    with pytest.raises(Error):
        inspect_epub(epub)


def test_archive_entry_count_limit(tmp_path):
    extra = [(f"EPUB/unused/{i}.bin", b"x") for i in range(2001)]
    epub = _write_epub(tmp_path / "many-members.epub", extra=extra)
    with pytest.raises(Error):
        inspect_epub(epub)


def test_image_occurrence_limit(tmp_path):
    body = '<img src="../images/one.png" alt="x"/>' * 201
    epub = _write_epub(tmp_path / "many-images.epub", _members(docs={"one.xhtml": _chapter(body)}))
    with pytest.raises(Error):
        inspect_epub(epub)


def test_edited_review_content_is_escaped_not_executed(tmp_path):
    body = (
        '<p>&lt;script&gt;window.INJECTED=1&lt;/script&gt; &amp; surrounding context.</p>'
        '<img src="../images/one.png" alt="&quot;&gt;&lt;script&gt;window.INJECTED=2&lt;/script&gt;"/>'
    )
    epub = _write_epub(tmp_path / "hostile-text.epub", _members(docs={"one.xhtml": _chapter(body)}))
    packet = tmp_path / "hostile-review"
    export_packet(epub, packet)
    html = (packet / "review.html").read_text()
    assert "<script>window.INJECTED=1</script>" not in html
    assert "<script>window.INJECTED=2</script>" not in html


@pytest.mark.skipif(not hasattr(os, "mkfifo") or not hasattr(os, "O_NONBLOCK"), reason="POSIX named-pipe boundary")
@pytest.mark.parametrize("operation", ["epub", "decisions"])
def test_named_pipes_fail_without_waiting_for_a_writer(publication, packet, tmp_path, operation):
    pipe = tmp_path / "untrusted-pipe"
    os.mkfifo(pipe)
    if operation == "epub":
        arguments = ["export", str(pipe), "--out", str(tmp_path / "fifo-output")]
    else:
        arguments = ["check", str(publication), str(packet), "--decisions", str(pipe), "--allow-incomplete"]
    result = subprocess.run(
        [sys.executable, "-m", "altfreeze", *arguments],
        capture_output=True,
        text=True,
        timeout=3,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    report = json.loads(result.stderr)
    assert report["ok"] is False
    assert "regular file" in report["error"]
