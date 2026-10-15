# Orchard example (CC0)

`make_demo.py` creates `orchard.epub` and `orchard-revised.epub` using only Python's standard library. All text, raster artwork and generated book contents are dedicated to the public domain under CC0-1.0. This is a constructed demonstration, not a customer publication.

The same three-bar illustration occurs in two chapters for different editorial purposes. The first starts with weak text `Chart`; the second has no alt attribute. Review each occurrence separately. The revision changes chapter 2 prose and the publication modification timestamp. Reconciliation retains chapter 1 and reopens chapter 2.

```sh
python make_demo.py demo
altfreeze export demo/orchard.epub --out demo/review
```

Open the review HTML, choose Replace and enter suitable descriptions plus reviewer names. Save the returned JSON. Then:

```sh
altfreeze check demo/orchard.epub demo/review --decisions returned.json
altfreeze reconcile demo/orchard.epub demo/review demo/orchard-revised.epub --decisions returned.json --out demo/next
```

The fixture is designed to test control flow and repeated-image context. A real statistical chart may need accessible data or an extended description outside this product's short-alt scope.
