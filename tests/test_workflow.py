import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from altfreeze.core import Error, apply, export_packet, inspect_epub, reconcile, validate

spec = importlib.util.spec_from_file_location("demo", Path(__file__).resolve().parents[1] / "examples" / "make_demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class Workflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.epub = self.root / "source.epub"
        demo.write(self.epub, demo.entries())
        self.packet = self.root / "packet"
        self.snapshot = export_packet(self.epub, self.packet)

    def approve(self):
        d = json.loads((self.packet / "decisions.json").read_text())
        for i, row in enumerate(d["items"]):
            row.update(action="replace", alt=f'Blue bars: "season {i + 1}" & growth — récolte.', reviewer="Subject editor")
        (self.packet / "decisions.json").write_text(json.dumps(d))
        return d

    def revised(self, changes):
        content = demo.entries()
        content.update(changes)
        target = self.root / "revised.epub"
        demo.write(target, content)
        return target

    def test_pending_blocks_apply_without_output(self):
        with self.assertRaises(Error):
            apply(self.epub, self.packet, self.root / "out")
        self.assertFalse((self.root / "out").exists())

    def test_partial_check_is_explicit(self):
        validate(self.epub, self.packet, complete=False)
        with self.assertRaises(Error):
            validate(self.epub, self.packet)

    def test_occurrences_not_deduplicated(self):
        one, two = self.snapshot["items"]
        self.assertEqual(one["image_sha256"], two["image_sha256"])
        self.assertNotEqual(one["id"], two["id"])
        self.assertIsNone(two["current_alt"])

    def test_apply_unicode_escaping_and_postapply_lineage(self):
        decisions = self.approve()
        original = self.epub.read_bytes()
        out = self.root / "final"
        receipt = apply(self.epub, self.packet, out)
        self.assertEqual(original, self.epub.read_bytes())
        self.assertEqual(receipt["output_sha256"], inspect_epub(out / "publication.epub").snapshot["source_sha256"])
        final, _, _ = validate(out / "publication.epub", out / "review")
        for item, row in zip(final.snapshot["items"], decisions["items"]):
            self.assertEqual(item["current_alt"], row["alt"])
        ledger = reconcile(out / "publication.epub", out / "review", out / "publication.epub", self.root / "same")
        self.assertEqual(ledger["summary"]["retained"], 2)
        validate(out / "publication.epub", self.root / "same")
        for name, data in inspect_epub(self.epub).entries.items():
            if name not in receipt["changed_entries"]:
                self.assertEqual(data, final.entries[name])

    def test_reconcile_changed_chapter_only_reopens_that_chapter(self):
        self.approve()
        target = self.root / "revision.epub"
        demo.write(target, demo.entries(True))
        report = reconcile(self.epub, self.packet, target, self.root / "next")
        self.assertEqual(report["summary"], {"retained": 1, "invalidated": 1, "new": 0, "removed": 0})
        rows = json.loads((self.root / "next" / "decisions.json").read_text())["items"]
        self.assertEqual([r["action"] for r in rows], ["replace", "pending"])

    def test_shared_css_change_reopens_everything(self):
        self.approve()
        new = self.revised({"EPUB/style.css": b"img {display: none}"})
        report = reconcile(self.epub, self.packet, new, self.root / "next")
        self.assertEqual(report["summary"]["invalidated"], 2)

    def test_changed_image_reopens_every_occurrence(self):
        self.approve()
        # PNG signature remains valid; content-byte identity is intentionally conservative.
        new = self.revised({"EPUB/images/harvest.png": demo.png() + b"new"})
        report = reconcile(self.epub, self.packet, new, self.root / "next")
        self.assertEqual(report["summary"]["invalidated"], 2)

    def test_stale_exact_apply_fails(self):
        self.approve()
        new = self.revised({"EPUB/style.css": b"body {}"})
        with self.assertRaisesRegex(Error, "Snapshot"):
            apply(new, self.packet, self.root / "out")

    def test_new_and_removed_occurrences(self):
        self.approve()
        content = demo.entries()
        content["EPUB/chapter-2.xhtml"] = content["EPUB/chapter-2.xhtml"].replace(b'<img src="images/harvest.png"/>', b'')
        content["EPUB/chapter-1.xhtml"] = content["EPUB/chapter-1.xhtml"].replace(b'</figure>', b'<img src="images/harvest.png" alt="Second"/></figure>')
        new = self.revised(content)
        report = reconcile(self.epub, self.packet, new, self.root / "next")
        self.assertEqual(report["summary"], {"retained": 0, "invalidated": 1, "removed": 1, "new": 1})

    def test_tampered_snapshot_is_recomputed(self):
        snap = copy.deepcopy(self.snapshot)
        snap["items"][0]["current_alt"] = "pretend"
        (self.packet / "snapshot.json").write_text(json.dumps(snap))
        with self.assertRaisesRegex(Error, "Snapshot"):
            validate(self.epub, self.packet, complete=False)

    def test_foreign_decisions_rejected(self):
        d = self.approve()
        d["snapshot_sha256"] = "0" * 64
        (self.packet / "decisions.json").write_text(json.dumps(d))
        with self.assertRaisesRegex(Error, "different snapshot"):
            validate(self.epub, self.packet)

    def test_destination_never_overwritten(self):
        self.approve()
        out = self.root / "out"
        out.mkdir()
        (out / "note").write_text("preserve")
        with self.assertRaises(Error):
            apply(self.epub, self.packet, out)
        self.assertEqual((out / "note").read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
