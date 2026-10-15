"""Offline review output and executable client validation regressions.

The small Node DOM harness tests client logic, not browser layout, CSP
enforcement, or whether a browser actually writes a requested download.
"""

import copy
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

from altfreeze.core import Error, _validate_decisions
from altfreeze.review import _SCRIPT, render_review


def snapshot():
    return {
        "title": "Images in scholarly publishing",
        "identifier": "urn:uuid:review-fixture",
        "snapshot_sha256": "c" * 64,
        "source_sha256": "d" * 64,
        "items": [{
            "id": "one", "document": "EPUB/chapter.xhtml", "index": 1,
            "image": "EPUB/image.png", "media_type": "image/png",
            "current_alt": "An existing description", "chapter_text": "Chapter text.",
            "caption": "Figure caption.", "near_text": "Image context.",
            "document_sha256": "a" * 64, "image_sha256": "b" * 64,
        }],
    }


def decisions(**changes):
    return {
        "format": "altfreeze.decisions.v1", "snapshot_sha256": "c" * 64,
        "items": [{"id": "one", "action": "pending", "alt": "", "reviewer": "", "note": "", **changes}],
    }


class Parsed(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_hostile_publication_and_decision_text_is_inert():
    attack = '</script><script>alert(1)</script><img src="https://invalid.test/" onerror="alert(1)">&\u2028'
    source = snapshot()
    source.update(title=attack, identifier=attack)
    source["items"][0].update(id=attack, current_alt=attack, chapter_text=attack, caption=attack, near_text=attack)
    record = decisions(id=attack, alt=attack, reviewer=attack, note=attack)
    page = render_review(source, record, {"EPUB/image.png": b"\x89PNG\r\n\x1a\n"})
    parsed = Parsed()
    parsed.feed(page)
    assert len([tag for tag, _ in parsed.tags if tag == "script"]) == 2
    assert not any(key.startswith("on") for _, attrs in parsed.tags for key in attrs)
    assert not any(attrs.get("src", "").startswith("https:") for _, attrs in parsed.tags)
    assert attack not in page
    data = re.search(r'<script id="review-data"[^>]*>(.*?)</script>', page, re.S).group(1)
    assert json.loads(data)["items"][0]["id"] == attack
    ids = [attrs["id"] for _, attrs in parsed.tags if "id" in attrs]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("media,data,embedded", [
    ("image/png", b"\x89PNG\r\n\x1a\n", True),
    ("image/jpeg", b"\xff\xd8\xff\xe0", True),
    ("image/png", b"<svg onload='alert(1)'/>", False),
    ("image/svg+xml", b"\x89PNG\r\n\x1a\n", False),
])
def test_only_matching_png_or_jpeg_previews_are_embedded(media, data, embedded):
    source = snapshot()
    source["items"][0]["media_type"] = media
    parsed = Parsed()
    parsed.feed(render_review(source, decisions(), {"EPUB/image.png": data}))
    images = [attrs for tag, attrs in parsed.tags if tag == "img"]
    assert bool(images) == embedded
    assert all(image["src"].startswith("data:" + media + ";base64,") for image in images)


def test_offline_csp_nonce_and_no_script_warning():
    page = render_review(snapshot(), decisions(), {})
    parsed = Parsed()
    parsed.feed(page)
    policy = next(attrs["content"] for tag, attrs in parsed.tags if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy")
    nonce = re.search(r"script-src 'nonce-([^']+)'", policy).group(1)
    assert all(attrs.get("nonce") == nonce for tag, attrs in parsed.tags if tag in {"script", "style"})
    assert "default-src 'none'" in policy
    assert "connect-src 'none'" in policy
    assert "frame-src 'none'" in policy
    assert "img-src data:" in policy
    assert "<noscript><p" in page and "Enable JavaScript" in page
    assert "There is no autosave" in page
    assert "command line is the final validation gate" in page
    assert 'maxlength="1000"' not in page and 'maxlength="20000"' not in page


def test_renderer_rejects_wrong_snapshot_and_duplicate_occurrence_ids():
    source = snapshot()
    with pytest.raises(ValueError, match="different snapshot"):
        render_review(source, {**decisions(), "snapshot_sha256": "other"}, {})
    source["items"].append(copy.deepcopy(source["items"][0]))
    with pytest.raises(ValueError, match="duplicate image IDs"):
        render_review(source, decisions(), {})


_HARNESS = r"""
const vm = require('node:vm');
class Element {
  constructor(value='') {
    this.value=value; this.textContent=''; this.hidden=true; this.events={};
    this.attrs={}; this.children={}; this.classList={toggle(){}};
  }
  addEventListener(name,fn){ this.events[name]=fn; }
  querySelector(name){ return this.children[name]; }
  setAttribute(key,value){ this.attrs[key]=value; }
  removeAttribute(key){ delete this.attrs[key]; }
  focus(){}
  scrollIntoView(){}
  click(){ if(this.events.click) this.events.click(); }
  remove(){}
}
const row = new Element();
for(const field of ['action','alt','reviewer','note'])
  row.children['[data-field="'+field+'"]']=new Element(field==='action'?'pending':'');
for(const name of ['error','replacement','reviewer-label','note-label','state'])
  row.children['.'+name]=new Element();
const elements={};
for(const id of ['review-data','status','save-state','error-summary','progress-count','remaining-count','save','load','load-file','nav-1'])
  elements[id]=new Element();
elements['error-summary'].children.p=new Element();
elements['nav-1'].children['.index-state']=new Element();
elements['review-data'].textContent=JSON.stringify({items:[{id:'one',current_alt:'An existing description'}],snapshot_sha256:'c'.repeat(64)});
let downloaded=null;
const windowEvents={};
const context={document:{getElementById:id=>elements[id],querySelectorAll:()=>[row],
  createElement:()=>new Element(),body:{appendChild(){}}},
  window:{addEventListener:(name,fn)=>windowEvents[name]=fn,confirm:()=>true},
  Blob:class {constructor(parts){this.parts=parts;}},
  URL:{createObjectURL:blob=>{downloaded=blob;return 'blob:offline';},revokeObjectURL(){}},
  setTimeout:()=>0};
vm.createContext(context);
"""


def client(record, *, load=False):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is needed to execute client-validation regressions")
    code = _HARNESS + "\nvm.runInContext(" + json.dumps(_SCRIPT) + ",context);\n"
    # Parse actual JSON: an object literal treats __proto__ specially and would
    # accidentally remove that unknown field before the import test sees it.
    code += "const input=JSON.parse(" + json.dumps(json.dumps(record, ensure_ascii=True)) + ");\n"
    if load:
        code += r"""
(async()=>{
  elements['load-file'].files=[{size:100,text:async()=>JSON.stringify(input)}];
  await elements['load-file'].events.change();
  console.log(JSON.stringify({error:!elements['error-summary'].hidden,
    message:elements['error-summary'].children.p.textContent,
    action:row.children['[data-field="action"]'].value}));
})();
"""
    else:
        code += r"""
for(const field of ['action','alt','reviewer','note'])
  row.children['[data-field="'+field+'"]'].value=input[field];
row.events.input();
elements.save.events.click();
console.log(JSON.stringify({downloaded:downloaded!==null,
  ready:elements['progress-count'].textContent.startsWith('1 of'),
  output:downloaded ? JSON.parse(downloaded.parts[0]) : null,
  error:elements['error-summary'].children.p.textContent}));
"""
    # Node emits UTF-8; Windows' locale default can otherwise decode Unicode
    # decision JSON as a legacy code page and corrupt valid boundary fixtures.
    result = subprocess.run([node], input=code, encoding="utf-8", capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("changes", [
    {"action": "keep", "reviewer": "Editor"},
    {"action": "keep", "reviewer": "\U0001f600" * 120},
    {"action": "keep", "reviewer": "\U0001f600" * 121},
    {"action": "keep", "reviewer": "\u0085"},
    {"action": "keep", "reviewer": "\ufeff"},
    {"action": "replace", "reviewer": "Editor", "alt": "\U0001f600" * 2000},
    {"action": "replace", "reviewer": "Editor", "alt": "\U0001f600" * 2001},
    {"action": "replace", "reviewer": "Editor", "alt": "Valid \t\n\r\U00010000 text"},
    {"action": "replace", "reviewer": "Editor", "alt": "\ud800"},
    {"action": "replace", "reviewer": "Editor", "alt": "\udfff"},
    {"action": "replace", "reviewer": "Editor", "alt": "bad\x00text"},
    {"action": "replace", "reviewer": "Editor", "alt": "bad\ufffetext"},
    {"action": "replace", "reviewer": "Editor", "alt": "\u0085"},
    {"action": "decorative", "reviewer": "Editor", "note": "Divider repeated."},
    {"action": "decorative", "reviewer": "Editor", "note": "\u0085"},
    {"action": "pending", "note": "\U0001f600" * 4000},
    {"action": "pending", "note": "\U0001f600" * 4001},
    {"action": "pending", "reviewer": "\x1c"},
    {"action": "needs-work", "note": "Question for author."},
])
def test_client_save_and_ready_match_core_validation(changes):
    packet = decisions(**changes)
    try:
        _validate_decisions(snapshot(), packet, complete=False)
        valid = True
    except Error:
        valid = False
    result = client(packet["items"][0])
    assert result["downloaded"] == valid
    assert result["ready"] == (valid and changes["action"] in {"keep", "replace", "decorative"})
    if valid:
        _validate_decisions(snapshot(), result["output"], complete=False)


@pytest.mark.parametrize("mutation", [
    "root-extra", "root-missing", "row-extra", "row-missing", "foreign-snapshot",
    "nonreplace-alt", "invalid-xml", "long-reviewer", "long-note", "unknown-action",
])
def test_client_import_rejects_schema_text_and_snapshot_failures(mutation):
    packet = decisions(action="keep", reviewer="Editor")
    if mutation == "root-extra":
        packet["__proto__"] = {"unexpected": True}
    elif mutation == "root-missing":
        del packet["format"]
    elif mutation == "row-extra":
        packet["items"][0]["unexpected"] = True
    elif mutation == "row-missing":
        del packet["items"][0]["note"]
    elif mutation == "foreign-snapshot":
        packet["snapshot_sha256"] = "other"
    elif mutation == "nonreplace-alt":
        packet["items"][0]["alt"] = "Unexpected replacement"
    elif mutation == "invalid-xml":
        packet["items"][0]["note"] = "\ud800"
    elif mutation == "long-reviewer":
        packet["items"][0]["reviewer"] = "x" * 121
    elif mutation == "long-note":
        packet["items"][0]["note"] = "x" * 4001
    else:
        packet["items"][0]["action"] = "__proto__"
    result = client(packet, load=True)
    assert result["error"]
    assert result["message"]
    assert result["action"] == "pending", "Import failure must not partially change the form"


def test_client_import_accepts_core_valid_unicode_boundaries():
    packet = decisions(action="replace", alt="\U0001f600" * 2000, reviewer="\U0001f600" * 120, note="\U0001f600" * 4000)
    _validate_decisions(snapshot(), packet, complete=False)
    result = client(packet, load=True)
    assert not result["error"]
    assert result["action"] == "replace"
