"""Bounded EPUB inspection and conservative editorial decision transactions.

No input archive is extracted, no book code is executed, and no network is used.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import stat
import struct
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
from PIL import Image, UnidentifiedImageError

XHTML = "http://www.w3.org/1999/xhtml"
OPF = "http://www.idpf.org/2007/opf"
DC = "http://purl.org/dc/elements/1.1/"
CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
XML = "http://www.w3.org/XML/1998/namespace"
for prefix, uri in (("", XHTML), ("opf", OPF), ("dc", DC)):
    ET.register_namespace(prefix, uri)

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_MEMBER = 8 * 1024 * 1024
MAX_XML = 2 * 1024 * 1024
MAX_JSON = 16 * 1024 * 1024
MAX_ITEMS = 200


class Error(ValueError):
    """An unsupported, stale, or malformed input; no successful result exists."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Error(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _bounded_regular(path, limit, label):
    # O_NONBLOCK lets fstat reject a named pipe before a read/open can hang.
    descriptor = os.open(Path(path), os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise Error(f"{label} input must be a regular file")
        return source.read(limit + 1)


def read_json(path) -> dict:
    p = Path(path)
    raw = _bounded_regular(p, MAX_JSON, "JSON")
    if len(raw) > MAX_JSON:
        raise Error(f"JSON exceeds 16 MiB: {p.name}")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(Error("Nonfinite JSON number")))
    except Error:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise Error(f"Invalid UTF-8 JSON in {p.name}: {exc}") from exc
    if not isinstance(result, dict):
        raise Error(f"Expected JSON object: {p.name}")
    return result


def _xml(data: bytes, name: str) -> ET.ElementTree:
    if len(data) > MAX_XML:
        raise Error(f"XML exceeds 2 MiB: {name}")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise Error(f"Only UTF-8 XML is supported: {name}") from exc
    if re.search(r"<!\s*(DOCTYPE|ENTITY)", text, re.I):
        raise Error(f"DTD/entity declarations are unsupported: {name}")
    declaration = re.match(r"\s*<\?xml\s[^?]*encoding\s*=\s*['\"]([^'\"]+)", text, re.I)
    if declaration and declaration[1].lower().replace("-", "") != "utf8":
        raise Error(f"Only UTF-8 XML is supported: {name}")
    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
        return ET.ElementTree(ET.fromstring(text, parser=parser))
    except ET.ParseError as exc:
        raise Error(f"Malformed XML in {name}: {exc}") from exc


def _resolve(base: str, href: str) -> str:
    if not isinstance(href, str) or not href or "\\" in href or re.search(r"%(?![a-fA-F0-9]{2})", href):
        raise Error(f"Invalid local resource reference: {href!r}")
    try:
        parts = urlsplit(href)
    except ValueError as exc:
        raise Error(f"Malformed resource reference: {href!r}") from exc
    if parts.scheme or parts.netloc or parts.query or parts.fragment or parts.path.startswith("/"):
        raise Error(f"Only local resources without query/fragment are supported: {href!r}")
    try:
        decoded = unquote(parts.path, encoding="utf-8", errors="strict")
    except UnicodeError as exc:
        raise Error("Resource path is not UTF-8") from exc
    if "\\" in decoded or "\x00" in decoded or decoded.startswith("/"):
        raise Error(f"Unsafe resource reference: {href!r}")
    name = posixpath.normpath(posixpath.join(posixpath.dirname(base), decoded))
    if name in (".", "..") or name.startswith("../"):
        raise Error(f"Resource escapes EPUB root: {href!r}")
    return name


def _text(node) -> str:
    def visible_text(element):
        if not isinstance(element.tag, str):
            return
        if element.text:
            yield element.text
        for child in element:
            yield from visible_text(child)
            if child.tail:
                yield child.tail
    return " ".join(" ".join(visible_text(node)).split()) if node is not None else ""


def _xml_bytes(tree) -> bytes:
    return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)


@dataclass
class Book:
    snapshot: dict
    entries: dict[str, bytes]
    trees: dict[str, ET.ElementTree]
    opf_path: str
    infos: list[zipfile.ZipInfo]


def inspect_epub(path) -> Book:
    """Read a supported EPUB and reconstruct a deterministic source snapshot."""
    p = Path(path)
    raw = _bounded_regular(p, MAX_ARCHIVE, "EPUB")
    if len(raw) > MAX_ARCHIVE:
        raise Error("EPUB exceeds 64 MiB archive limit")
    entries = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > 2000:
                raise Error("EPUB must have 1–2000 ZIP entries")
            first = infos[0]
            if (first.filename != "mimetype" or first.compress_type != zipfile.ZIP_STORED
                    or first.extra or first.header_offset != 0):
                raise Error("EPUB mimetype must be first, uncompressed, without extra fields")
            if len(raw) < 38 or raw[:4] != b"PK\x03\x04":
                raise Error("Missing first ZIP local header")
            local_flags, local_method = struct.unpack_from("<HH", raw, 6)
            local_name_size, local_extra_size = struct.unpack_from("<HH", raw, 26)
            if (local_flags != first.flag_bits or local_method != zipfile.ZIP_STORED
                    or local_name_size != 8 or local_extra_size != 0 or raw[30:38] != b"mimetype"):
                raise Error("mimetype local ZIP header disagrees with EPUB container requirements")
            total = 0
            for info in infos:
                name = info.filename
                offset = info.header_offset
                if offset < 0 or offset + 30 > len(raw) or raw[offset:offset + 4] != b"PK\x03\x04":
                    raise Error(f"Invalid ZIP local header: {name}")
                flags, method = struct.unpack_from("<HH", raw, offset + 6)
                name_size, extra_size = struct.unpack_from("<HH", raw, offset + 26)
                if (flags != info.flag_bits or method != info.compress_type
                        or offset + 30 + name_size + extra_size + info.compress_size > len(raw)):
                    raise Error(f"ZIP local/central headers disagree: {name}")
                if info.is_dir():
                    raise Error("Explicit ZIP directory entries are unsupported; use resource entries only")
                if (name in entries or not name or name.startswith("/") or "\\" in name
                        or any(x in ("", ".", "..") for x in name.split("/"))
                        or any(ord(c) < 32 for c in name) or ":" in name):
                    raise Error(f"Duplicate or unsafe ZIP member: {name!r}")
                if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                    raise Error(f"Symlink/encrypted ZIP member unsupported: {name}")
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise Error(f"Unsupported ZIP compression: {name}")
                if info.file_size > MAX_MEMBER:
                    raise Error(f"ZIP member exceeds 8 MiB: {name}")
                total += info.file_size
                if total > MAX_EXPANDED:
                    raise Error("EPUB exceeds 128 MiB expanded limit")
                entries[name] = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise Error(f"Invalid EPUB ZIP: {exc}") from exc
    if entries.get("mimetype") != b"application/epub+zip":
        raise Error("Invalid EPUB mimetype content")
    if any(name in entries for name in ("META-INF/encryption.xml", "META-INF/signatures.xml", "META-INF/rights.xml")):
        raise Error("Encrypted, signed, or rights-managed EPUBs are unsupported")
    if "META-INF/container.xml" not in entries:
        raise Error("Missing META-INF/container.xml")
    container = _xml(entries["META-INF/container.xml"], "container.xml")
    roots = container.findall(f".//{{{CONTAINER}}}rootfile")
    if len(roots) != 1 or roots[0].get("media-type") != "application/oebps-package+xml":
        raise Error("Exactly one EPUB package rendition is supported")
    opf_path = _resolve("", roots[0].get("full-path", ""))
    if opf_path not in entries:
        raise Error("Missing EPUB package document")
    package = _xml(entries[opf_path], opf_path)
    root = package.getroot()
    if root.tag != f"{{{OPF}}}package" or root.get("version") != "3.0":
        raise Error("Only EPUB 3 packages (version=3.0) are supported")
    if any(node.get(f"{{{XML}}}base") is not None for node in root.iter()):
        raise Error("xml:base is unsupported")
    metadata = root.find(f"{{{OPF}}}metadata")
    titles = metadata.findall(f"{{{DC}}}title") if metadata is not None else []
    ids = metadata.findall(f"{{{DC}}}identifier") if metadata is not None else []
    uid = root.get("unique-identifier")
    matching_ids = [n for n in ids if n.get("id") == uid]
    modified = [] if metadata is None else [n for n in metadata.findall(f"{{{OPF}}}meta") if n.get("property") == "dcterms:modified"]
    if not titles or not _text(titles[0]) or len(matching_ids) != 1 or not _text(matching_ids[0]):
        raise Error("Package needs title and a unique publication identifier")
    if len(modified) != 1 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", _text(modified[0])):
        raise Error("Package needs one UTC dcterms:modified timestamp")
    if modified[0].get("refines") is not None:
        raise Error("Publication dcterms:modified must be unrefined")
    try:
        datetime.strptime(_text(modified[0]), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise Error("Invalid dcterms:modified date") from exc
    if any(n.get("property") == "rendition:layout" and _text(n) != "reflowable" for n in metadata.findall(f"{{{OPF}}}meta")):
        raise Error("Fixed-layout EPUBs are unsupported")
    manifest = root.find(f"{{{OPF}}}manifest")
    spine = root.find(f"{{{OPF}}}spine")
    if manifest is None or spine is None or not list(spine):
        raise Error("Missing EPUB manifest or spine")
    resources = {}
    media = {}
    for node in manifest:
        if not isinstance(node.tag, str):
            continue
        if node.tag != f"{{{OPF}}}item":
            raise Error("Unsupported manifest element")
        rid = node.get("id")
        name = _resolve(opf_path, node.get("href", ""))
        if not rid or rid in resources or name in media or name not in entries:
            raise Error(f"Duplicate/missing manifest resource: {name}")
        if set(node.get("properties", "").split()) & {"scripted", "remote-resources"}:
            raise Error(f"Scripted/remote content unsupported: {name}")
        resources[rid] = name
        media[name] = node.get("media-type", "")
    spine_paths = []
    for node in spine:
        if not isinstance(node.tag, str):
            continue
        if node.tag != f"{{{OPF}}}itemref" or node.get("idref") not in resources:
            raise Error("Spine has unknown item reference")
        if "rendition:layout-pre-paginated" in node.get("properties", "").split():
            raise Error("Fixed-layout spine content unsupported")
        name = resources[node.get("idref")]
        if media[name] != "application/xhtml+xml" or name in spine_paths:
            raise Error("Spine must contain unique XHTML documents")
        spine_paths.append(name)
    docs = spine_paths + sorted(n for n, m in media.items() if m == "application/xhtml+xml" and n not in spine_paths)
    trees = {opf_path: package}
    items = []
    verified_images = set()
    total_pixels = 0
    review_text_bytes = 0
    preview_bytes = 0
    for name in docs:
        tree = _xml(entries[name], name)
        trees[name] = tree
        if tree.getroot().tag != f"{{{XHTML}}}html":
            raise Error(f"Expected XHTML html root: {name}")
        body = tree.getroot().find(f"{{{XHTML}}}body")
        if body is None:
            raise Error(f"Missing XHTML body: {name}")
        parents = {child: parent for parent in tree.iter() for child in parent}
        for node in tree.iter():
            if not isinstance(node.tag, str):
                continue
            local = node.tag.rsplit("}", 1)[-1].lower()
            if local == "img" and node.tag != f"{{{XHTML}}}img":
                raise Error(f"Foreign-namespace img is unsupported: {name}")
            if local in {"script", "iframe", "object", "embed", "canvas", "picture", "svg", "audio", "video", "base", "template"}:
                raise Error(f"Unsupported {local} content: {name}")
            if node.get(f"{{{XML}}}base") is not None or any(k.lower().startswith("on") for k in node.attrib):
                raise Error(f"Active content/xml:base unsupported: {name}")
        images = list(body.iter(f"{{{XHTML}}}img"))
        if len(images) != len(list(tree.iter(f"{{{XHTML}}}img"))):
            raise Error(f"Images outside XHTML body unsupported: {name}")
        chapter_text = _text(body)
        for index, image in enumerate(images, 1):
            if (set(image.attrib) & {"role", "title", "tabindex", "accesskey", "contenteditable", "longdesc", "srcset", "usemap", "ismap"}
                    or any(k.lower().startswith("aria-") for k in image.attrib)):
                raise Error(f"Image naming/description overrides or responsive/maps unsupported: {name} image {index}")
            cursor = image
            figure = None
            while cursor is not None:
                if (cursor.get("aria-hidden", "false").lower() != "false"
                        or set(cursor.attrib) & {"hidden", "inert"}):
                    raise Error(f"Hidden image/ancestor unsupported: {name} image {index}")
                if "role" in cursor.attrib or "contenteditable" in cursor.attrib:
                    raise Error(f"Explicit image/ancestor role or editing context unsupported: {name}")
                if cursor.tag in {f"{{{XHTML}}}{tag}" for tag in ("a", "button", "summary", "label", "legend")}:
                    raise Error(f"Linked images require functional-text review and are unsupported: {name}")
                if cursor is not image and set(cursor.attrib) & {"aria-label", "aria-labelledby", "aria-describedby", "aria-details"}:
                    raise Error(f"Ancestor accessible-name override unsupported: {name}")
                if cursor.tag == f"{{{XHTML}}}figure" and figure is None:
                    figure = cursor
                cursor = parents.get(cursor)
            image_path = _resolve(name, image.get("src", ""))
            image_type = media.get(image_path)
            if image_path not in entries or image_type not in ("image/png", "image/jpeg"):
                raise Error(f"Only manifest-declared local PNG/JPEG img resources are supported: {image_path}")
            data = entries[image_path]
            if not ((image_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"))
                    or (image_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"))):
                raise Error(f"Image signature does not match media type: {image_path}")
            if image_path not in verified_images:
                try:
                    with Image.open(io.BytesIO(data), formats=["PNG", "JPEG"]) as decoded:
                        pixels = decoded.width * decoded.height
                        if pixels > 25_000_000 or pixels < 1 or total_pixels + pixels > 100_000_000:
                            raise Error("Raster limit: 25 million pixels per image; 100 million total")
                        if getattr(decoded, "n_frames", 1) != 1:
                            raise Error(f"Animated/multiframe images unsupported: {image_path}")
                        decoded.verify()
                    with Image.open(io.BytesIO(data), formats=["PNG", "JPEG"]) as decoded:
                        decoded.load()
                    total_pixels += pixels
                    verified_images.add(image_path)
                except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
                    raise Error(f"Cannot decode supported raster: {image_path}") from exc
            parent = parents.get(image)
            caption = _text(figure.find(f"{{{XHTML}}}figcaption")) if figure is not None else ""
            near_text = _text(figure if figure is not None else parent)
            review_text_bytes += len((chapter_text + caption + near_text).encode("utf-8"))
            preview_bytes += len(data)
            if review_text_bytes > 4 * 1024 * 1024 or preview_bytes > 24 * 1024 * 1024:
                raise Error("Review packet limit: 4 MiB occurrence context; 24 MiB occurrence previews")
            items.append({"id": digest((name + "\0" + str(index)).encode("utf-8")),
                          "document": name, "index": index, "image": image_path, "media_type": image_type,
                          "document_sha256": digest(entries[name]), "image_sha256": digest(data),
                          "current_alt": image.get("alt"), "chapter_text": chapter_text,
                          "caption": caption, "near_text": near_text})
            if len(items) > MAX_ITEMS:
                raise Error("EPUB exceeds 200 image occurrence limit")
    # Shared resource changes (including package/spine, CSS and fonts) invalidate
    # every approval. Other XHTML changes invalidate their own document only.
    # Include every raster in shared context too: an image may be referenced by
    # CSS as well as img, and this product does not interpret the CSS cascade.
    independent = set(docs)
    shared = {n: digest(data) for n, data in sorted(entries.items()) if n not in independent}
    # A normal corrected delivery updates last-modified. Ignore only this
    # validated timestamp value, binding every other package field and declared
    # namespace (including prefixes appearing in vocabulary attribute values).
    normalized_package = copy.deepcopy(package)
    next(n for n in normalized_package.iter(f"{{{OPF}}}meta") if n.get("property") == "dcterms:modified").text = "IGNORED-TIMESTAMP"
    namespaces = list(ET.iterparse(io.BytesIO(entries[opf_path]), events=("start-ns",)))
    shared[opf_path] = digest(canonical({"xml": _xml_bytes(normalized_package).decode("utf-8"),
                                       "namespaces": [list(value) for _, value in namespaces]}))
    snapshot = {"format": "altfreeze.snapshot.v1", "source_sha256": digest(raw),
                "title": _text(titles[0]), "identifier": _text(matching_ids[0]),
                "context_sha256": digest(canonical(shared)), "items": items}
    snapshot["snapshot_sha256"] = digest(canonical(snapshot))
    return Book(snapshot, entries, trees, opf_path, infos)


def _pending(item) -> dict:
    return {"id": item["id"], "action": "pending", "alt": "", "reviewer": "", "note": ""}


def _initial(snapshot) -> dict:
    return {"format": "altfreeze.decisions.v1", "snapshot_sha256": snapshot["snapshot_sha256"],
            "items": [_pending(i) for i in snapshot["items"]]}


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _packet(book, destination, decisions=None):
    from .review import render_review
    snapshot = book.snapshot
    decisions = decisions or _initial(snapshot)
    _write_json(destination / "snapshot.json", snapshot)
    _write_json(destination / "decisions.json", decisions)
    images = {i["image"]: book.entries[i["image"]] for i in snapshot["items"]}
    (destination / "review.html").write_text(render_review(snapshot, decisions, images), encoding="utf-8")


def _transaction(out, producer):
    destination = Path(out).absolute()
    if destination.exists() or destination.is_symlink():
        raise Error(f"Destination already exists: {destination.name}; choose a new directory")
    if not destination.parent.is_dir():
        raise Error("Destination parent must already exist")
    staging = Path(tempfile.mkdtemp(prefix=".altfreeze-", dir=destination.parent))
    try:
        result = producer(staging)
        # Do not clobber an output created by a second operator during processing.
        if destination.exists() or destination.is_symlink():
            raise Error("Destination appeared during processing")
        os.rename(staging, destination)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def export_packet(epub, out) -> dict:
    book = inspect_epub(epub)
    def produce(staging):
        _packet(book, staging)
        return book.snapshot
    return _transaction(out, produce)


def _valid_text(value, field, limit=2000):
    if not isinstance(value, str) or len(value) > limit:
        raise Error(f"{field} must be text of at most {limit} characters")
    if any(not (ord(c) in (9, 10, 13) or 0x20 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise Error(f"{field} contains invalid XML characters")


def _validate_decisions(snapshot, decisions, complete):
    if set(decisions) != {"format", "snapshot_sha256", "items"} or decisions.get("format") != "altfreeze.decisions.v1":
        raise Error("Unsupported decisions format or fields")
    if decisions.get("snapshot_sha256") != snapshot["snapshot_sha256"]:
        raise Error("Decisions belong to a different snapshot")
    rows = decisions.get("items")
    if not isinstance(rows, list) or len(rows) != len(snapshot["items"]):
        raise Error("Decisions must contain exactly one row per image occurrence")
    by_id = {i["id"]: i for i in snapshot["items"]}
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "action", "alt", "reviewer", "note"}:
            raise Error("Invalid decision row fields")
        rid = row["id"]
        if not isinstance(rid, str) or rid not in by_id or rid in seen:
            raise Error("Unknown or duplicate decision occurrence ID")
        seen.add(rid)
        action = row["action"]
        if not isinstance(action, str) or action not in {"pending", "keep", "replace", "decorative", "needs-work"}:
            raise Error(f"Unknown action for {rid}")
        for field, limit in (("alt", 2000), ("reviewer", 120), ("note", 4000)):
            _valid_text(row[field], field, limit)
        if action in {"keep", "replace", "decorative"} and not row["reviewer"].strip():
            raise Error(f"Approved decision requires reviewer: {rid}")
        if action == "replace" and not row["alt"].strip():
            raise Error(f"Replace requires nonblank alt: {rid}")
        if action != "replace" and row["alt"]:
            raise Error(f"Only replace may supply alt text: {rid}")
        if action == "keep" and not (by_id[rid]["current_alt"] or "").strip():
            raise Error(f"Keep requires existing nonblank alt; use replace or decorative: {rid}")
        if action == "decorative" and not row["note"].strip():
            raise Error(f"Decorative requires a rationale: {rid}")
        if complete and action in {"pending", "needs-work"}:
            raise Error(f"Unresolved decision ({action}) for {rid}; review every occurrence")


def validate(epub, packet, decisions_path=None, complete=True):
    book = inspect_epub(epub)
    recorded = read_json(Path(packet) / "snapshot.json")
    if canonical(recorded) != canonical(book.snapshot):
        raise Error("Snapshot does not exactly match EPUB; use its original source or reconcile")
    decisions = read_json(decisions_path if decisions_path is not None else Path(packet) / "decisions.json")
    _validate_decisions(recorded, decisions, complete)
    return book, recorded, decisions


def _write_epub(book, target, changes):
    with zipfile.ZipFile(target, "w") as archive:
        for original in book.infos:
            info = copy.copy(original)
            if info.filename == "mimetype":
                info.extra = b""
                info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, changes.get(info.filename, book.entries[info.filename]))


def apply(epub, packet, out, decisions_path=None) -> dict:
    book, snapshot, decisions = validate(epub, packet, decisions_path, complete=True)
    lookup = {i["id"]: i for i in snapshot["items"]}
    changed_docs = set()
    audit = []
    for row in decisions["items"]:
        item = lookup[row["id"]]
        new_alt = item["current_alt"] if row["action"] == "keep" else row["alt"] if row["action"] == "replace" else ""
        if new_alt != item["current_alt"]:
            image = list(book.trees[item["document"]].getroot().find(f"{{{XHTML}}}body").iter(f"{{{XHTML}}}img"))[item["index"] - 1]
            image.set("alt", new_alt)
            changed_docs.add(item["document"])
        audit.append({**row, "document": item["document"], "index": item["index"],
                      "before": item["current_alt"], "after": new_alt})
    changes = {name: _xml_bytes(book.trees[name]) for name in changed_docs}
    if changed_docs:
        modified = next(n for n in book.trees[book.opf_path].iter(f"{{{OPF}}}meta") if n.get("property") == "dcterms:modified")
        modified.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        changes[book.opf_path] = _xml_bytes(book.trees[book.opf_path])
    def produce(staging):
        target = staging / "publication.epub"
        _write_epub(book, target, changes)
        output = inspect_epub(target)
        next_decisions = _initial(output.snapshot)
        previous = {r["id"]: r for r in decisions["items"]}
        for row in next_decisions["items"]:
            prior = previous[row["id"]]
            row.update(action="decorative" if prior["action"] == "decorative" else "keep", reviewer=prior["reviewer"], note=prior["note"])
        _validate_decisions(output.snapshot, next_decisions, complete=True)
        review = staging / "review"
        review.mkdir()
        _packet(output, review, next_decisions)
        receipt = {"format": "altfreeze.receipt.v1", "input_sha256": snapshot["source_sha256"],
                   "output_sha256": output.snapshot["source_sha256"], "snapshot_sha256": snapshot["snapshot_sha256"],
                   "decisions_sha256": digest(canonical(decisions)), "output_snapshot_sha256": output.snapshot["snapshot_sha256"],
                   "changed_entries": sorted(changes), "items": audit}
        _write_json(staging / "receipt.json", receipt)
        return receipt
    return _transaction(out, produce)


def reconcile(old_epub, packet, new_epub, out, decisions_path=None) -> dict:
    _, old, decisions = validate(old_epub, packet, decisions_path, complete=False)
    new_book = inspect_epub(new_epub)
    new = new_book.snapshot
    if old["identifier"] != new["identifier"]:
        raise Error("Publication identifier differs; refusing cross-book reconciliation")
    before = {i["id"]: i for i in old["items"]}
    decisions_by_id = {r["id"]: r for r in decisions["items"]}
    after = {i["id"]: i for i in new["items"]}
    next_decisions = _initial(new)
    rows = {r["id"]: r for r in next_decisions["items"]}
    report = {"format": "altfreeze.reconciliation.v1", "old_source_sha256": old["source_sha256"],
              "new_source_sha256": new["source_sha256"], "items": [],
              "summary": {"retained": 0, "invalidated": 0, "removed": 0, "new": 0}}
    for item in old["items"]:
        rid = item["id"]
        reasons = []
        if rid not in after:
            status = "removed"
            reasons.append("Occurrence no longer present at this document/index")
        else:
            other = after[rid]
            if old["context_sha256"] != new["context_sha256"]:
                reasons.append("Shared publication resources changed (package, CSS, fonts or other shared content)")
            if item["document_sha256"] != other["document_sha256"]:
                reasons.append("Chapter bytes changed")
            if item["image_sha256"] != other["image_sha256"] or item["image"] != other["image"]:
                reasons.append("Image resource changed")
            status = "invalidated" if reasons else "retained"
            if status == "retained":
                rows[rid].update(decisions_by_id[rid])
        report["items"].append({"id": rid, "status": status, "reasons": reasons,
                                "previous_decision": decisions_by_id[rid]})
        report["summary"][status] += 1
    for item in new["items"]:
        if item["id"] not in before:
            report["items"].append({"id": item["id"], "status": "new", "reasons": ["New occurrence"], "previous_decision": None})
            report["summary"]["new"] += 1
    def produce(staging):
        _packet(new_book, staging, next_decisions)
        _write_json(staging / "reconciliation.json", report)
        return report
    return _transaction(out, produce)
