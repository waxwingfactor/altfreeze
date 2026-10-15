"""Render a self-contained, offline human review desk.

Book markup is never rendered as HTML. Only verified PNG/JPEG byte signatures
are embedded, and every source string enters the document as escaped text.
"""

from __future__ import annotations

import base64
import html
import json
import secrets


_CSS = r"""
:root { color-scheme: light; --ink:#102f51; --blue:#1e5a96; --desk:#eef3f8;
  --paper:#fff; --muted:#526477; --rule:#b9c8d7; --error:#a53131; --good:#205b45; }
* { box-sizing:border-box; }
html { scroll-padding-top:1.5rem; }
body { margin:0; background:var(--desk); color:var(--ink);
  font:1rem/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
button,input,select,textarea { font:inherit; }
button,a,input,select,textarea,summary { -webkit-tap-highlight-color:transparent; }
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,
textarea:focus-visible,summary:focus-visible { outline:3px solid #c16c13; outline-offset:3px; }
a { color:var(--blue); text-underline-offset:.18em; }
button { cursor:pointer; }
button,.button { min-height:2.8rem; padding:.6rem 1rem; border:1px solid var(--blue);
  border-radius:4px; background:var(--paper); color:var(--blue); font-weight:650; }
button:hover { background:#e5eff9; }
button.primary { background:var(--blue); color:#fff; }
button.primary:hover { background:#164876; }
button:disabled { opacity:.55; cursor:default; }
.skip { position:absolute; left:1rem; top:-8rem; z-index:10; padding:1rem; background:#fff; }
.skip:focus { top:.5rem; }
.masthead { background:var(--ink); color:#fff; padding:2rem max(1.2rem,calc((100vw - 1280px)/2)); }
.brand { margin:0 0 .8rem; font-size:1.05rem; font-weight:700; }
h1,h2,h3 { font-family:Georgia,"Times New Roman",serif; font-weight:500; line-height:1.18; }
h1 { margin:0; max-width:34ch; font-size:clamp(1.85rem,4vw,3rem); overflow-wrap:anywhere; }
.masthead p { margin:.7rem 0 0; max-width:74ch; }
.edition { color:#d3e2f1; font-size:.92rem; overflow-wrap:anywhere; }
.toolbar { max-width:1280px; margin:0 auto; padding:1.4rem 1.2rem; }
.toolbar-row { display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap; }
.toolbar h2 { margin:0; font-size:1.4rem; }
.actions { display:flex; gap:.65rem; flex-wrap:wrap; }
.save-guidance { margin:.65rem 0 0; color:var(--muted); max-width:80ch; font-size:.92rem; }
.status { min-height:1.5em; margin:.65rem 0 0; font-weight:600; }
.save-state { color:var(--muted); font-weight:400; }
.error-summary { margin-top:1rem; padding:1rem; border:2px solid var(--error); background:#fff6f6; color:#762020; }
.error-summary p { margin:0; }
.desk { max-width:1280px; margin:0 auto; padding:0 1.2rem 3rem; display:grid;
  grid-template-columns:190px minmax(0,1fr); align-items:start; gap:1.4rem; }
.index { position:sticky; top:1rem; max-height:calc(100vh - 2rem); overflow:auto; padding:.4rem .5rem .5rem 0; }
.index h2 { font-size:1.35rem; margin:0 0 .65rem; }
.index ol { list-style:none; padding:0; margin:0; }
.index li { border-bottom:1px solid var(--rule); }
.index a { display:block; padding:.6rem .3rem; text-decoration:none; border-left:3px solid transparent; }
.index a:hover { background:#e2ebf4; border-left-color:var(--blue); }
.index-number { font-weight:650; display:block; }
.index-state { font-size:.82rem; color:var(--muted); }
.index .approved .index-state { color:var(--good); }
main { min-width:0; }
.proof { background:var(--paper); border:1px solid #c5d1dd; margin:0 0 1.5rem;
  box-shadow:0 3px 0 #dce5ee; border-radius:6px; overflow:hidden; scroll-margin-top:1rem; }
.proof-head { padding:1.2rem 1.4rem; display:flex; align-items:baseline; gap:1rem;
  flex-wrap:wrap; border-bottom:1px solid var(--rule); }
.proof-head h2 { margin:0; font-size:1.75rem; }
.location { color:var(--muted); font-size:.88rem; overflow-wrap:anywhere; flex:1; }
.state { font-size:.85rem; font-weight:650; border:1px solid #99aec3; padding:.2rem .6rem;
  border-radius:3px; white-space:nowrap; }
.state.approved { color:var(--good); border-color:#7aab93; background:#f0f8f3; }
.proof-body { display:grid; grid-template-columns:minmax(0,1.1fr) minmax(260px,.9fr); }
.evidence { padding:1.4rem; min-width:0; }
.image-mat { margin:0 0 1.2rem; padding:.8rem; border:1px solid #d5dfe9; background:#f4f7fa;
  min-height:9rem; display:flex; align-items:center; justify-content:center; }
.image-mat img { max-width:100%; max-height:29rem; width:auto; height:auto; object-fit:contain; }
.image-unavailable { color:var(--muted); text-align:center; }
.evidence h3 { margin:1.1rem 0 .4rem; font:650 .93rem/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.source-text { margin:0; max-width:74ch; white-space:pre-wrap; overflow-wrap:anywhere; }
.book-text { font:1rem/1.65 Georgia,"Times New Roman",serif; color:#253d56; }
.empty { color:var(--muted); font-style:italic; }
details { margin-top:1rem; }
summary { cursor:pointer; color:var(--blue); font-weight:600; padding:.35rem 0; }
.chapter { margin-top:.5rem; padding:1rem; background:#f4f7fa; max-height:24rem; overflow:auto; }
.record { font-size:.82rem; color:var(--muted); }
.record dl { margin:.4rem 0; }
.record dt { font-weight:650; margin-top:.45rem; }
.record dd { margin:0; overflow-wrap:anywhere; }
.decision { padding:1.4rem; border-left:1px solid var(--rule); background:#f9fbfd; }
.decision h3 { font-size:1.35rem; margin:0 0 1rem; }
.field { margin:0 0 1rem; }
label { display:block; font-weight:650; margin-bottom:.35rem; }
input,select,textarea { width:100%; min-width:0; border:1px solid #7c91a7; border-radius:3px;
  padding:.6rem .65rem; background:#fff; color:var(--ink); }
select { min-height:2.8rem; }
textarea { resize:vertical; min-height:6.5rem; }
.hint { display:block; color:var(--muted); font-size:.86rem; margin:.35rem 0 0; }
.error { color:var(--error); font-size:.88rem; margin:.45rem 0 0; font-weight:600; }
[aria-invalid="true"] { border:2px solid var(--error); }
.proof-foot { padding:.7rem 1.4rem; border-top:1px solid #d5dfe9; display:flex;
  justify-content:space-between; gap:1rem; font-size:.9rem; }
.empty-review { padding:2rem; background:#fff; border:1px solid var(--rule); }
footer { max-width:1280px; margin:0 auto; padding:0 1.2rem 2rem; color:var(--muted); font-size:.88rem; }
[hidden] { display:none !important; }
@media (max-width:1000px) {
  .desk { grid-template-columns:150px minmax(0,1fr); gap:1rem; }
  .proof-body { grid-template-columns:1fr; }
  .decision { border-left:0; border-top:1px solid var(--rule); }
}
@media (max-width:640px) {
  .masthead { padding:1.5rem 1rem; }
  .toolbar { padding:1.1rem 1rem; }
  .toolbar-row { align-items:flex-start; }
  .actions { width:100%; }
  .actions button { flex:1; padding:.65rem .6rem; }
  .desk { display:block; padding:0 1rem 2rem; }
  .index { position:static; max-height:12rem; margin:0 0 1rem; padding:0; }
  .index ol { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 .75rem; }
  .proof-head,.evidence,.decision { padding:1rem; }
  .proof-head { gap:.5rem; }
  .proof-head h2 { font-size:1.5rem; }
  .location { flex-basis:100%; order:2; }
  .proof-foot { padding:.7rem 1rem; }
  footer { padding:0 1rem 1.5rem; }
}
@media print {
  body { background:#fff; }
  .masthead { background:#fff; color:var(--ink); }
  .edition { color:var(--muted); }
  .actions,.index,.proof-foot { display:none; }
  .desk { display:block; }
  .proof { box-shadow:none; break-inside:avoid; }
  .proof-body { grid-template-columns:1fr 1fr; }
}
"""


_SCRIPT = r"""
(() => {
  'use strict';
  const payload = JSON.parse(document.getElementById('review-data').textContent);
  const items = payload.items;
  const rows = Array.from(document.querySelectorAll('.proof'));
  const allowed = new Set(['pending','keep','replace','decorative','needs-work']);
  const approved = new Set(['keep','replace','decorative']);
  const labels = {pending:'Pending',keep:'Keep existing',replace:'Replace description',
    decorative:'Decorative', 'needs-work':'Needs work'};
  const limits = {alt:2000,reviewer:120,note:4000};
  const fieldNames = {alt:'Replacement description',reviewer:'Reviewer name',note:'Review note'};
  // Match Python str.strip(), including U+0085 and excluding U+FEFF.
  const blank = /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*$/u;
  const status = document.getElementById('status');
  const saveState = document.getElementById('save-state');
  const errorSummary = document.getElementById('error-summary');
  const count = document.getElementById('progress-count');
  let dirty = false;

  function announce(message) { status.textContent = message; }
  function setDirty(value) {
    dirty = value;
    saveState.textContent = value ? 'Unsaved changes' : 'No unsaved changes';
  }
  function controls(row) {
    return { action:row.querySelector('[data-field="action"]'),
      alt:row.querySelector('[data-field="alt"]'),
      reviewer:row.querySelector('[data-field="reviewer"]'),
      note:row.querySelector('[data-field="note"]') };
  }
  function hasExactKeys(value,expected) {
    return value !== null && typeof value === 'object' && !Array.isArray(value) &&
      Object.keys(value).length === expected.length &&
      expected.every(key => Object.prototype.hasOwnProperty.call(value,key));
  }
  function validXmlText(value) {
    return Array.from(value).every(character => {
      const point = character.codePointAt(0);
      return point === 9 || point === 10 || point === 13 ||
        (point >= 0x20 && point <= 0xd7ff) ||
        (point >= 0xe000 && point <= 0xfffd) ||
        (point >= 0x10000 && point <= 0x10ffff);
    });
  }
  function collect() {
    return {format:'altfreeze.decisions.v1', snapshot_sha256:payload.snapshot_sha256,
      items:rows.map((row,index) => {
        const c = controls(row);
        return {id:items[index].id, action:c.action.value,
          alt:c.action.value === 'replace' ? c.alt.value : '',
          reviewer:c.reviewer.value, note:c.note.value};
      })};
  }
  function problem(item,record) {
    if (!allowed.has(record.action)) return ['action','Choose a supported decision.'];
    for (const [field,limit] of Object.entries(limits)) {
      if (typeof record[field] !== 'string')
        return [field,fieldNames[field] + ' must be text.'];
      if (Array.from(record[field]).length > limit)
        return [field,fieldNames[field] + ' must contain no more than ' + limit.toLocaleString('en-US') + ' characters.'];
      if (!validXmlText(record[field]))
        return [field,fieldNames[field] + ' contains characters that XML cannot store. Remove control characters or incomplete Unicode characters.'];
    }
    if (record.action !== 'replace' && record.alt !== '')
      return ['alt','Only a replacement decision may contain replacement text.'];
    if (record.action === 'keep' && blank.test(item.current_alt || ''))
      return ['action','There is no nonempty description to keep. Choose another decision.'];
    if (record.action === 'replace' && blank.test(record.alt))
      return ['alt','Enter the replacement description, or choose Pending to save a draft.'];
    if (approved.has(record.action) && blank.test(record.reviewer))
      return ['reviewer','Add a reviewer name for this decision, or choose Pending to save a draft.'];
    if (record.action === 'decorative' && blank.test(record.note))
      return ['note','Explain why this occurrence is decorative, or choose Pending to save a draft.'];
    return null;
  }
  function clearErrors() {
    errorSummary.hidden = true;
    rows.forEach(row => {
      row.querySelector('.error').hidden = true;
      Object.values(controls(row)).forEach(el => el.removeAttribute('aria-invalid'));
    });
  }
  function showError(message,element) {
    errorSummary.querySelector('p').textContent = message;
    errorSummary.hidden = false;
    if (element) { element.focus(); element.scrollIntoView({block:'center'}); }
    else errorSummary.focus();
  }
  function refresh() {
    const records = collect().items;
    let completed = 0;
    let needsWork = 0;
    rows.forEach((row,index) => {
      const c = controls(row);
      const record = records[index];
      const ready = approved.has(record.action) && !problem(items[index],record);
      if (ready) completed++;
      if (record.action === 'needs-work') needsWork++;
      row.querySelector('.replacement').hidden = record.action !== 'replace';
      row.querySelector('.reviewer-label').textContent = approved.has(record.action)
        ? 'Reviewer name (required)' : 'Reviewer name';
      row.querySelector('.note-label').textContent = record.action === 'decorative'
        ? 'Reason this is decorative (required)' : 'Review note';
      const state = row.querySelector('.state');
      state.textContent = approved.has(record.action) && !ready
        ? labels[record.action] + ' — incomplete' : labels[record.action];
      state.classList.toggle('approved',ready);
      const nav = document.getElementById('nav-' + (index + 1));
      nav.classList.toggle('approved',ready);
      nav.querySelector('.index-state').textContent = state.textContent;
    });
    count.textContent = completed + ' of ' + items.length + ' ready to apply';
    document.getElementById('remaining-count').textContent =
      (items.length - completed) + ' still require a complete decision' +
      (needsWork ? '; ' + needsWork + ' marked Needs work.' : '.');
  }
  rows.forEach(row => {
    row.addEventListener('input',() => { clearErrors(); setDirty(true); refresh(); });
    row.addEventListener('change',() => { clearErrors(); setDirty(true); refresh(); });
  });

  document.getElementById('save').addEventListener('click',() => {
    clearErrors();
    const data = collect();
    for (let index = 0; index < items.length; index++) {
      const issue = problem(items[index],data.items[index]);
      if (issue) {
        const row = rows[index];
        const field = controls(row)[issue[0]];
        const error = row.querySelector('.error');
        error.textContent = issue[1];
        error.hidden = false;
        field.setAttribute('aria-invalid','true');
        showError('Image ' + (index + 1) + ': ' + issue[1],field);
        return;
      }
    }
    try {
      const file = new Blob([JSON.stringify(data,null,2) + '\n'], {type:'application/json'});
      const url = URL.createObjectURL(file);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'altfreeze-decisions.json';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(url),30000);
      setDirty(false);
      announce('Decision file download requested. Check your downloads and keep the JSON file for production.');
    } catch (_) {
      showError('The browser could not create the download. Keep this page open and try saving again.');
    }
  });

  const fileInput = document.getElementById('load-file');
  document.getElementById('load').addEventListener('click',() => fileInput.click());
  fileInput.addEventListener('change',async () => {
    const file = fileInput.files[0];
    fileInput.value = '';
    if (!file) return;
    clearErrors();
    if (file.size > 8 * 1024 * 1024) {
      showError('This decision file exceeds the 8 MiB review-file limit. Use a smaller decision file.');
      return;
    }
    try {
      const imported = JSON.parse(await file.text());
      if (!hasExactKeys(imported,['format','snapshot_sha256','items']) ||
          imported.format !== 'altfreeze.decisions.v1')
        throw new Error('Choose an altfreeze.decisions.v1 JSON file with exactly format, snapshot_sha256, and items fields.');
      if (imported.snapshot_sha256 !== payload.snapshot_sha256)
        throw new Error('This decision file belongs to a different snapshot. Open its matching review file or reconcile it first.');
      if (!Array.isArray(imported.items) || imported.items.length !== items.length)
        throw new Error('The decision file must contain exactly one record for every image in this snapshot.');
      const byId = new Map();
      const expected = new Set(items.map(item => item.id));
      for (const record of imported.items) {
        if (!hasExactKeys(record,['id','action','alt','reviewer','note']))
          throw new Error('Each decision must contain exactly id, action, alt, reviewer, and note fields.');
        if (typeof record.id !== 'string' || !expected.has(record.id) || byId.has(record.id))
          throw new Error('The decision file contains an unknown or duplicate image record.');
        if (!allowed.has(record.action) || ['alt','reviewer','note'].some(key => typeof record[key] !== 'string'))
          throw new Error('Each record needs a supported action and text values for description, reviewer, and note.');
        const issue = problem(items.find(item => item.id === record.id),record);
        if (issue) throw new Error(issue[1]);
        byId.set(record.id,record);
      }
      if (dirty && !window.confirm('Loading will replace the unsaved decisions on this page. Continue?')) return;
      rows.forEach((row,index) => {
        const record = byId.get(items[index].id);
        const c = controls(row);
        c.action.value = record.action;
        c.alt.value = record.alt;
        c.reviewer.value = record.reviewer;
        c.note.value = record.note;
      });
      setDirty(false);
      refresh();
      announce('Decision file loaded. Review the entries, then save a new file after making changes.');
    } catch (error) {
      showError(error instanceof SyntaxError ? 'The file is not valid JSON. Choose a saved altfreeze decision file.' : error.message);
    }
  });
  window.addEventListener('beforeunload',event => {
    if (dirty) { event.preventDefault(); event.returnValue = ''; }
  });
  refresh();
})();
"""


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _safe_json(value: object) -> str:
    """JSON for a script data block, including hostile closing-tag strings."""
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _image_uri(media_type: str, data: bytes | None) -> str | None:
    if not isinstance(data, bytes):
        return None
    if media_type == "image/png" and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    if media_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"):
        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    return None


def _source_section(heading: str, value: object, *, book: bool = False) -> str:
    text = str(value or "")
    classes = "source-text book-text" if book else "source-text"
    content = _escape(text) if text else '<span class="empty">Not present in the source.</span>'
    return f'<h3>{_escape(heading)}</h3><p class="{classes}">{content}</p>'


def render_review(snapshot: dict, decisions: dict, images: dict[str, bytes]) -> str:
    """Return one offline HTML review document for a validated snapshot.

    The core owns archive validation and snapshot integrity. This renderer adds
    output escaping and a strict offline CSP independently of that validation.
    """
    nonce = secrets.token_urlsafe(24)
    items = snapshot["items"]
    decision_map = {record["id"]: record for record in decisions["items"]}
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise ValueError("Review snapshot contains duplicate image IDs")
    if set(decision_map) != set(ids) or len(decisions["items"]) != len(ids):
        raise ValueError("Review decisions must match all snapshot image IDs")
    if decisions.get("format") != "altfreeze.decisions.v1":
        raise ValueError("Unsupported review decisions format")
    if decisions.get("snapshot_sha256") != snapshot["snapshot_sha256"]:
        raise ValueError("Review decisions belong to a different snapshot")
    policy = (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}'; style-src 'nonce-{nonce}'; "
        "img-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; "
        "base-uri 'none'; form-action 'none'"
    )
    title = snapshot.get("title") or "Untitled publication"
    fragments = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f'<meta http-equiv="Content-Security-Policy" content="{_escape(policy)}">',
        f'<title>{_escape(title)} — altfreeze review</title>',
        f'<style nonce="{nonce}">{_CSS}</style></head><body>',
        '<a class="skip" href="#proofs">Skip to image review</a>',
        '<header class="masthead"><p class="brand">altfreeze / Image-description proof desk</p>',
        f'<h1>{_escape(title)}</h1>',
        f'<p class="edition">Publication identifier: {_escape(snapshot.get("identifier") or "Not supplied")}</p>',
        '<p>Review each image in context. Record the description to keep, replace it, or explain why this occurrence is decorative.</p></header>',
        '<section class="toolbar" aria-label="Decision files and review progress">',
        '<div class="toolbar-row"><div><h2 id="progress-count">Review progress</h2>',
        '<span id="remaining-count" class="hint"></span></div>',
        '<div class="actions"><button id="load" type="button">Load decisions JSON</button>',
        '<button id="save" class="primary" type="button">Save decisions JSON</button></div></div>',
        '<input id="load-file" type="file" accept=".json,application/json" hidden>',
        '<p class="save-guidance">There is no autosave. Save partial work with Pending or Needs work selected; production requires a complete decision for every image. Keep the downloaded JSON file with this review file. The production editor must run altfreeze check on the saved file before applying it; the command line is the final validation gate.</p>',
        '<p class="status"><span id="save-state" class="save-state">No unsaved changes</span></p>',
        '<p id="status" role="status" aria-live="polite" class="status">This review works offline. Loading a decision file replaces the entries on this page.</p>',
        '<div id="error-summary" class="error-summary" role="alert" tabindex="-1" hidden><p></p></div>',
        '<noscript><p class="error-summary">Enable JavaScript in this browser to record decisions and save a decision file. Book text remains readable below.</p></noscript>',
        '</section><div class="desk"><nav class="index" aria-label="Image review index"><h2>Proof index</h2><ol>',
    ]
    for position, _item in enumerate(items, 1):
        fragments.append(
            f'<li id="nav-{position}"><a href="#proof-{position}">'
            f'<span class="index-number">Image {position}</span>'
            '<span class="index-state">Pending</span></a></li>'
        )
    fragments.append('</ol></nav><main id="proofs" tabindex="-1" aria-label="Image proofs">')
    if not items:
        fragments.append('<div class="empty-review"><h2>No supported image occurrences</h2><p>This snapshot has no image decisions to review. Check the extraction report for the supported scope.</p></div>')
    for position, item in enumerate(items, 1):
        record = decision_map[item["id"]]
        current_alt = item.get("current_alt")
        fragments.extend([
            f'<article class="proof" id="proof-{position}" aria-labelledby="title-{position}">',
            f'<header class="proof-head"><h2 id="title-{position}">Image {position}</h2>',
            f'<span class="location">{_escape(item["document"])} / occurrence {_escape(item["index"])}</span>',
            '<span class="state">Pending</span></header><div class="proof-body"><section class="evidence" aria-label="Source image and context">',
        ])
        uri = _image_uri(item.get("media_type", ""), images.get(item["image"]))
        if uri:
            fragments.append(
                f'<figure class="image-mat"><img src="{uri}" '
                f'alt="Source image {position} for visual description review"></figure>'
            )
        else:
            fragments.append('<div class="image-mat"><p class="image-unavailable">Image preview unavailable. Only embedded PNG and JPEG previews are supported; review the source before approving.</p></div>')
        if current_alt is None:
            alt_display = '<span class="empty">The source has no alt attribute.</span>'
        elif current_alt == "":
            alt_display = '<span class="empty">The source alt attribute is empty. This alone does not establish that the image is decorative.</span>'
        else:
            alt_display = _escape(current_alt)
        fragments.extend([
            f'<h3>Current description</h3><p class="source-text">{alt_display}</p>',
            _source_section("Caption", item.get("caption"), book=True),
            _source_section("Nearby text", item.get("near_text"), book=True),
            '<details><summary>Read whole chapter text</summary>',
            '<p class="hint">Plain source text, in document order. This is not a rendered reading-system preview.</p>',
            f'<div class="chapter source-text book-text" tabindex="0" aria-label="Whole chapter text">{_escape(item.get("chapter_text") or "No chapter text was extracted.")}</div></details>',
            '<details class="record"><summary>Source record</summary><dl>',
            f'<dt>Image path</dt><dd>{_escape(item["image"])}</dd>',
            f'<dt>Occurrence ID</dt><dd>{_escape(item["id"])}</dd>',
            f'<dt>Chapter SHA-256</dt><dd>{_escape(item.get("document_sha256", ""))}</dd>',
            f'<dt>Image SHA-256</dt><dd>{_escape(item.get("image_sha256", ""))}</dd>',
            '</dl></details></section>',
            f'<section class="decision" aria-labelledby="decision-{position}"><h3 id="decision-{position}">Your decision</h3>',
            f'<div class="field"><label for="action-{position}">Decision</label>',
            f'<select id="action-{position}" data-field="action" aria-describedby="action-hint-{position} error-{position}">',
        ])
        for value, label in [
            ("pending", "Pending — review later"),
            ("keep", "Keep existing description"),
            ("replace", "Replace description"),
            ("decorative", "Decorative — empty description"),
            ("needs-work", "Needs work — send back for review"),
        ]:
            selected = " selected" if record.get("action") == value else ""
            disabled = " disabled" if value == "keep" and not (current_alt or "").strip() else ""
            fragments.append(f'<option value="{value}"{selected}{disabled}>{label}</option>')
        fragments.extend([
            f'</select><p class="hint" id="action-hint-{position}">Keep, Replace, and Decorative are approval decisions. Use Needs work when the image needs further editorial attention.</p></div>',
            f'<div class="field replacement"><label for="alt-{position}">Replacement description (required)</label>',
            f'<textarea id="alt-{position}" data-field="alt" rows="5" aria-describedby="alt-hint-{position} error-{position}">{_escape(record.get("alt", ""))}</textarea>',
            f'<p class="hint" id="alt-hint-{position}">Describe this image’s purpose in this chapter. Maximum 2,000 characters. Complex images may need a separately edited extended description.</p></div>',
            f'<div class="field"><label class="reviewer-label" for="reviewer-{position}">Reviewer name</label>',
            f'<input id="reviewer-{position}" data-field="reviewer" type="text" autocomplete="off" aria-describedby="reviewer-hint-{position} error-{position}" value="{_escape(record.get("reviewer", ""))}">',
            f'<p class="hint" id="reviewer-hint-{position}">Maximum 120 Unicode characters.</p></div>',
            f'<div class="field"><label class="note-label" for="note-{position}">Review note</label>',
            f'<textarea id="note-{position}" data-field="note" rows="3" aria-describedby="note-hint-{position} error-{position}">{_escape(record.get("note", ""))}</textarea>',
            f'<p class="hint" id="note-hint-{position}">Explain a decorative decision or leave a question for the production editor. Maximum 4,000 Unicode characters. A note does not become book content.</p></div>',
            f'<p class="error" id="error-{position}" hidden></p>',
            '</section></div><div class="proof-foot">',
        ])
        fragments.append(f'<a href="#proof-{position - 1}">Previous image</a>' if position > 1 else '<span>First image</span>')
        fragments.append(f'<a href="#proof-{position + 1}">Next image</a>' if position < len(items) else '<a href="#save">Back to save controls</a>')
        fragments.append('</div></article>')
    fragments.extend([
        '</main></div><footer><p>Human review records editorial decisions; it does not certify accessibility. Apply the saved decision file with altfreeze against its matching source snapshot.</p>',
        f'<details class="record"><summary>Review identity</summary><dl><dt>Snapshot SHA-256</dt><dd>{_escape(snapshot["snapshot_sha256"])}</dd>',
        f'<dt>Source EPUB SHA-256</dt><dd>{_escape(snapshot["source_sha256"])}</dd></dl></details></footer>',
        f'<script id="review-data" type="application/json" nonce="{nonce}">',
        _safe_json({"snapshot_sha256": snapshot["snapshot_sha256"], "items": [{"id": item["id"], "current_alt": item.get("current_alt")} for item in items]}),
        '</script>',
        f'<script nonce="{nonce}">{_SCRIPT}</script></body></html>',
    ])
    return "".join(fragments)
