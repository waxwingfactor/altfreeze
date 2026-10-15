# Independent AI-agent code review — initial findings

Date: 2026-10-15. Reviewer: separate AI agent assigned competition and adversarial code review. This is not a human review or a GitHub approval from another account. Reviewed src/altfreeze/core.py, review.py, cli.py, packaging, demo generator and current tests. Documentation was a five-line placeholder at initial review; final user documentation needs subsequent review. No core files were edited by this reviewer.

The existing suite passed independently: 98 tests in 1.67 seconds using the development Python environment. That is local test evidence, not published-artifact installation verification.

## Findings requiring resolution or an explicit bounded disposition

### P2: Decorative decisions preserve attributes that defeat decorative semantics

Initial core.py lines 261 and 443–447 permit an img with explicit role="img" and only write alt="" for a decorative decision. title, tabindex and several global ARIA attributes also pass. Reproduction outputs `<img role="img" title="Old image title" tabindex="0" alt=""/>`, and its postapply baseline validates. An empty alt is not sufficient to mark an image decorative when an explicit img role or another accessible name remains. Reject the ambiguous source profile or deliberately implement and test semantic changes. Ancestor roles that flatten descendants or make the image functional also need consideration.

Primary rule: https://www.w3.org/WAI/standards-guidelines/act/rules/23a2a8/ . It defines the no-explicit-role requirement for the empty-alt decorative case.

Reproduction: work/review_reproductions.py, first case.

### P2: Shared CSS background rasters escape reconciliation invalidation

Initial core.py lines 314–315 exclude every manifest PNG/JPEG from global context, even rasters not represented by img occurrences. A PNG referenced from unchanged CSS as a background can change without changing the global context or any occurrence image hash. Reproduction changes that background and reconcile returns retained=2, invalidated=0. Bind those shared raster dependencies or adopt a deliberately more conservative image invalidation rule.

Reproduction: work/review_reproductions.py, second case.

### P2: Review page accepts records that production rejects

Initial review.py lines 297–298, 470, 472 allow reviewer strings of 1000 and notes of 20000 characters, while core.py line 400 limits those to 120/4000. An otherwise approved record can be shown ready and saved, then rejected during production. Align all browser validation, field limits, messages and Python validation, accounting for JavaScript UTF-16 length versus Python code-point counts if Unicode limits are promised identically.

Reproduction: work/review_reproductions.py, third case (121-character reviewer).

### P2: JSON input resource limit uses a stale stat followed by an unbounded read

Initial core.py lines 64–67 check stat().st_size before read_text(). A growing/swapped file bypasses the advertised 16 MiB limit. FIFO or device paths can block or consume unbounded memory. Read at most MAX_JSON+1 bytes from one opened source, check actual size, then decode/parse. Consider rejecting nonregular input paths if the interface promises file-only input.

Reproduction: work/review_edge_cases.py spoofs a pre-growth zero-size stat and successfully parses a >16 MiB JSON file.

### P2: Malformed resource URL escapes the stable CLI error contract

Initial core.py line 98 calls urlsplit without handling ValueError. `src="//["` produces ValueError("Invalid IPv6 URL"), escaping Error and the CLI handler to give a traceback. Wrap URL-parser failures as Error and include malformed references in the CLI acceptance tests.

Reproduction: work/review_edge_cases.py, first case.

### Product-value concern: ordinary modification timestamps reopen the entire book

Initial core.py lines 314–315 bind the full OPF byte string globally. A vendor changing one chapter should ordinarily also update dcterms:modified, which then invalidates every approval. This is conservative, but substantially limits the selective-chapter value proposition; the demo revision currently retains the old timestamp. A narrowly specified exception for the one validated publication modification timestamp could preserve strict binding for all other package content. If the policy remains, disclose that ordinary vendor package updates reopen all approvals and avoid selective-retention savings claims.

Current primary EPUB3.3 recommendation: https://www.w3.org/TR/epub-33/#sec-metadata-modified . Updating the date is recommended with “should”, not a normative MUST in the current text.

## Strengths observed

Source hash and parsed entries originate from the same bounded raw read. Input archives are not extracted. Archive/expanded/member/XML/image/context budgets are explicit. XML DTD/entity declarations are refused. All occurrence decisions are required before output. Snapshots are recomputed, not trusted. The output is created transactionally, preserves source bytes, and includes a postapply baseline. Browser output escapes source text and embeds a restrictive offline CSP. These strengths do not dispose of the findings above.

## Limits of review

A separate rendered desktop/mobile/keyboard inspection and independent installation of actual public wheel/sdist artifacts remain required for release verification. Attribution fields are intentionally unauthenticated; this is not a signature or proof of identity. No universal EPUB compatibility or accessibility certification was evaluated.
