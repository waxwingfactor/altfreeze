# Bounded independent competition review

Research date: 2026-10-15. Researcher: separate AI agent assigned adversarial competition research; no customer interviews, private product evaluations, adoption or measured savings claimed.

## Decision

Reject generic EPUB alt-text extraction, contextual preview, image-table editing or spreadsheet round trips as differentiation. Existing tools already provide those workflows. A narrower chapter-bound editorial approval ledger is defensible as an inferred opportunity: small press production editors reviewing existing EPUB 3 files returned by composition vendors, preserving approvals only under explicit source-identity rules and reopening changed contexts. This is a bounded feature comparison, not proof of universal uniqueness or demonstrated customer demand.

## Current alternatives and documented capabilities

- Ace by DAISY: image inventory with alt text and identifiable descriptions plus automated accessibility checks. Inspection/reporting rather than decision application or conservative approval reconciliation. https://kb.daisy.org/publishing/docs/epub/validation/ace.html
- Ace SMART: guided human conformance evaluation, saved evaluations and reports; its guide requires separate publication editing software. It does not document an occurrence-level description-authoring and byte-bound approval carryover workflow. https://smart.daisy.org/user-guide/overview.html ; https://kb.daisy.org/publishing/docs/epub/validation/smart.html
- Sigil Access-Aide: image/alt collection, editable image table, direct EPUB changes, recovery from image metadata. A strong direct-editor alternative; separate reviewer packets and a revision approval ledger are outside its documented workflow. Current source revision checked: 746793b35771a54d5f67cbc3df25d5d035431684 (2024-10-15). https://github.com/kevinhendricks/Access-Aide
- ImageAltGen: Ollama drafting, exclusions, individual review/regeneration, EPUB roles, apply into EPUB. Generation/review/apply already exists. Current README checked at a74b86d3f9b40d4179ee0ed739e52b6e634f1817 (2026-05-10). https://github.com/byword77/ImageAltGen/tree/a74b86d3f9b40d4179ee0ed739e52b6e634f1817
- b-t-k EPUB scripts: extract image/caption/alt into XLSX and import edited alt into EPUB. Closest free round-trip competitor. Source examined at 861c6446e55084e9e2cb059a0765635b31f60603 (2025-05-22): importer matches src and replaces the first matching img in each XHTML document; no chapter/image hash or human approval ledger. Its README describes workflow-specific example scripts and weak error checking. https://github.com/b-t-k/epub-python-scripts/blob/861c6446e55084e9e2cb059a0765635b31f60603/Run_alttext_update.py ; https://github.com/b-t-k/epub-python-scripts/blob/861c6446e55084e9e2cb059a0765635b31f60603/README.md
- Circular Software / SIDD: contextual description editor, alt and extended description fields, collaborators, offline image/PDF/TSV handoff, bulk application into InDesign. Genuinely capable whole workflow. Prefer it when a team controls InDesign production and its integrations. https://www.circularsoftware.com/kb/topic/image-description-tools ; https://circularsoftware.com/tutorial/accessible-fixed-layout-ebooks-with-circular-software
- HoloPress: IDML/PDF to EPUB, private AI drafting, editable descriptions, editor spreadsheet export/import, validation reports. Advertised platform is beta; spreadsheet round trip directly overlaps generic handoff claims. https://www.holographpressworks.com/holopress
- Poet: historically crowdsourced image descriptions for DAISY/EPUB. Current hosted Poet says it became a training site; do not describe the historical authoring service as current hosted capability. https://diagramcenter.org/poet.html ; https://poet.bornaccessible.org/
- Describler: experimental SVG/data-visualization reader/accessibility tooling, adjacent rather than an EPUB editorial reconciliation alternative. https://describler.com/

## Corrections and revision-safety evidence

Native tools already detect some outdated alt text. Adobe's official guide, updated 2026-08-31, documents an outdated-alt-text indicator after cropping an image or moving it within its frame. Do not claim stale-alt tracking is generally absent. https://helpx.adobe.com/indesign/desktop/add-graphics-and-media/add-edit-graphics/generate-alt-text-for-images.html

Circular Software documents that InDesign object IDs used for image descriptions can reset after structural changes (IDML save/version conversion). Its tools detect marker mismatches, alert users and preserve old/new reference information. This supports the reality of handoff fragility, while proving competent alternatives already address related safety issues. Their documented mechanism is InDesign identifiers rather than chapter/image byte-bound approvals for vendor-delivered EPUB files. https://www.circularsoftware.com/kb/article/fixing-marker-mismatches

## Workflow evidence and limits

A firsthand production account describes creating alt text in spreadsheets, merging it into EPUB, exporting fresh alt text to a production editor, performing code/reading-system checks and accepting changes over one or two rounds. This supports the existence of the editorial handoff; it does not establish measured prevalence or demand for this specific ledger. https://macblaze.ca/?p=15853

UNICEF's Accessible Textbooks for All guidance explicitly recommends preparing image descriptions in a spreadsheet with a naming convention matching image files. https://www.accessibletextbooksforall.org/stories/creating-accessible-epub

The value proposition should remain conservative source-identity and decision control, not accessibility certification or description quality assessment. Chapter/image bytes alone do not establish unchanged visual or publication context; bind shared dependencies (package/spine, CSS, fonts and other resources) or state the limitation. Reused images in distinct chapter contexts must remain distinct occurrences. Exact byte rules cause deliberate false invalidations after harmless reserialization and substantive package changes; the implemented contract ignores only the validated unrefined modification timestamp value. An attributed decision file is not an authenticated signature or proof of reviewer identity.
