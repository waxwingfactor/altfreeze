# Independent AI-agent focused re-review

Date: 2026-10-15. Reviewer: separate AI agent assigned adversarial competition and code review. This is an independent AI review, not a human approval or a review from another GitHub account. The reviewer did not edit application source files. This record supplements the initial findings in [review-initial.md](review-initial.md) and preserves their history.

## Result

No remaining release-blocking code finding was identified in the focused repaired scope. The browser validation repair is present. Final public-artifact installation and final rendered-browser evidence are separate release gates and are not claimed by this source review.

Source files reviewed and exercised:

- `src/altfreeze/core.py`: SHA-256 `713ddba10ace128827ab59953c8d280cd0c3d63a3d3d4dc4be793e6a70588741`
- `src/altfreeze/review.py`: SHA-256 `a9706060a21aa7e63917d33204c16bcedcc7364f5b760464e36e68e85c1fd1d9`
- `src/altfreeze/cli.py`: SHA-256 `e16e1c86ec2b575a3fd47db0f5938dd6a6832441eea139148d6404175b81921b`

The complete current source test suite passed independently: **146 tests in 3.37 seconds**, using the local development Python environment. This is not a fresh published-wheel installation test.

## Finding dispositions checked

- Decorative/functional ambiguity: explicit image and ancestor roles are now rejected; image title/focusability/editing/ARIA attributes are rejected; inert/hidden ancestors and native control-label contexts are refused. Reproduced inert, summary and label cases now raise the public `Error`.
- Shared raster hole: all rasters now participate in global context. An otherwise unchanged CSS background PNG change invalidates all approvals. This is intentionally conservative and documented; no CSS dependency inference is claimed.
- Review/CLI disagreement: browser limits now use 2,000/120/4,000 Unicode code points, validate XML character ranges, match the Python whitespace test, and check exact root/row fields. The CLI remains the final gate, including duplicate JSON-key rejection.
- JSON resource boundary: one bounded nonblocking file-descriptor read plus regular-file validation replaces stat-then-read. Named pipes promptly fail on the reviewed POSIX platform for both JSON and EPUB. Oversized JSON is rejected using actual read bytes. Huge-integer parser errors are converted to the public error type.
- Malformed URLs: urlsplit failures are wrapped as `Error`. The malformed `//[` image-reference reproduction fails through the supported error path.
- Modification timestamp value: reconciliation ignores only the validated, unrefined publication timestamp's text in the normalized package comparison, while binding the remaining parsed package and namespace declarations. A chapter correction with an updated timestamp retains other chapters' decisions; title, CSS and image changes invalidate them. Exact-source application still binds raw archive bytes.
- Snapshot type integrity: canonical-byte comparison rejects a floating-point `1.0` substituted for an integer occurrence index. Local/central ZIP flags/method/range checks are present.
- Displayed prose excludes comments and processing instructions while preserving following text. Changed-document serialization and the postapply baseline remain explicit parts of the contract.

## Independent two-round checks

`focused_rereview.py` builds its own small EPUB fixture without importing the application's example or writer. It performs an initial Replace/Decorative application, validates receipt hashes and postapply baseline, changes a chapter plus modification date, observes retained=1/invalidated=1, confirms unresolved application writes no output, returns a second reviewer decision, and validates the final baseline. It also exercises timestamp-only retention, global invalidation for title/background/CSS changes, malformed URLs, typed snapshots and actual oversized JSON. Results with source hashes: `focused-rereview-results.json`.

`real_fixture_rereview.py` separately exercised the official IDPF `epub30-spec.epub`, SHA-256 `def6a7a1d2302689c77d7c04585f9eb2da825a7ef546888cfe2f5fbba92d51ce`. All ten existing image occurrences were supported. After an initial engineering-only Keep round, a modified terminology chapter plus updated package date produced **9 retained and 1 invalidated** decision. Unresolved apply failed without output. A second engineering decision allowed application and a valid postapply baseline. Final EPUBCheck 5.4.0 exited 0 with **zero errors and warnings**, reporting EPUB 3.4 rules. Results: `real-fixture-rereview-results.json`.

These fixture decisions were engineering transaction tests, not substantive human image-description approvals or accessibility certification. The official sample is not redistributed by this reviewer.

## Remaining review limits

The supported profile excludes many legitimate EPUB constructs. In particular, explicit semantic roles, linked/control images, long descriptions, SVG, fixed layout, font-obfuscation/encryption files and several media types require other tools. Hashes and attribution are not signatures. Cross-chapter semantic effects and description quality remain editorial responsibilities. Documentation was reviewed as it appeared; final public links, release hashes, installed behavior and rendered states still require release verification.

The script/result basenames above identify internal engineering work artifacts; they are not bundled executables. The source tests and public release verification assets are the reproducible supported evidence.
