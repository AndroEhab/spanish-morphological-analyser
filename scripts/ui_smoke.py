"""Real-browser UI smoke test for the Spanish Morphological Analyser.

Phase 1 dashboard: starts uvicorn on port 8011, drives the page with
Playwright (headless chromium), exercises the full user flow end to end —
combobox + free-text resolution, the six dashboard regions, the radial
family hub, the origin chain, empty states, the other-forms strip,
recent/favourites persistence, deep links and the Layer-3 hand-offs — and
captures screenshots to ``scripts/screenshots/``.

Run:  .venv\\Scripts\\python scripts\\ui_smoke.py
"""

import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "scripts" / "screenshots"


def _free_port() -> int:
    """Fresh ephemeral port so a lingering server can never collide."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()
BASE = f"http://127.0.0.1:{PORT}"

# documented empty states — the §C strings translated into the product's
# UI language (the specs' example strings are English because the docs are;
# the product is Spanish, design_UI.png has no English chrome)
EMPTY_ORIGIN = "No se dispone de un origen histórico fiable."
EMPTY_COGNATES = "No se han encontrado relaciones útiles con raíces en inglés."
EMPTY_FAMILY = "Todavía no hay una familia de palabras fiable para esta entrada."
EMPTY_MNEMONIC = "Todavía no hay una mnemotecnia fiable para esta entrada."

REGIONS = [
    "region-morphology",
    "region-family",
    "region-origin",
    "region-cognates",
    "region-mnemonics",
    "region-forms",
]


def start_server(backend: str = "fixture") -> subprocess.Popen:
    env = {**os.environ, "MORPH_BACKEND": backend}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(PORT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=2) as resp:
                if resp.status == 200:
                    return proc
        except Exception:
            time.sleep(0.3)
    proc.terminate()
    raise RuntimeError("server did not become ready on port 8011")


def shot(page, name, full=False):
    path = SHOTS / name
    page.screenshot(path=str(path), full_page=full)
    print(f"  screenshot: {name}" + (" (full page)" if full else ""))


def type_query(page, text):
    page.fill("#search-input", "")
    page.fill("#search-input", text)


def select_row(page, down_presses, enter=True):
    for _ in range(down_presses):
        page.keyboard.press("ArrowDown")
    if enter:
        page.keyboard.press("Enter")
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=8000)


def open_word(page, word):
    """Resolve a word through the free-text path (Analizar) and wait."""
    type_query(page, word)
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Escape")  # dropdown closed -> free-text resolution
    page.locator("#analyze-btn").click()
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)


def frame_scroll(page, selector):
    page.evaluate(
        """(sel) => {
            document.documentElement.style.scrollBehavior = 'auto';
            const el = document.querySelector(sel);
            if (el) el.scrollIntoView({block: 'start'});
        }""",
        selector,
    )
    page.wait_for_timeout(250)


def run_flows(browser):
    page = browser.new_page(viewport={"width": 1535, "height": 1024})
    page.goto(BASE + "/", wait_until="networkidle")
    assert not page.locator("#dashboard .entry-form").count(), "analysis present on first load"

    # ---- 1. combobox contract preserved: 'mient' renders ambiguous rows ----
    type_query(page, "mient")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    expect(page.locator(".option")).to_have_count(21)
    quals = sorted(
        page.locator(".option", has_text=re.compile(r"^mienta\(")).locator(".row-qualifier").all_text_contents()
    )
    assert quals == ["(mentar)", "(mentir)"], quals
    lb = page.evaluate(
        """() => {
            const lb = document.getElementById('search-listbox');
            return {scrolls: lb.scrollHeight > lb.clientHeight, cap: Math.round(parseFloat(getComputedStyle(lb).maxHeight))};
        }"""
    )
    assert lb["scrolls"] and lb["cap"] <= 400, lb
    print("PASS 1: combobox dropdown renders tiered results with qualifiers; height-capped and scrolls")
    shot(page, "01-dropdown.png")

    # ---- 2. Escape closes; Enter with an EMPTY input is a no-op ----
    page.keyboard.press("Escape")
    assert page.locator("#search-listbox").is_hidden(), "listbox still visible after Escape"
    page.fill("#search-input", "")  # empty input -> free-text submit is a no-op
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    assert not page.locator("#dashboard .entry-form").count(), "Enter with empty input must not analyze"
    print("PASS 2: Escape closes dropdown; Enter with empty input does nothing")

    # ---- 3. highlighted-row selection still works (combobox path) ----
    type_query(page, "mient")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    select_row(page, 2)
    assert page.locator("#dashboard .entry-form").inner_text() == "miento", \
        page.locator("#dashboard .entry-form").inner_text()
    print("PASS 3: ArrowDown x2 + Enter opens miento analysis on the dashboard")

    # ---- 4. 'Analizar' button resolves free text to the top-ranked match ----
    open_word(page, "hacer")
    assert page.locator("#dashboard .entry-form").inner_text() == "hacer"
    print("PASS 4: Analizar resolves 'hacer' to the top-ranked match (hacer)")

    # ---- 5. Enter with the dropdown closed also resolves the typed string ----
    type_query(page, "satisfacer")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Escape")
    page.keyboard.press("Enter")
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    assert page.locator("#dashboard .entry-form").inner_text() == "satisfacer"
    print("PASS 5: Enter (dropdown closed) resolves the typed string")

    # ---- 6. dashboard renders all six regions ----
    for rid in REGIONS:
        assert page.locator(f"#{rid}").count() == 1, f"missing region {rid}"
        assert page.locator(f"#{rid}").is_visible(), f"region {rid} not visible"
    words = page.locator("#region-forms .form-item .form-word").all_text_contents()
    assert words == ["satisfago", "satisfaces", "satisface", "satisfacemos", "satisfacéis", "satisfacen"], words
    feats = page.locator("#region-forms .form-item .form-feat").all_text_contents()
    assert feats[0] == "pres. ind. 1ª sing.", feats
    assert "verbo ·" in page.locator(".morph-summary").inner_text()
    print(f"PASS 6: all six regions render; other-forms strip = {words} with Spanish feature captions")

    # ---- 7. radial hub: centre label, node count, searched-form highlight ----
    hub = page.locator(".radial-hub text").text_content()
    assert hub == "hacer", hub
    nodes = page.locator(".radial-node")
    assert 1 <= nodes.count() <= 10, nodes.count()
    assert page.locator(".radial-node.is-selected text.word").text_content() == "satisfacer"
    assert page.locator("#region-family .count-badge").inner_text() == "26"
    # text alternative present on the svg
    label = page.locator(".radial-svg").get_attribute("aria-label")
    assert "Familia de palabras de hacer" in label and "satisfacer" in label, label
    # no stale loading spinner once results render; no duplicated satellite
    assert page.locator("#loading").is_hidden(), "loading spinner must hide once results render"
    node_lemmas = page.locator(".radial-node text.word").all_text_contents()
    assert len(node_lemmas) == len(set(node_lemmas)), f"radial must not repeat a lemma: {node_lemmas}"
    print(f"PASS 7: radial hub '{hub}' with {nodes.count()} satellites; satisfacer highlighted; badge 26; aria-label present")

    # ---- 8. origin chain oldest -> newest (real cited forms) ----
    assert page.locator("#region-origin .origin-lead").inner_text() == "Del latín"
    assert page.locator("#region-origin .origin-source-word").inner_text() == "facere"
    chain = [
        (w, l)
        for w, l in zip(
            page.locator("#region-origin .origin-stage .word").all_text_contents(),
            page.locator("#region-origin .origin-stage .lang").all_text_contents(),
        )
    ]
    assert chain == [
        ("facere", "latín"),
        ("satisfacere", "latín"),
        ("satisfacer", "español"),
    ], chain
    assert page.locator("#region-origin .origin-arrow").count() == 2
    print("PASS 8: origin chain renders facere -> satisfacere -> satisfacer (oldest first) with 2 arrows")

    # ---- 9. empty states: cognates + mnemonics (Phase 1 -> null) ----
    assert page.locator("#region-cognates .empty-state").inner_text() == EMPTY_COGNATES
    assert page.locator("#region-mnemonics .empty-state").inner_text() == EMPTY_MNEMONIC
    print("PASS 9: cognates and mnemonics render their documented empty states")

    # ---- 10. Layer 3 hand-off: 'Ver toda la familia' -> map view, back works ----
    page.locator("#region-family .card-link", has_text="Ver toda la familia").click()
    page.wait_for_selector("#layer3 .map-wrap", state="visible", timeout=8000)
    assert page.locator("#layer3 .map-node").count() >= 20
    assert page.locator("#layer3-title").inner_text() == "Familia completa de satisfacer"
    page.locator("#layer3-back").click()
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=5000)
    print("PASS 10: 'Ver toda la familia' opens the Layer-3 map; back returns to the dashboard")

    # ---- 11. Layer 3 hand-off: 'Ver conjugación completa' -> list view ----
    page.locator("#region-forms .card-link", has_text="Ver conjugación completa").click()
    page.wait_for_selector("#layer3 .entry-card", state="visible", timeout=8000)
    assert page.locator("#layer3 .pos-section").count() >= 1
    assert page.locator("#layer3-title").inner_text() == "Conjugación y formas de satisfacer"
    page.locator("#layer3-back").click()
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=5000)
    print("PASS 11: 'Ver conjugación completa' opens the Layer-3 POS-grouped list; back works")

    # ---- 12. recent results: popover, persistence across reload ----
    page.locator("#recent-btn").click()
    page.wait_for_selector("#recent-popover", state="visible", timeout=3000)
    recents = page.locator(".popover-word-btn").all_text_contents()
    assert "satisfacer" in recents and "hacer" in recents, recents
    page.locator("#recent-popover").press("Escape") if False else page.keyboard.press("Escape")
    page.locator("#recent-btn").click()  # toggle closed via outside click not needed; re-open
    page.keyboard.press("Escape")
    # persistence: reload and re-open
    page.reload()
    page.locator("#recent-btn").click()
    page.wait_for_selector("#recent-popover", state="visible", timeout=3000)
    assert "satisfacer" in page.locator(".popover-word-btn").all_text_contents()
    page.keyboard.press("Escape")
    print("PASS 12: recent results persist across reload in localStorage")

    # ---- 13. favourites: star toggles, sidebar view, persistence ----
    open_word(page, "hacer")
    page.locator(".fav-btn").click()
    assert "active" in page.locator(".fav-btn").get_attribute("class")
    page.locator(".side-item[data-target='view-favourites']").click()
    page.wait_for_selector("#favourites-view", state="visible", timeout=3000)
    fav_lemmas = page.locator(".favourite-card .favourite-lemma .lemma").all_text_contents()
    assert "hacer" in fav_lemmas, fav_lemmas
    # persistence across reload (same origin storage)
    page.reload()
    page.wait_for_timeout(400)
    page.locator(".side-item[data-target='view-favourites']").click()
    page.wait_for_selector("#favourites-view", state="visible", timeout=3000)
    assert "hacer" in page.locator(".favourite-card .favourite-lemma .lemma").all_text_contents()
    # clicking a favourite re-analyzes it
    page.locator(".favourite-card .card-link", has_text="Analizar").first.click()
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    assert page.locator("#dashboard .entry-form").inner_text() == "hacer"
    print("PASS 13: favourites persist across reload; clicking one re-analyzes the lemma")

    # ---- 14. deep link ?word= resolves on load ----
    deep = browser.new_page(viewport={"width": 1535, "height": 1024})
    deep.goto(BASE + "/?word=satisfacer", wait_until="networkidle")
    deep.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    assert deep.locator("#dashboard .entry-form").inner_text() == "satisfacer"
    assert deep.locator(".radial-hub text").text_content() == "hacer"
    deep.close()
    print("PASS 14: ?word=satisfacer resolves on load to the satisfacer analysis")

    # ---- screenshots: captured in the sqlite flow with hablábamos (the
    #      mockup example) so they are directly comparable to design_UI.png.
    #      The checks below (dashboard render, decomposition, empty states,
    #      dark data-theme, mobile layout) still run here against the fixture,
    #      which is the empty-state test harness. ----
    page.goto(BASE + "/?word=satisfacer", wait_until="networkidle")
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    page.evaluate("document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    print("PASS 15: satisfacer dashboard renders (screenshot captured in the sqlite flow)")

    # decomposition accordion (2-way split, first/cleanest analysis)
    frame_scroll(page, "#region-morphology")
    page.locator(".decompose-toggle").click()
    page.wait_for_selector(".decompose-body", state="visible", timeout=3000)
    segs = page.locator(".decompose-chip .seg").all_text_contents()
    assert segs == ["satisfac", "-er"], segs
    print("PASS 16: decomposition accordion splits satisfac + -er")

    # 45: empty states via heder (singleton family, no origin)
    page.goto(BASE + "/?word=heder", wait_until="networkidle")
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    assert page.locator("#region-origin .empty-state").inner_text() == EMPTY_ORIGIN
    assert page.locator("#region-cognates .empty-state").inner_text() == EMPTY_COGNATES
    assert page.locator("#region-mnemonics .empty-state").inner_text() == EMPTY_MNEMONIC
    assert page.locator("#region-family .radial-empty").inner_text() == EMPTY_FAMILY
    assert page.locator("#region-family .count-badge").inner_text() == "1"
    print("PASS 17: heder renders all four documented empty states (origin/cognates/mnemonics/family)")

    # ---- 18. dark mode ----
    dark = browser.new_page(viewport={"width": 1535, "height": 1024}, color_scheme="dark")
    dark.goto(BASE + "/?word=satisfacer", wait_until="networkidle")
    dark.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    assert dark.locator("html").get_attribute("data-theme") in ("system", "dark")
    dark.close()
    print("PASS 18: dark mode applies (data-theme set)")

    # ---- 19. mobile 400px: single column + horizontal sidebar ----
    mobile = browser.new_page(viewport={"width": 400, "height": 900})
    mobile.goto(BASE + "/?word=satisfacer", wait_until="networkidle")
    mobile.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    widths = mobile.evaluate(
        """() => ['region-morphology','region-family','region-origin',
                   'region-cognates','region-mnemonics','region-forms'].map(
            (id) => Math.round(document.getElementById(id).getBoundingClientRect().width))"""
    )
    assert all(w >= 360 for w in widths), widths  # one full-width column each
    sidebar_top = mobile.evaluate("() => document.querySelector('.sidebar').getBoundingClientRect().top")
    assert sidebar_top < 300, sidebar_top  # horizontal bar below the header, not a tall rail
    mobile.close()
    print(f"PASS 19: mobile renders single-column ({widths}); horizontal sidebar below header")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    backend = os.environ.get("MORPH_BACKEND", "fixture")
    proc = start_server(backend)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                if backend == "sqlite":
                    run_real_flows(browser)
                else:
                    run_flows(browser)
            finally:
                browser.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("ALL UI CHECKS PASSED")


# ---------------------------------------------------------------------------
# Real-data flow (MORPH_BACKEND=sqlite): latency, dropdown quality, the
# mienta/hecho ambiguities, Layer-3 map/list interactions and the dashboard
# on real data.
# ---------------------------------------------------------------------------

_REAL_QUERIES = ["h", "ha", "hac", "hace", "hacer", "mient", "hiz", "casa", "cant"]

_LATENCY_INIT = """
window.__latDeltas = [];
window.__lastInputAt = null;
function attachLatencyObserver() {
    new MutationObserver((muts) => {
        for (const m of muts) {
            if (m.type === 'attributes' && m.attributeName === 'hidden'
                && m.target.id === 'search-listbox' && !m.target.hidden
                && window.__lastInputAt != null) {
                window.__latDeltas.push(performance.now() - window.__lastInputAt);
                window.__lastInputAt = null;
            }
        }
    }).observe(document.body, {subtree: true, attributes: true, attributeFilter: ['hidden']});
}
if (document.body) attachLatencyObserver();
else document.addEventListener('DOMContentLoaded', attachLatencyObserver);
"""


def run_real_flows(browser):
    page = browser.new_page(viewport={"width": 1535, "height": 1024})
    page.add_init_script(_LATENCY_INIT)
    page.goto(BASE + "/", wait_until="networkidle")

    # ---- 1. keystroke -> dropdown paint latency ----
    print("latency (keystroke -> dropdown paint), ms:")
    for q in _REAL_QUERIES:
        if len(q) < 2:
            type_query(page, q)
            page.wait_for_timeout(500)
            assert page.locator("#search-listbox").is_hidden(), f"{q!r} must not fire a search"
            print(f"  {q:7s} no request (1-char guard)")
            continue
        page.evaluate("window.__lastInputAt = performance.now()")
        type_query(page, q)
        page.wait_for_selector(".option-row", state="visible", timeout=5000)
        page.wait_for_timeout(80)
        d = page.evaluate("() => window.__latDeltas.slice(-1)[0]")
        print(f"  {q:7s} {d if d is not None else 'n/a'}")
    print("PASS 1: latency measured; single-char queries never fire")

    # ---- 2. dropdown quality on real data ('hac') ----
    type_query(page, "hac")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    rows = page.evaluate(
        """() => [...document.querySelectorAll('.option-row')].map((r) => ({
            form: r.querySelector('.row-form').textContent,
            pos: r.querySelector('.pos-chip').textContent,
        }))"""
    )
    assert rows and rows[0]["form"] == "hacer", rows[0]
    print(f"PASS 2: 'hac' dropdown rendered ({len(rows)} rows, first={rows[0]['form']})")

    # ---- 3. mienta ambiguity in the dropdown ----
    type_query(page, "mienta")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    mienta_rows = page.locator(".option-row", has=page.locator(".row-form", has_text=re.compile(r"^mienta$")))
    expect(mienta_rows).to_have_count(2)
    quals = sorted(mienta_rows.locator(".row-qualifier").all_text_contents())
    assert quals == ["(mentar)", "(mentir)"], quals
    print("PASS 3: mienta shows mentir + mentar rows")

    # ---- 4. no-matches state ----
    type_query(page, "zzzz")
    expect(page.locator("#search-status")).to_have_text("Sin resultados", timeout=8000)
    assert page.locator("#search-listbox").is_hidden()
    print("PASS 4: zzzz shows clean 'Sin resultados'")

    # ---- 4b. dropdown selection path on real data (the original product
    #      rule: analysis triggered by selecting a concrete form). Row 0 of
    #      'miento' is miento (mentar, family head 'mente'); row 1 is miento
    #      (mentir). ArrowDown+Enter must open the highlighted row, i.e. the
    #      mentir analysis — proving the selected row, not the top-ranked
    #      free-text resolution. ----
    type_query(page, "miento")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("ArrowDown")  # row 0 highlighted -> row 1 (mentir)
    page.keyboard.press("Enter")
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=8000)
    assert page.locator("#dashboard .entry-form").inner_text() == "miento"
    assert page.locator(".radial-hub text").text_content() == "mentir", \
        "dropdown selection must open the highlighted row (miento under mentir), not the top-ranked (mentar)"
    print("PASS 4b: dropdown selection (ArrowDown+Enter) opens miento under mentir")

    # ---- 5. dashboard on real data: hacer ----
    open_word(page, "hacer")
    assert page.locator("#dashboard .entry-form").inner_text() == "hacer"
    for rid in REGIONS:
        assert page.locator(f"#{rid}").is_visible(), rid
    assert page.locator(".radial-hub text").text_content() == "hacer"
    assert page.locator(".radial-node").count() <= 10
    strip = page.locator("#region-forms .form-item .form-word").all_text_contents()
    assert len(strip) >= 6, strip
    print(f"PASS 5: hacer dashboard renders; strip {strip}")

    # ---- 6. Layer 3 map: open, hover-path, zoom, node navigation ----
    page.set_viewport_size({"width": 1700, "height": 1900})
    page.locator("#region-family .card-link", has_text="Ver toda la familia").click()
    page.wait_for_selector("#layer3 .map-wrap", state="visible", timeout=10000)
    assert page.locator("#layer3 .map-node").count() >= 10
    assert page.locator("#layer3 .map-node.is-root .map-node-lemma").text_content() == "hacer"
    # hover path to root from any non-root node
    target = page.locator("#layer3 .map-node:not(.is-root):not(.is-selected)").first
    target.scroll_into_view_if_needed()
    target.hover()
    page.wait_for_timeout(250)
    assert page.locator("#layer3 .map-node.is-path").count() >= 2
    # zoom controls
    assert page.locator("#layer3 .map-toolbar .zoom-level").inner_text() == "100%"
    page.locator("#layer3 .zoom-btn", has_text="+").click()
    assert page.locator("#layer3 .map-toolbar .zoom-level").inner_text() == "125%"
    page.mouse.move(8, 8)
    page.wait_for_timeout(200)
    print("PASS 6: Layer-3 map renders the full hacer tree; hover path + zoom work")
    # navigate to a node from the map (keyboard path — dodges sticky overlays)
    target.focus()
    page.keyboard.press("Enter")
    page.wait_for_selector("#dashboard .entry-form", state="visible", timeout=10000)
    assert page.locator("#dashboard .entry-form").inner_text() != "hacer"
    print(f"PASS 6b: opening a map node navigates to {page.locator('#dashboard .entry-form').inner_text()}'s analysis")

    # ---- 7. Layer 3 list: paradigm sections + clitics toggle ----
    open_word(page, "hacer")
    page.locator("#region-forms .card-link", has_text="Ver conjugación completa").click()
    page.wait_for_selector("#layer3 .entry-card", state="visible", timeout=20000)
    hacer_card = page.locator("#layer3 .member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^hacer$"))).first
    hacer_card.locator(".show-all").click()
    heads = page.locator("#layer3 .paradigm-head").all_text_contents()
    for expected in ["No personales", "Indicativo", "Subjuntivo", "Imperativo", "Con clíticos"]:
        assert expected in heads, (expected, heads)
    indic = page.locator("#layer3 .paradigm-section", has=page.locator(".paradigm-head", has_text="Indicativo"))
    chips = indic.locator(".form-chip").all_text_contents()
    wanted = ["hago", "haces", "hace", "hacemos", "hacéis", "hacen"]
    idxs = [chips.index(w) for w in wanted]
    assert idxs == sorted(idxs), (chips, idxs)
    expect(page.locator("#layer3 .show-all", has_text="formas con clítico")).to_have_count(1)
    page.locator("#layer3 .show-all", has_text="formas con clítico").click()
    print("PASS 7: Layer-3 list shows paradigm sections (1sg..3pl order) and the clitic toggle expands")

    # ---- 8. cousins strip inside Layer 3 (echar) ----
    open_word(page, "echar")
    assert page.locator("#region-origin .origin-source-word").inner_text() == "iactāre"
    steps = page.locator("#region-origin .origin-stage .word").all_text_contents()
    # real chain is rich (iactāre -> ... -> echar); assert direction oldest->newest
    assert steps and steps[0] == "iactāre" and steps[-1] == "echar" and len(steps) >= 2, steps
    langs = page.locator("#region-origin .origin-stage .lang").all_text_contents()
    assert langs[0] == "latín" and langs[-1] == "español", langs
    assert page.locator("#region-origin .origin-arrow").count() == len(steps) - 1
    page.locator("#region-forms .card-link", has_text="Ver conjugación completa").click()
    page.wait_for_selector("#layer3 .cousins-strip", state="visible", timeout=20000)
    assert page.locator("#layer3 .cousins-title").inner_text() == "También del latín iactāre"
    assert page.locator("#layer3 .cousin-word").count() >= 1
    print(f"PASS 8: origin chain on real data (iactāre -> ... -> echar, {len(steps)} stages); cousins strip in Layer 3")

    # ---- 9. mockup-comparable screenshots: hablábamos on real data ----
    page.set_viewport_size({"width": 1535, "height": 1024})
    open_word(page, "hablábamos")
    assert page.locator("#dashboard .entry-form").inner_text() == "hablábamos"
    # radial: hub is hablar; the backend includes the hub as a node, so it
    # must be filtered out of the satellite ring; one pill per lemma (no
    # dupes like the two hablador rows); searched form highlighted
    assert page.locator(".radial-hub text").text_content() == "hablar"
    sat_words = page.locator(".radial-node .word").all_text_contents()
    assert "hablar" not in sat_words, sat_words
    assert len(sat_words) == len(set(sat_words)), sat_words
    assert 1 <= len(sat_words) <= 10, len(sat_words)
    assert page.locator(".radial-node.is-selected text.word").text_content() == "hablábamos"
    # required empty states (cognates + mnemonics, Phase 1 -> null)
    assert page.locator("#region-cognates .empty-state").inner_text() == EMPTY_COGNATES
    assert page.locator("#region-mnemonics .empty-state").inner_text() == EMPTY_MNEMONIC
    # morphology card mirrors the mockup summary line
    assert "verbo · modo indicativo · pretérito imperfecto · 1ª persona del plural" in \
        page.locator(".morph-summary").inner_text()
    print(f"PASS 9: hablábamos dashboard; radial hub 'hablar' with {len(sat_words)} distinct satellites, hablábamos highlighted; cognates+mnemonics empty states")

    # 40: full dashboard, top of page
    page.evaluate("document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    shot(page, "40-dashboard.png", full=True)
    # 43: radial family framed
    frame_scroll(page, "#region-family")
    page.mouse.move(8, 8)
    page.wait_for_timeout(250)
    shot(page, "43-radial-family.png")
    # 44: origin chain framed
    frame_scroll(page, "#region-origin")
    page.wait_for_timeout(250)
    shot(page, "44-origin-chain.png")
    # 46: decomposition accordion expanded
    frame_scroll(page, "#region-morphology")
    page.locator(".decompose-toggle").click()
    page.wait_for_selector(".decompose-body", state="visible", timeout=3000)
    segs = page.locator(".decompose-chip .seg").all_text_contents()
    assert segs == ["habl", "-ábamos"], segs
    page.mouse.move(8, 8)
    page.wait_for_timeout(250)
    shot(page, "46-morphology-expanded.png")
    # 45: empty states framed (cognates + mnemonics of hablábamos)
    frame_scroll(page, "#region-cognates")
    page.wait_for_timeout(250)
    shot(page, "45-empty-states.png")
    print("PASS 9b: 43-radial-family, 44-origin-chain, 45-empty-states, 46-morphology-expanded captured")
    # 41: dark dashboard
    dark = browser.new_page(viewport={"width": 1535, "height": 1024}, color_scheme="dark")
    dark.goto(BASE + "/?word=hablábamos", wait_until="networkidle")
    dark.wait_for_selector("#dashboard .entry-form", state="visible", timeout=15000)
    dark.evaluate("document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0)")
    dark.wait_for_timeout(300)
    shot(dark, "41-dashboard-dark.png", full=True)
    dark.close()
    # 42: mobile 400px, single column + horizontal sidebar
    mobile = browser.new_page(viewport={"width": 400, "height": 900})
    mobile.goto(BASE + "/?word=hablábamos", wait_until="networkidle")
    mobile.wait_for_selector("#dashboard .entry-form", state="visible", timeout=15000)
    widths = mobile.evaluate(
        """() => ['region-morphology','region-family','region-origin',
                   'region-cognates','region-mnemonics','region-forms'].map(
            (id) => Math.round(document.getElementById(id).getBoundingClientRect().width))"""
    )
    assert all(w >= 360 for w in widths), widths
    sidebar_top = mobile.evaluate("() => document.querySelector('.sidebar').getBoundingClientRect().top")
    assert sidebar_top < 300, sidebar_top
    mobile.evaluate("document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0)")
    mobile.wait_for_timeout(300)
    shot(mobile, "42-dashboard-mobile.png", full=True)
    mobile.close()
    print(f"PASS 9c: 41-dashboard-dark, 42-dashboard-mobile (400px, single column {widths}) captured")

    # legacy real-data dark/mobile artifacts (hacer)
    dark = browser.new_page(viewport={"width": 1535, "height": 1024}, color_scheme="dark")
    dark.goto(BASE + "/?word=hacer", wait_until="networkidle")
    dark.wait_for_selector("#dashboard .entry-form", state="visible", timeout=15000)
    shot(dark, "05-dark.png")
    dark.close()
    mobile = browser.new_page(viewport={"width": 400, "height": 900})
    mobile.goto(BASE + "/?word=hacer", wait_until="networkidle")
    mobile.wait_for_selector("#dashboard .entry-form", state="visible", timeout=15000)
    shot(mobile, "06-mobile.png")
    mobile.close()
    print("PASS 9d: 05-dark and 06-mobile regenerated on real data")


if __name__ == "__main__":
    main()
