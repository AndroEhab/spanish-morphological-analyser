"""Real-browser UI smoke test for the Spanish Morphological Analyser.

Starts uvicorn on port 8011, drives the page with Playwright (headless
chromium), exercises the real user flow end to end, and captures screenshots
to ``scripts/screenshots/``.

Run:  .venv\\Scripts\\python scripts\\ui_smoke.py
"""

import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "scripts" / "screenshots"
PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"


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


def shot(page, name):
    path = SHOTS / name
    page.screenshot(path=str(path))
    print(f"  screenshot: {name}")


def type_query(page, text):
    page.fill("#search-input", "")
    page.fill("#search-input", text)


def select_row(page, down_presses, enter=True):
    for _ in range(down_presses):
        page.keyboard.press("ArrowDown")
    if enter:
        page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=5000)


def run_flows(browser):
    page = browser.new_page(viewport={"width": 1100, "height": 800})
    if os.environ.get("UI_SMOKE_DEBUG"):
        page.add_init_script("""
          window.__log = [];
          const t = () => performance.now().toFixed(1);
          document.addEventListener('blur', (e) => window.__log.push(t() + ' BLUR ' + (e.target.id||e.target.tagName)), true);
          document.addEventListener('focus', (e) => window.__log.push(t() + ' FOCUS ' + (e.target.id||e.target.tagName)), true);
          window.addEventListener('blur', () => window.__log.push(t() + ' WINBLUR'));
          window.addEventListener('focus', () => window.__log.push(t() + ' WINFOCUS'));
          new MutationObserver(() => {
            const lb = document.getElementById('search-listbox');
            if (lb) window.__log.push(t() + ' listbox.hidden=' + lb.hidden + ' ad=' + document.getElementById('search-input').getAttribute('aria-activedescendant'));
          }).observe(document.body, {subtree: true, attributes: true, attributeFilter: ['hidden']});
        """)
    page.goto(BASE + "/", wait_until="networkidle")
    assert not page.locator("#analysis .entry-card").count(), "analysis present on first load"

    # ---- 1. type "mient" -> listbox shows two mienta options with qualifiers
    type_query(page, "mient")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    expect(page.locator(".option")).to_have_count(21)
    mienta_mentir = page.locator(".option", has_text=re.compile(r"^mienta\(mentir\)"))
    mienta_mentar = page.locator(".option", has_text=re.compile(r"^mienta\(mentar\)"))
    expect(mienta_mentir).to_have_count(1)
    expect(mienta_mentar).to_have_count(1)
    quals = sorted(page.locator(".option", has_text=re.compile(r"^mienta\(")).locator(".row-qualifier").all_text_contents())
    assert quals == ["(mentar)", "(mentir)"], quals
    print("PASS 1: 'mient' renders mienta (mentir) and mienta (mentar) as separate options")
    # the listbox must scroll, not grow: bounded height with overflow
    lb = page.evaluate("""() => {
        const lb = document.getElementById('search-listbox');
        return {scrolls: lb.scrollHeight > lb.clientHeight, cap: Math.round(parseFloat(getComputedStyle(lb).maxHeight))};
    }""")
    assert lb["scrolls"], "listbox should scroll when results overflow"
    assert lb["cap"] <= 400, lb
    print("PASS 1b: listbox is height-capped and scrolls (cap ~" + str(lb["cap"]) + "px)")
    shot(page, "01-dropdown.png")

    # ---- 2. Escape closes the dropdown; Enter with no highlight does nothing
    page.keyboard.press("Escape")
    assert page.locator("#search-listbox").is_hidden(), "listbox still visible after Escape"
    assert page.locator("#search-input").get_attribute("aria-expanded") == "false"
    page.keyboard.press("Enter")
    page.wait_for_timeout(400)
    assert not page.locator("#analysis .entry-card").count(), "Enter without highlight triggered analysis"
    print("PASS 2: Escape closes dropdown; Enter with no highlighted option does nothing")

    # ---- 3. ArrowDown x2 + Enter selects a row; header shows form + lemma
    type_query(page, "mient")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    select_row(page, 2)
    assert page.locator(".entry-form").inner_text() == "miento", page.locator(".entry-form").inner_text()
    assert "mentir" in page.locator(".entry-lemma").inner_text()
    print("PASS 3: ArrowDown x2 + Enter opens analysis for miento (mentir)")

    # ---- 4. select mienta (mentir): header form, lemma, ambiguous features
    type_query(page, "mient")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    select_row(page, 8)
    actual = page.locator(".entry-form").inner_text()
    if actual != "mienta" and os.environ.get("UI_SMOKE_DEBUG"):
        print("  [dbg] EVENT LOG:")
        for line in page.evaluate("() => window.__log"):
            print("   ", line)
    assert actual == "mienta", f"expected mienta, got {actual!r}"
    assert "mentir" in page.locator(".entry-lemma").inner_text()
    expect(page.locator(".entry-features li")).to_have_count(2)
    assert page.locator(".entry-card").get_attribute("data-entry-id") == "mienta::mentir::verb"
    assert "Dictionary id:" not in page.locator(".entry-card").inner_text()
    print("PASS 4: mienta (mentir) analysis shows form, lemma and both subjunctive analyses")
    shot(page, "02-analysis-mienta.png")

    # ---- 5. search "hacer"; infinitive ranks first; family renders
    type_query(page, "hacer")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    first_form = page.locator(".option").first.locator(".row-form").inner_text()
    assert first_form == "hacer", first_form
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=5000)
    assert page.locator(".entry-form").inner_text() == "hacer"
    verbs = page.locator(".pos-section", has=page.locator("h2", has_text="Verbs"))
    expect(verbs).to_have_count(1)
    satis = page.locator(".member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^satisfacer$")))
    expect(satis).to_have_count(1)
    expect(satis.locator(".show-all")).to_have_count(1)
    assert "47 forms" in satis.locator(".show-all").inner_text()
    expect(page.locator(".pos-nav button")).to_have_count(3)
    print("PASS 5: 'hacer' -> hacer first; verb section renders satisfacer card with 'Show all 47 forms' toggle")
    page.evaluate("window.scrollTo(0, 0)")
    shot(page, "03-analysis-hacer.png")

    # ---- 6. expand satisfacer's form grid
    satis.locator(".show-all").click()
    expect(satis.locator(".show-all")).to_have_count(0)
    expect(satis.locator(".form-chip")).to_have_count(47)
    satis.scroll_into_view_if_needed()
    page.mouse.move(8, 8)  # leave the grid so no hover tooltip appears in the shot
    page.wait_for_timeout(250)
    shot(page, "04-expanded.png")
    print("PASS 6: 'Show all 47 forms' expands satisfacer to 47 form chips")

    # ---- 7. Escape closes a reopened dropdown (end-of-flow re-check)
    type_query(page, "hac")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    assert not page.locator("#search-listbox").is_hidden()
    page.keyboard.press("Escape")
    assert page.locator("#search-listbox").is_hidden()
    print("PASS 7: Escape closes a reopened dropdown")

    # ---- 8. dark mode
    dark = browser.new_page(viewport={"width": 1100, "height": 800}, color_scheme="dark")
    dark.goto(BASE + "/", wait_until="networkidle")
    type_query(dark, "mient")
    dark.wait_for_selector(".option-row", state="visible", timeout=5000)
    select_row(dark, 8)
    shot(dark, "05-dark.png")
    dark.close()
    print("PASS 8: dark-mode analysis captured")

    # ---- 9. mobile 400px
    mobile = browser.new_page(viewport={"width": 400, "height": 800})
    mobile.goto(BASE + "/", wait_until="networkidle")
    type_query(mobile, "hacer")
    mobile.wait_for_selector(".option-row", state="visible", timeout=5000)
    mobile.keyboard.press("Enter")
    mobile.wait_for_selector("#analysis .entry-card", state="visible", timeout=5000)
    shot(mobile, "06-mobile.png")
    mobile.close()
    print("PASS 9: mobile (400px) analysis captured")

    # ---- 10. large synthetic family: probar (15-member verb group, 315-form head)
    start = time.perf_counter()
    type_query(page, "probar")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    render_elapsed = time.perf_counter() - start
    assert render_elapsed < 8, f"analysis render too slow: {render_elapsed:.1f}s"
    assert page.locator(".entry-form").inner_text() == "probar"
    verbs = page.locator(".pos-section", has=page.locator("h2", has_text="Verbs"))
    expect(verbs.locator(".member-card")).to_have_count(12)
    expect(verbs.locator(".show-all", has_text="lemmas")).to_have_count(1)
    assert "15 lemmas" in verbs.locator(".show-all", has_text="lemmas").inner_text()
    # unknown POS tags from the backend render without breaking
    expect(page.locator(".pos-section", has=page.locator("h2", has_text="Names"))).to_have_count(1)
    expect(page.locator(".pos-section", has=page.locator("h2", has_text="Phrases"))).to_have_count(1)
    expect(page.locator(".pos-nav button")).to_have_count(5)
    print(f"PASS 10: probar family renders in {render_elapsed:.2f}s; verb section collapsed to 12 with "
          "'Show all 15 lemmas'; unknown POS sections (Names/Phrases) render")

    # ---- 11. expand section + expand the 300+ form member; page stays responsive
    verbs.locator(".show-all", has_text="lemmas").click()
    expect(verbs.locator(".member-card")).to_have_count(15)
    expect(verbs.locator(".show-all", has_text="lemmas")).to_have_count(0)
    probar_card = page.locator(".member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^probar$")))
    expect(probar_card.locator(".show-all")).to_have_count(1)
    probar_card.locator(".show-all").click()
    clitic_toggle = probar_card.locator(".show-all", has_text="clitic forms")
    if clitic_toggle.count():
        clitic_toggle.click()  # the clitics bucket stays collapsed until its own toggle
    chip_count = probar_card.locator(".form-chip").count()
    assert chip_count >= 300, chip_count
    t0 = time.perf_counter()
    assert page.evaluate("1 + 1") == 2
    assert time.perf_counter() - t0 < 2, "page unresponsive after rendering large grid"
    print(f"PASS 11: section expanded to 15 lemmas; probar card shows {chip_count} form chips; page responsive")
    page.evaluate("document.querySelector('.pos-section').scrollIntoView()")
    page.mouse.move(8, 8)  # leave the grid so no hover tooltip appears in the shot
    page.wait_for_timeout(300)
    shot(page, "07-large-family.png")
    # relation chips with long labels (task C) must wrap gracefully next to the lemma
    page.locator(".pos-section", has=page.locator("h2", has_text="Nouns")).scroll_into_view_if_needed()
    page.wait_for_timeout(250)
    shot(page, "09-relation-chips.png")
    inherited = page.locator(".relation-chip", has_text="inherited from Latin")
    expect(inherited).to_have_count(1)
    expect(page.locator(".relation-chip", has_text="same paradigm as probar")).to_have_count(1)
    assert inherited.first.evaluate("(el) => el.getBoundingClientRect().width > 0")
    print("PASS 11b: long relation labels render and wrap next to the lemma")

    # ---- 12. long gloss truncates to one line in the dropdown
    type_query(page, "contraprobar")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    first_opt = page.locator(".option-row").first
    gloss = first_opt.locator(".row-gloss")
    assert gloss.evaluate("(el) => el.scrollWidth > el.clientWidth"), "long gloss should be ellipsised"
    assert gloss.evaluate("(el) => getComputedStyle(el).textOverflow") == "ellipsis"
    assert first_opt.evaluate("(el) => el.offsetHeight") <= 60, "long gloss must not grow the row"
    shot(page, "08-long-gloss-dropdown.png")
    print("PASS 12: long gloss truncated to one line with ellipsis, row height unchanged")


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
# Real-data flow (MORPH_BACKEND=sqlite): latency, dropdown quality, large
# analysis, the mienta ambiguity, hizo/hacerlo, and the no-matches state.
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
    page = browser.new_page(viewport={"width": 1100, "height": 900})
    page.add_init_script(_LATENCY_INIT)
    page.goto(BASE + "/", wait_until="networkidle")

    # ---- 1. keystroke -> dropdown paint latency (user experience)
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

    # ---- 1b. in-flight cancellation on rapid retype
    page.fill("#search-input", "hac")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.wait_for_timeout(200)  # dropdown for 'hac' is up; fetch in flight
    page.fill("#search-input", "hacer")
    page.wait_for_function(
        """() => {
            const first = document.querySelector('.option-row .row-form');
            return first && first.textContent === 'hacer';
        }""",
        timeout=5000,
    )
    print("PASS 1b: rapid retype cancels in-flight request; final dropdown is 'hacer'")

    # ---- 2. dropdown quality on real data ('hac')
    type_query(page, "hac")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.wait_for_timeout(150)
    shot(page, "real-dropdown-hac.png")
    rows = page.evaluate("""() => [...document.querySelectorAll('.option-row')].map((r) => ({
        form: r.querySelector('.row-form').textContent,
        qual: (r.querySelector('.row-qualifier') || {}).textContent || null,
        pos: r.querySelector('.pos-chip').textContent,
        gloss: (r.querySelector('.row-gloss') || {}).textContent || '',
    }))""")
    print("hac dropdown rows:")
    for r in rows:
        print(f"   {r['form']!r:14s} {r['qual']!r:12s} {r['pos']:6s} gloss={r['gloss'][:44]!r}")
    print("PASS 2: 'hac' dropdown rendered (see rows above)")

    # ---- 3. genuinely large analysis: hacer
    type_query(page, "hacer")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    t0 = time.perf_counter()
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .pos-section", state="visible", timeout=10000)
    render_s = time.perf_counter() - t0
    nodes = page.evaluate("() => document.querySelectorAll('*').length")
    groups = page.evaluate("""() => [...document.querySelectorAll('.pos-section')].map(
        (s) => s.querySelector('h2').textContent + ':' + s.querySelectorAll('.member-card').length)""")
    assert page.locator(".entry-form").inner_text() == "hacer"
    print(f"PASS 3: hacer analysis rendered in {render_s * 1000:.0f} ms; {nodes} DOM nodes; groups: {groups}")
    shot(page, "10-real-hacer.png")
    # scroll smoothness probe: 40 instant jumps, measuring frame pacing
    jank = page.evaluate("""() => new Promise((resolve) => {
        const scroller = document.scrollingElement;
        const total = scroller.scrollHeight - window.innerHeight;
        const steps = 40;
        const deltas = [];
        let i = 0;
        let last = performance.now();
        const step = () => {
            const now = performance.now();
            deltas.push(now - last);
            last = now;
            window.scrollTo(0, Math.round((i / steps) * total));
            i += 1;
            if (i <= steps) requestAnimationFrame(step);
            else resolve({frames: deltas.length, max: Math.round(Math.max(...deltas)),
                          over50: deltas.filter((d) => d > 50).length});
        };
        requestAnimationFrame(step);
    })""")
    assert jank["max"] < 100, jank
    print(f"PASS 3b: scroll probe {jank['frames']} frames, max {jank['max']} ms, {jank['over50']} frames over 50 ms")

    # ---- 3c. paradigm sectioning inside the hacer member card
    type_query(page, "hacer")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=10000)
    hacer_card = page.locator(".member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^hacer$"))).first
    hacer_card.locator(".show-all").click()
    heads = page.locator(".paradigm-head").all_text_contents()
    for expected in ["Non-finite", "Indicative", "Subjunctive", "Imperative", "With clitics"]:
        assert expected in heads, (expected, heads)
    # the citation form sits in the Non-finite section and leads it
    nonfinite = page.locator(".paradigm-section", has=page.locator(".paradigm-head", has_text="Non-finite"))
    assert nonfinite.locator(".form-chip.citation").count() >= 1
    assert nonfinite.locator(".form-chip").first.inner_text() == "hacer"
    # present-tense chips keep person order 1sg, 2sg, 3sg, 1pl, 2pl, 3pl
    # (vos forms such as "hacés" may interleave with 2sg — the six standard
    # persons must appear in strictly increasing order, not contiguously)
    indic = page.locator(".paradigm-section", has=page.locator(".paradigm-head", has_text="Indicative"))
    indic_chips = indic.locator(".form-chip").all_text_contents()
    wanted = ["hago", "haces", "hace", "hacemos", "hacéis", "hacen"]
    idxs = [indic_chips.index(w) for w in wanted]
    assert idxs == sorted(idxs), (indic_chips, idxs)
    # clitics are collapsed by default with their own toggle
    clitics_toggle = page.locator(".show-all", has_text="clitic forms")
    expect(clitics_toggle).to_have_count(1)
    hacer_card.scroll_into_view_if_needed()
    page.mouse.move(8, 8)  # leave the grid so no hover tooltip appears in the shot
    page.wait_for_timeout(200)
    shot(page, "13-paradigm-sections.png")
    clitics_section = page.locator(".paradigm-section", has=page.locator(".paradigm-head", has_text="With clitics"))
    clitics_section.scroll_into_view_if_needed()
    chips_before = clitics_section.locator(".form-chip").count()
    clitics_toggle.click()
    expect(clitics_toggle).to_have_count(0)
    chips_after = clitics_section.locator(".form-chip").count()
    assert chips_after > chips_before, (chips_before, chips_after)
    page.mouse.move(8, 8)  # leave the grid so no hover tooltip appears in the shot
    page.wait_for_timeout(200)
    shot(page, "14-clitics-expanded.png")
    print(f"PASS 3c: paradigm sections render (Non-finite/Indicative/Subjunctive/Imperative/With clitics); "
          f"clitic toggle expands {chips_before} -> {chips_after} chips")

    # ---- 4. the mienta ambiguity
    type_query(page, "mienta")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    mienta_rows = page.locator(".option-row", has=page.locator(".row-form", has_text=re.compile(r"^mienta$")))
    expect(mienta_rows).to_have_count(2)
    quals = sorted(mienta_rows.locator(".row-qualifier").all_text_contents())
    assert quals == ["(mentar)", "(mentir)"], quals
    page.evaluate("window.scrollTo(0, 0)")  # the scroll probe left the viewport at the bottom
    page.wait_for_timeout(120)
    shot(page, "11-real-mienta.png")
    # each row leads to a different analysis header (order-agnostic: click the row)
    mienta_rows.filter(has=page.locator(".row-qualifier", has_text="mentir")).click()
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "mienta"
    assert "mentir" in page.locator(".entry-lemma").inner_text()
    type_query(page, "mienta")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    mrows2 = page.locator(".option-row", has=page.locator(".row-form", has_text=re.compile(r"^mienta$")))
    mrows2.filter(has=page.locator(".row-qualifier", has_text="mentar")).click()
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "mienta"
    assert "mentar" in page.locator(".entry-lemma").inner_text()
    print("PASS 4: mienta shows mentir + mentar rows; each selects a different analysis header")

    # ---- 5. hizo
    type_query(page, "hizo")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "hizo"
    assert "hacer" in page.locator(".entry-lemma").inner_text()
    feats = page.locator(".entry-features li").all_text_contents()
    assert any("preterite" in f and "3rd singular" in f for f in feats), feats
    assert page.locator(".pos-section h2", has_text=re.compile(r"^Verbs$")).count() == 1
    print("PASS 5: hizo -> header hizo/hacer with features " + str(feats))
    shot(page, "12-real-hizo.png")

    # ---- 6. hacerlo (clitic form findable, features mention the clitic)
    type_query(page, "hacerlo")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    assert page.locator(".option-row").count() >= 1
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "hacerlo"
    feats = page.locator(".entry-features li").all_text_contents()
    assert any("clitic" in f for f in feats), feats
    print("PASS 6: hacerlo findable; features mention the clitic: " + str(feats[:2]))

    # ---- 6b. three-way hecho ambiguity (verb participle / adjective / noun)
    type_query(page, "hecho")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    hecho_rows = page.locator(".option-row", has=page.locator(".row-form", has_text=re.compile(r"^hecho$")))
    expect(hecho_rows).to_have_count(3)
    pos_chips = sorted(hecho_rows.locator(".pos-chip").all_text_contents())
    assert pos_chips == ["adj", "noun", "verb"], pos_chips
    # only the disambiguating qualifier renders; the self-qualifying rows
    # ("hecho (hecho)") leave the qualifier cell empty
    quals = sorted(hecho_rows.locator(".row-qualifier").all_text_contents())
    assert quals == ["", "", "(hacer)"], quals
    shot(page, "15-real-hecho-ambiguity.png")
    print("PASS 6b: hecho shows three rows (hacer participle / adj / noun); only the (hacer) qualifier renders — self-qualifying cells are empty")

    # ---- 6c. relation chips across the hacer family (labels still being tuned)
    type_query(page, "hacer")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=15000)
    for _ in range(6):  # expand any collapsed lemma sections so all chips are visible
        toggles = page.locator(".show-all", has_text="lemmas")
        if not toggles.count():
            break
        toggles.first.click()
        page.wait_for_timeout(120)
    # no exact label text is asserted — the pipeline is still adjusting the
    # relation strings; what matters is that chips render across the family
    chips = page.locator(".relation-chip")
    assert chips.count() >= 8, chips.count()
    # the longest label must stay inside its card (no layout breakage)
    longest_text = chips.evaluate_all(
        "(els) => els.reduce((m, el) => (el.textContent.length > m.length ? el.textContent : m), '')"
    )
    assert len(longest_text) >= 25, longest_text
    longest_chip = page.locator(".relation-chip", has_text=re.compile(re.escape(longest_text)))
    assert longest_chip.count() >= 1
    assert longest_chip.first.evaluate(
        "(el) => el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().right <= el.closest('.member-card').getBoundingClientRect().right"
    )
    # frame the shot on the card carrying the longest label, clearing the
    # sticky pos-nav bar so the card's top labels are not clipped; the page
    # uses CSS smooth scrolling, so force an instant scroll here
    longest_card = longest_chip.first.locator("xpath=ancestor::*[contains(@class,'member-card')]")
    longest_card.evaluate("""(el) => {
        document.documentElement.style.scrollBehavior = 'auto';
        el.scrollIntoView({block: 'start'});
        window.scrollBy(0, -96);
    }""")
    page.mouse.move(8, 8)  # leave the grid so no hover tooltip appears in the shot
    page.wait_for_timeout(300)
    shot(page, "16-real-hacer-relations.png")
    print(f"PASS 6c: {chips.count()} relation chips render across the family; longest label {longest_text!r} stays inside its card")

    # ---- 7. no-matches state (substring fallback path)
    type_query(page, "zzzz")
    page.wait_for_timeout(1400)  # substring fallback ~160 ms + debounce + render
    assert page.locator("#search-listbox").is_hidden()
    assert page.locator("#search-status").inner_text() == "No matches"
    assert page.locator(".option-row").count() == 0
    print("PASS 7: zzzz shows clean 'No matches' — no hang, no stale list")

    # ---- 8. dark-mode and mobile shots against real data
    dark = browser.new_page(viewport={"width": 1100, "height": 800}, color_scheme="dark")
    dark.goto(BASE + "/", wait_until="networkidle")
    type_query(dark, "hacer")
    dark.wait_for_selector(".option-row", state="visible", timeout=5000)
    dark.keyboard.press("Enter")
    dark.wait_for_selector("#analysis .entry-card", state="visible", timeout=15000)
    shot(dark, "05-dark.png")
    dark.close()
    mobile = browser.new_page(viewport={"width": 400, "height": 800})
    mobile.goto(BASE + "/", wait_until="networkidle")
    type_query(mobile, "hacer")
    mobile.wait_for_selector(".option-row", state="visible", timeout=5000)
    mobile.keyboard.press("Enter")
    mobile.wait_for_selector("#analysis .entry-card", state="visible", timeout=15000)
    shot(mobile, "06-mobile.png")
    mobile.close()
    print("PASS 8: dark and mobile screenshots regenerated on real data")

    # ---- 9. adverbs get a paradigm table: Base + Superlative, no OTHER
    # heading, citation form chip first. The assertions are driven by the
    # forms' features, not by which family the adverb happens to live in.
    # The adverb screenshots use a taller viewport so whole cards fit below
    # the sticky nav without clipping.
    page.set_viewport_size({"width": 1100, "height": 1200})

    def frame_below_nav(loc):
        # scroll so the element's top sits just below the sticky nav (~52px)
        loc.evaluate("""(el) => {
            document.documentElement.style.scrollBehavior = 'auto';
            const top = el.getBoundingClientRect().top + window.scrollY;
            window.scrollTo(0, top - 72);
        }""")

    type_query(page, "rápidamente")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "rápidamente"
    adv_card = page.locator(".member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^rápidamente$"))).first
    heads = adv_card.locator(".paradigm-head").all_text_contents()
    assert heads == ["Base", "Superlative"], (heads, "adverb card must show Base + Superlative, never a lone OTHER")
    assert adv_card.locator(".form-chip").first.inner_text() == "rápidamente", "citation form chip must come first"
    # 17: rápidamente inside its multi-group family — frame the whole
    # Adverbs group (heading + both adverb cards) below the sticky nav
    page.wait_for_timeout(600)  # let openAnalysis' smooth scroll-to-top settle
    frame_below_nav(page.locator(".pos-section", has=page.locator("h2", has_text="Adverbs")))
    page.mouse.move(8, 8)  # leave the grid so no hover tooltip appears in the shot
    page.wait_for_timeout(200)
    shot(page, "17-adverb-card.png")

    type_query(page, "claramente")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    page.keyboard.press("Enter")
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "claramente"
    cl_card = page.locator(".member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^claramente$"))).first
    heads = cl_card.locator(".paradigm-head").all_text_contents()
    assert heads == ["Base", "Superlative"], (heads, "claramente card must show Base + Superlative, never a lone OTHER")
    assert cl_card.locator(".form-chip").first.inner_text() == "claramente", "citation form chip must come first"
    print("PASS 9: rápidamente and claramente render Base + Superlative (no OTHER); citation form chip first")

    # ---- 10. single-group family: no sticky nav, no count badge; and a
    # lone Other bucket renders as one unlabelled chip group (Defect 2/4)
    type_query(page, "fa")
    page.wait_for_selector(".option-row", state="visible", timeout=5000)
    fa_intj = page.locator(".option-row", has=page.locator(".row-form", has_text=re.compile(r"^fa$")))
    fa_intj.filter(has=page.locator(".pos-chip", has_text="intj")).click()
    page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
    assert page.locator(".entry-form").inner_text() == "fa"
    assert page.locator(".pos-nav").count() == 0, "single-group family must not show the sticky nav"
    assert page.locator(".count-badge").count() == 0, "isolated member must not show the count badge"
    fa_card = page.locator(".member-card").first
    assert fa_card.locator(".paradigm-head").count() == 0, "lone Other bucket must render with no heading"
    assert fa_card.locator(".form-chip").count() == 1
    fa_card.scroll_into_view_if_needed()
    page.mouse.move(8, 8)
    page.wait_for_timeout(200)
    shot(page, "18-single-group-family.png")
    print("PASS 10: fa — single-group family hides nav and count badge; lone Other bucket renders unlabelled")

    # ---- 11. the user-facing promise: rápido (adj), rápido (adv) and
    # rápidamente all resolve to the SAME family, whichever door you come
    # in through. Permanent check: each entry point must yield the
    # identical set of (POS group, member lemma) cards.
    def family_lemma_set():
        out = set()
        for sec in page.locator(".pos-section").all():
            group = sec.locator("h2").first.inner_text()
            for card in sec.locator(".member-card").all():
                out.add((group, card.locator(".member-lemma").first.inner_text()))
        return out

    def open_entry(form, pos):
        type_query(page, form)
        page.wait_for_selector(".option-row", state="visible", timeout=5000)
        row = page.locator(".option-row", has=page.locator(".row-form", has_text=re.compile("^" + re.escape(form) + "$")))
        row.filter(has=page.locator(".pos-chip", has_text=pos)).click()
        page.wait_for_selector("#analysis .entry-card", state="visible", timeout=8000)
        return page.locator(".entry-form").inner_text()

    # ---- adjective door
    assert open_entry("rápido", "adj") == "rápido"
    adv_group = page.locator(".pos-section", has=page.locator("h2", has_text="Adverbs"))
    expect(adv_group).to_have_count(1)
    adv_lemmas = adv_group.locator(".member-lemma").all_text_contents()
    assert "rápidamente" in adv_lemmas, adv_lemmas
    # the rápidamente card carries the "rápido + -mente" relation chip
    rap_card = page.locator(".member-card", has=page.locator(".member-lemma", has_text=re.compile(r"^rápidamente$")))
    assert "rápido + -mente" in rap_card.locator(".relation-chip").all_text_contents(), \
        rap_card.locator(".relation-chip").all_text_contents()
    set_adj = family_lemma_set()
    # 19: the family via the adjective door — frame the Adverbs group
    # (heading + both adverb cards) below the sticky nav
    page.wait_for_timeout(600)  # let openAnalysis' smooth scroll-to-top settle
    frame_below_nav(adv_group)
    page.mouse.move(8, 8)
    page.wait_for_timeout(200)
    shot(page, "19-rapido-from-adjective.png")

    # ---- adverb door
    assert open_entry("rápido", "adv") == "rápido"
    set_adv = family_lemma_set()
    # 21: the adverb entry, framed on the header card so the selected POS
    # is unambiguous (page is already scrolled to top)
    page.wait_for_timeout(600)  # let openAnalysis' smooth scroll-to-top settle
    page.evaluate("document.documentElement.style.scrollBehavior = 'auto'; window.scrollTo(0, 0)")
    page.mouse.move(8, 8)
    page.wait_for_timeout(200)
    shot(page, "21-rapido-adverb-entry.png")

    # ---- -mente door
    assert open_entry("rápidamente", "adv") == "rápidamente"
    set_mente = family_lemma_set()

    assert set_adj == set_adv == set_mente, (
        "rápido (adj), rápido (adv) and rápidamente must land in the same family",
        sorted(set_adj),
        sorted(set_adv),
        sorted(set_mente),
    )
    # sticky nav offers all three POS groups of the shared family
    nav_labels = page.locator(".pos-nav button").all_text_contents()
    assert nav_labels == ["Nouns", "Adjectives", "Adverbs"], nav_labels
    # 20: the family via rápidamente — sticky nav pinned at the very top
    # with all three group buttons visible
    page.wait_for_timeout(600)  # let openAnalysis' smooth scroll-to-top settle
    page.evaluate("""() => {
        document.documentElement.style.scrollBehavior = 'auto';
        const nav = document.querySelector('.pos-nav');
        window.scrollTo(0, nav.getBoundingClientRect().top + window.scrollY);
    }""")
    page.mouse.move(8, 8)
    page.wait_for_timeout(200)
    shot(page, "20-rapido-from-adverb.png")
    print("PASS 11: rápido (adj), rápido (adv) and rápidamente resolve to the same family "
          "(identical member-lemma sets); rápidamente carries 'rápido + -mente'")


if __name__ == "__main__":
    main()
