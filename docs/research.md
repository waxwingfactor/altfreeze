# Independent discovery evidence — EPUB image-description decisions

Research date: 15 October 2026. Researcher: a separate AI discovery agent. This is a bounded desk-research assessment, not customer validation, an exhaustive product census, or a claim of universal novelty.

## Recommendation

Conditional **go** for a vendor-neutral, offline review-decision ledger for small university-press production teams handling image-heavy, reflowable EPUB 3 publications. The useful core is conservative preservation and invalidation of human decisions across a corrected vendor delivery, plus exact-source transactional application. A gallery, an accessibility checker, or spreadsheet export/import by itself is not differentiated; several credible tools and services already offer those capabilities.

The beachhead should be the production editor with access to an EPUB file and a subject-expert reviewer, who needs to preserve evidence of which image descriptions were approved and identify which decisions must be repeated after corrections. Do not target all publishers, all accessible documents, fixed-layout books, or semantic quality certification.

## Facts supporting the workflow

| Primary source | Documented fact | What it supports; what it does not establish |
| --- | --- | --- |
| [DAISY: Image Description, T-269 (30 September 2024)](https://daisy.org/news-events/articles/image-description-t-269-w/) | Cambridge University Press describes author-, vendor-, and in-house creation routes and a human QA responsibility for each. | Human handoffs and expert review are real publishing work. It does not establish demand for this particular software or revision algorithm. |
| [UCL Press: Alt text author guidelines](https://uclpress.co.uk/publish-with-us/the-publishing-process-writing-production/alt-text-author-guidelines/) | Authors provide descriptions in an artwork/permissions spreadsheet alongside captions; image purpose and surrounding text affect the description. | Author/editor handoff and context-aware review fit an institutional press audience. The source does not say its current workflow is failing. |
| [University of Hamburg CSMC: SMC volume-editor instructions, updated 26 February 2025](https://www.csmc.uni-hamburg.de/publications/smc/accessible-instructions.html) | Image descriptions are supplied with typesetting inputs; authors/editors correct first proofs; book editors check a second proof to ensure marked corrections were implemented. | Repeated proof/correction handoffs are documented. These are broader production proofs, not evidence that EPUB approvals are currently lost. |
| [DAISY: Image descriptions knowledge base](https://kb.daisy.org/publishing/docs/html/images-desc.html) | Description needs depend on publication context, and complex images can require an extended description. | Each occurrence needs appropriate context; a resource filename alone is an inadequate decision identity. |
| [DAISY: Using AI to support image/alt-text QA](https://daisy.org/activities/projects/ai-special-interest-group/using-ai-to-support-quality-assurance-of-images-and-alt-text-in-accessible-publications/) | DAISY reports descriptions assigned to the wrong images in one assessed publication and explains that the same image can be informative or decorative in different contexts. | Misassociation is a concrete example, and source/context binding has a sound rationale. One example is not a frequency or cost estimate. |

The specific unmet need remains an inference: a team using independent EPUB vendors and ordinary files could benefit from portable evidence and conservative decision reconciliation. No source reviewed proves how many teams require it or how often stale approvals cause publication failures. No interviews, adoption, measured savings, or production deployment occurred during this research.

## Feature-level alternatives checked

| Alternative | What it already does well | Bounded distinction for the proposed product |
| --- | --- | --- |
| [Ace by DAISY HTML report](https://daisy.github.io/ace/docs/report-html/) | Renders images with alt text, referenced descriptions, figcaption, location, and role; supports manual assessment. | A decision ledger and transactional write-back/reconciliation would add a workflow beyond this report. Do not claim a new image inventory or review gallery. |
| [DAISY Fido](https://daisy.org/activities/software/fido/) and its [image QA workflow](https://daisy.org/activities/projects/ai-special-interest-group/using-ai-to-support-quality-assurance-of-images-and-alt-text-in-accessible-publications/) | Interactive image/context inspection, editable descriptions, decorative decisions, extended descriptions where supported, and batch reports. Current public page describes an experimental app and cloud credentials for most AI features. | A human-only portable review artifact with explicitly documented source-binding behavior is different. The inspected documentation does not establish that Fido lacks an equivalent internal mechanism; make only a documentation-bounded comparison. |
| [Sigil Access-Aide](https://github.com/kevinhendricks/Access-Aide) | Free native EPUB edit plugin presents each image thumbnail and current description for changes. Also changes accessibility-related markup and metadata. | An external reviewer need not install/use Sigil to return decisions; exact-source all-or-nothing patching and a reconciliation ledger are the candidate's focus. |
| [DIAGRAM Poet](https://diagramcenter.org/poet.html) | Historically offered DAISY/EPUB description creation, collaborative participation and enriched downloads; its current hosted site is a training resource. | Offline portable handoff and revision-decision retention are a narrower candidate. Do not claim first collaborative description tool. The historical authoring service is not presented as a currently available hosted service; see the [current site](https://poet.bornaccessible.org/). |
| [HoloPress](https://www.holographpressworks.com/holopress) | Full InDesign/PDF-to-EPUB production service/platform; description drafts can go to editors as a spreadsheet and return to the book. The page invites beta-list participation. | A local tool for an already-produced EPUB avoids requiring the conversion platform. Spreadsheet round-trip itself is not a differentiator. The reviewed page gives no explicit approval-invalidation contract. |
| [DPS/desLibris ATAR](https://support.deslibris.pub/portal/en/kb/articles/the-alt-text-revision-atar-service) | Managed post-production EPUB 3 workflow with an editable local Excel sheet containing thumbnails, filenames, captions, decorative flags, short/long descriptions; the service integrates returned modifications. | A competent alternative when vendor integration is desired. The candidate is vendor-neutral and locally applies decisions with a documented conservative revision policy. Do not describe ATAR as merely an inventory. |
| [Adobe InDesign current alt-text feature](https://helpx.adobe.com/indesign/desktop/add-graphics-and-media/add-edit-graphics/generate-alt-text-for-images.html) | Current documentation says cropping/moving an image marks generated description as outdated. | Revision-sensitive descriptions are not a novel general concept. An EPUB-side cross-party ledger serves a different point in the pipeline. |

Searches included separate general publishing-workflow, EPUB export/import/CSV/spreadsheet, Sigil/InDesign/native-tool, and revision/approval/conflict passes. This is triangulation from current primary documentation, not proof that no other product exists. Strong alternatives should be named prominently in public documentation.

## Product boundary that makes the distinction credible

The complete supported workflow should be: validate a supported EPUB input; export self-contained reviewer material with relevant prose, captions, current descriptions, and occurrence identities; record explicit informative/decorative/needs-work decisions and reviewer notes; validate the returned artifact; apply approved decisions to the exact source in one transaction; and reconcile onto a revised EPUB while retaining only decisions whose recorded context and image inputs are unchanged. Reconciliation should explicitly report retained, changed, added, and removed occurrences. It must never equate an absent decision with approval.

Chapter-byte equality is a conservative boundary that users can understand. It will repeat review after harmless chapter edits or formatting changes; document this as a deliberate tradeoff. Do not use fuzzy matching to silently carry approvals. Do not call a matching record proof of accessibility, semantic correctness, or reader usability.

An important implementation risk: unchanged XHTML and image bytes can still produce changed rendered context if referenced CSS crops, transforms, or hides imagery, or if other referenced descriptions change. Either track those dependencies conservatively, reject unsupported constructions, or narrow the guarantee to unchanged recorded source inputs. The interface must expose scope gaps such as SVG, remote assets, linked images, complex descriptions, and unsupported EPUB forms instead of giving an optimistic complete result.

## Selective application of Crossing the Chasm

[Geoffrey Moore's own book page](https://geoffreyamoore.com/book/crossing-the-chasm/) emphasizes one challenging use case in one industry, a compelling reason to adopt, a complete solution, and clear competitive positioning. The [Chasm Institute's framework](https://www.chasminstitute.com/WhatWeDo/eLearning/tabid/293/Default.aspx) defines the whole product around the customer's desired outcome and treats competition as the logical alternatives the customer could use. These are useful scope and usability principles here; they do not justify invented market-size, pricing, distribution, or customer-reference claims.

- **Beachhead:** small university-press production teams receiving reflowable EPUB 3 corrections from an external producer and sending description questions to authors or expert editors.
- **Compelling reason to use:** preserve an inspectable record of approved image/context pairs while making every uncertain approval visible before applying the next corrected delivery.
- **Market alternative:** an author artwork spreadsheet plus email/versioned EPUB files and manual checking of returned corrections.
- **Product alternative:** a native EPUB image editor such as Sigil Access-Aide or a managed service such as ATAR. They are useful alternatives, not straw competitors.
- **Whole-product requirement:** installable local release; supported-input contract; accessible offline review; explicit status and notes; atomic application; conservative reconciliation; readable audit reports; examples; error recovery; and tests of stale input, dropped images, changed context, malformed archives, unsupported content, and independent installed operation.

### Original two-sentence positioning statement

For small university-press production editors who are dissatisfied with manually matching author approvals and spreadsheets to successive vendor EPUBs, altfreeze is an offline image-description approval tool that keeps human decisions attached to the image and chapter they reviewed. Unlike editing descriptions directly in Sigil Access-Aide, it combines portable reviewer material, an explicit decision ledger, exact-source transactional application, and conservative reconciliation that returns changed or missing inputs for review.

The dissatisfaction in this statement is a target-customer hypothesis, not a reported UCL, Cambridge, or Hamburg opinion.

### Constructed usage scenarios, not observed customers

1. A production editor sends an image-review bundle for a scholarly chapter to its author. While the author works, the vendor corrects another chapter. Reconciliation retains the unchanged chapter's decisions and lists the altered chapter for fresh review.
2. A vendor replaces a map but retains its filename. The tool refuses to carry the old approval because the image bytes differ, keeping that map in the review queue.
3. A revised delivery deletes a figure and introduces a new one. The report records the dropped decision and leaves the new occurrence unapproved; it never silently applies text by row position or filename.

## Implemented v1 boundary

The implemented contract is documented in [contract.md](contract.md). All raster and shared resource changes reopen all decisions; chapter-only changes reopen their own decisions, with a narrow exception for a valid modification timestamp update. Existing roles/naming overrides, long-description attributes and interactive image contexts fail clearly. Application emits a new output-bound baseline for subsequent corrections. This deliberately conservative behavior is narrower than a general-purpose EPUB editor.
