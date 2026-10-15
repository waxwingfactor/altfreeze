"""Make a CC0 synthetic two-chapter EPUB and one realistic vendor revision.

No third-party packages or source checkout imports are needed.
"""
import struct
import sys
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


def png():
    width, height = 480, 220
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            color = (237, 244, 250)
            if y >= 180 or x == 40 and 30 <= y <= 180:
                color = (55, 75, 94)
            for left, top, right, bottom in ((90, 110, 155, 179), (205, 75, 270, 179), (320, 40, 385, 179)):
                if left <= x < right and top <= y < bottom:
                    color = (39, 94, 149)
            row.extend(color)
        rows.append(b"\0" + row)
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")


def entries(revised=False):
    xhtml = 'xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en"'
    content = {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": b'<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        "EPUB/package.opf": b'''<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0" unique-identifier="pub-id"><metadata><dc:identifier id="pub-id">urn:uuid:7655a832-d979-489d-bb16-9589987c14aa</dc:identifier><dc:title>Community Orchard Notes</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">2026-10-15T12:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="one" href="chapter-1.xhtml" media-type="application/xhtml+xml"/><item id="two" href="chapter-2.xhtml" media-type="application/xhtml+xml"/><item id="art" href="images/harvest.png" media-type="image/png"/><item id="css" href="style.css" media-type="text/css"/></manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>''',
        "EPUB/nav.xhtml": f'<html {xhtml} xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><nav epub:type="toc"><h1>Contents</h1><ol><li><a href="chapter-1.xhtml">Harvest</a></li><li><a href="chapter-2.xhtml">Illustration practice</a></li></ol></nav></body></html>'.encode(),
        "EPUB/chapter-1.xhtml": f'<html {xhtml}><head><title>Harvest</title><link href="style.css" rel="stylesheet" type="text/css"/></head><body><h1>Harvest</h1><p>The orchard harvest rose over three seasons. This illustration introduces the trend; exact figures appear in our field notebook.</p><figure><img src="images/harvest.png" alt="Chart"/><figcaption>Harvest trend over three seasons.</figcaption></figure><p>The volunteers expanded the planted area each spring.</p></body></html>'.encode(),
        "EPUB/chapter-2.xhtml": f'<html {xhtml}><head><title>Illustration practice</title></head><body><h1>Illustration practice</h1><p>{"The revised exercise asks readers to identify the blue bars." if revised else "In this exercise, readers describe the shape and colour of the illustration."}</p><figure><img src="images/harvest.png"/><figcaption>A repeated illustration used for a different purpose.</figcaption></figure></body></html>'.encode(),
        "EPUB/style.css": b'body { font-family: serif; } img { max-width: 100%; }',
        "EPUB/images/harvest.png": png(),
    }
    if revised:
        content["EPUB/package.opf"] = content["EPUB/package.opf"].replace(b"2026-10-15T12:00:00Z", b"2026-10-15T13:00:00Z")
    return content


def write(path, content):
    with ZipFile(path, "w") as archive:
        for name, data in content.items():
            archive.writestr(name, data, compress_type=ZIP_STORED if name == "mimetype" else ZIP_DEFLATED)


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / "orchard.epub", entries())
    write(folder / "orchard-revised.epub", entries(True))
    print("Created orchard.epub and orchard-revised.epub (synthetic CC0 examples)")


if __name__ == "__main__":
    main()
