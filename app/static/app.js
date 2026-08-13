"use strict";

/* Spanish Morphological Analyser — frontend logic.
   Combobox dropdown (no free-text submit) + family analysis view. */

(() => {
  const input = document.getElementById("search-input");
  const listbox = document.getElementById("search-listbox");
  const statusEl = document.getElementById("search-status");
  const loadingEl = document.getElementById("loading");
  const analysisEl = document.getElementById("analysis");
  const kbdHint = document.getElementById("kbd-hint");

  const SEARCH_LIMIT = 25;
  const DEBOUNCE_MS = 120;
  const COLLAPSE_THRESHOLD = 40; // members with more forms start collapsed
  const COLLAPSE_SHOW = 24;      // ...showing this many initially
  const SECTION_COLLAPSE = 12;   // POS groups with more lemmas start collapsed
  const CLITIC_PREVIEW = 12;     // clitic forms shown before the "show N clitic forms" toggle
  const BADGE_MIN_FORMS = 6;     // single-member groups show a count badge only past this many forms

  let results = [];
  let active = -1;
  let searchController = null;
  let debounceTimer = null;
  let scrollspyHandler = null;
  const expandedMembers = new Set(); // member keys whose full form list is shown
  const expandedSections = new Set(); // pos keys whose full lemma list is shown
  const expandedClitics = new Set(); // member keys whose clitic forms are expanded

  /* ---------------- map / list view state ---------------- */

  const VIEW_KEY = "sma.view";       // localStorage key remembering Map | List
  const MAP_COL_W = 320;             // horizontal pitch between tree columns
  const MAP_ROW_H = 54;              // vertical pitch between leaf rows
  const MAP_NODE_H = 44;             // node box height
  const MAP_COLLAPSE_MIN = 25;         // trees above this size collapse deep subtrees
  const MAP_COLLAPSE_AGGRESSIVE = 30;  // trees above this size start as root + direct children
  const MAP_COLLAPSE_DEPTH = 3;        // depth at which deep subtrees collapse (25-30 node trees)
  const NS = "http://www.w3.org/2000/svg";
  let lastData = null;               // most recent analyze payload (toggle re-renders from it)
  let measurer = null;               // shared canvas 2d context used to measure SVG text
  let fontFamily = null;

  function currentView() {
    try {
      return localStorage.getItem(VIEW_KEY) === "map" ? "map" : "list";
    } catch {
      return "list";
    }
  }

  function measureText(text, weight, size) {
    if (!measurer) measurer = document.createElement("canvas").getContext("2d");
    if (!fontFamily) fontFamily = getComputedStyle(document.body).fontFamily;
    measurer.font = `${weight} ${size}px ${fontFamily}`;
    return measurer.measureText(text).width;
  }

  function truncateTo(text, maxWidth, weight, size) {
    if (measureText(text, weight, size) <= maxWidth) return text;
    let out = text;
    while (out.length > 1 && measureText(out + "\u2026", weight, size) > maxWidth) {
      out = out.slice(0, -1);
    }
    return out + "\u2026";
  }

  function svgEl(tag, attrs, text) {
    const node = document.createElementNS(NS, tag);
    if (attrs) {
      for (const [key, value] of Object.entries(attrs)) {
        if (value !== undefined && value !== null) node.setAttribute(key, String(value));
      }
    }
    if (text !== undefined) node.textContent = text;
    return node;
  }

  /* Paradigm bucketing: forms are classified from their FIRST feature
     analysis (the API joins analyses with " · "). Rules are an explicit,
     ordered table — first matching rule wins. The clitics rule also checks
     proclitic pronouns ("me hago" carries plain "present indicative"
     features in the real data, so the form's leading pronoun is the only
     reliable marker). */
  const VERB_RULES = [
    { b: "clitics", o: 0, p: ["me ", "te ", "se ", "nos ", "os "], any: ["clitic"] },
    { b: "clitics", o: 0, any: ["object"] },
    { b: "clitics", o: 0, any: ["reflexive"] },
    { b: "nonfinite", o: 0, any: ["infinitive"] },
    { b: "nonfinite", o: 1, any: ["gerund"] },
    { b: "nonfinite", o: 2, any: ["participle"] },
    { b: "indicative", o: 0, any: ["present indicative"] },
    { b: "indicative", o: 1, any: ["imperfect indicative"] },
    { b: "indicative", o: 2, any: ["preterite indicative"] },
    { b: "indicative", o: 3, any: ["future indicative"] },
    { b: "indicative", o: 4, any: ["conditional indicative"] },
    { b: "subjunctive", o: 0, any: ["present subjunctive"] },
    { b: "subjunctive", o: 2, all: ["imperfect subjunctive", "(-se)"] },
    { b: "subjunctive", o: 1, any: ["imperfect subjunctive"] },
    { b: "subjunctive", o: 3, any: ["future subjunctive"] },
    { b: "indicative", o: 0, any: ["present"] },
    { b: "indicative", o: 2, any: ["preterite"] },
    { b: "imperative", o: 1, all: ["imperative", "(negative)"] },
    { b: "imperative", o: 0, any: ["imperative"] },
    { b: "other", o: 0 },
  ];
  const VERB_SECTION_ORDER = ["nonfinite", "indicative", "subjunctive", "imperative", "clitics", "other"];
  const VERB_SECTION_LABELS = {
    nonfinite: "Non-finite",
    indicative: "Indicative",
    subjunctive: "Subjunctive",
    imperative: "Imperative",
    clitics: "With clitics",
    other: "Other",
  };

  const NOUN_RULES = [
    { b: "diminutive", o: 0, any: ["diminutive"] },
    { b: "augmentative", o: 0, any: ["augmentative"] },
    { b: "superlative", o: 0, any: ["superlative"] },
    { b: "comparative", o: 0, any: ["comparative"] },
    { b: "femplural", o: 0, all: ["feminine", "plural"] },
    { b: "plural", o: 0, any: ["plural"] },
    { b: "feminine", o: 0, any: ["feminine"] },
    { b: "base", o: 0, any: ["singular", "masculine", "canonical", "citation form"] },
    { b: "other", o: 0 },
  ];
  const NOUN_SECTION_ORDER = ["base", "diminutive", "augmentative", "superlative", "comparative", "feminine", "plural", "femplural", "other"];
  const NOUN_SECTION_LABELS = {
    base: "Base",
    diminutive: "Diminutive",
    augmentative: "Augmentative",
    superlative: "Superlative",
    comparative: "Comparative",
    feminine: "Feminine",
    plural: "Plural",
    femplural: "Feminine plural",
    other: "Other",
  };

  /* Adverbs inflect for the absolute superlative ("rapidísimamente"), a
     comparative ("mejor", "peor" under bien/mal) and occasionally a
     diminutive ("rapidito", "prontito") or augmentative. Base is the
     citation form or anything featureless; the -ísimamente shape is a
     fallback for absolute superlatives whose features do not spell out
     "superlative" (the citation form is protected by the earlier base rule
     — "malísimamente" is its own lemma and must stay in Base). */
  const ADV_RULES = [
    { b: "base", o: 0, any: ["citation form"] },
    { b: "diminutive", o: 1, any: ["diminutive"] },
    { b: "augmentative", o: 1, any: ["augmentative"] },
    { b: "superlative", o: 2, any: ["superlative"] },
    { b: "superlative", o: 2, suf: ["\u00edsimamente"] },
    { b: "comparative", o: 2, any: ["comparative"] },
    { b: "other", o: 3 },
  ];
  const ADV_SECTION_ORDER = ["base", "diminutive", "augmentative", "superlative", "comparative", "other"];
  const ADV_SECTION_LABELS = {
    base: "Base",
    diminutive: "Diminutive",
    augmentative: "Augmentative",
    superlative: "Superlative",
    comparative: "Comparative",
    other: "Other",
  };

  /* POS -> paradigm table. The noun table doubles for adjectives, proper
     names, pronouns, determiners, articles and numerals (they all inflect
     for gender/number). Every other POS falls through to the default single
     unlabelled group: its only bucket is "other", which the renderer leaves
     heading-less when it stands alone. */
  const VERB_TABLE = { rules: VERB_RULES, order: VERB_SECTION_ORDER, labels: VERB_SECTION_LABELS };
  const NOUN_TABLE = { rules: NOUN_RULES, order: NOUN_SECTION_ORDER, labels: NOUN_SECTION_LABELS };
  const ADV_TABLE = { rules: ADV_RULES, order: ADV_SECTION_ORDER, labels: ADV_SECTION_LABELS };
  const DEFAULT_TABLE = { rules: [{ b: "other", o: 0 }], order: ["other"], labels: { other: "Other" } };
  const POS_TABLE = {
    verb: VERB_TABLE,
    noun: NOUN_TABLE,
    adj: NOUN_TABLE,
    name: NOUN_TABLE,
    pron: NOUN_TABLE,
    det: NOUN_TABLE,
    article: NOUN_TABLE,
    num: NOUN_TABLE,
    adv: ADV_TABLE,
  };

  function paradigmTableFor(pos) {
    return POS_TABLE[pos] || DEFAULT_TABLE;
  }

  /* ---------------- search dropdown ---------------- */

  function closeDropdown() {
    listbox.hidden = true;
    listbox.replaceChildren();
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    kbdHint.hidden = true;
    active = -1;
    results = [];
  }

  function openDropdown() {
    listbox.hidden = false;
    input.setAttribute("aria-expanded", "true");
    kbdHint.hidden = false;
  }

  function setActive(index) {
    if (!results.length) return;
    active = (index + results.length) % results.length;
    const options = listbox.children;
    for (let i = 0; i < options.length; i++) {
      const row = options[i].firstElementChild;
      row.classList.toggle("active", i === active);
      options[i].setAttribute("aria-selected", String(i === active));
    }
    input.setAttribute("aria-activedescendant", `opt-${active}`);
    options[active].firstElementChild.scrollIntoView({ block: "nearest" });
  }

  function optionEl(row, index) {
    const li = document.createElement("li");
    li.id = `opt-${index}`;
    li.className = "option";
    li.setAttribute("role", "option");
    li.setAttribute("aria-selected", "false");

    const rowEl = document.createElement("div");
    rowEl.className = "option-row";
    li.append(rowEl);

    const form = document.createElement("span");
    form.className = "row-form";
    form.textContent = row.form;
    rowEl.append(form);

    /* The parenthesised qualifier exists to name a DIFFERENT lemma. When it
       equals the surface form ("hecho (hecho)") it is noise — the POS chip
       and gloss already distinguish those rows — so the cell renders empty.
       The span is still appended so the grid's shared column 2 stays
       aligned across rows. */
    const q = document.createElement("span");
    q.className = "row-qualifier";
    q.textContent = row.qualifier && row.qualifier !== row.form ? `(${row.qualifier})` : "";
    rowEl.append(q);

    const chip = document.createElement("span");
    chip.className = `pos-chip ${row.pos}`;
    chip.textContent = row.pos;
    rowEl.append(chip);

    const gloss = document.createElement("span");
    gloss.className = "row-gloss";
    gloss.textContent = row.gloss;
    rowEl.append(gloss);

    li.addEventListener("mousemove", () => setActive(index));
    li.addEventListener("click", () => selectResult(index));
    return li;
  }

  function renderDropdown(items) {
    results = items;
    listbox.replaceChildren();
    if (!items.length) {
      closeDropdown();
      statusEl.textContent = "No matches";
      return;
    }
    statusEl.textContent = items.length === 1 ? "1 result" : `${items.length} results`;
    for (let i = 0; i < items.length; i++) listbox.append(optionEl(items[i], i));
    openDropdown();
    // Keep a previously highlighted row if it survived the re-render,
    // otherwise highlight the first result so Enter works immediately.
    if (active >= 0 && active < items.length) {
      setActive(active);
    } else {
      active = -1;
      setActive(0);
    }
  }

  async function runSearch(query) {
    if (searchController) searchController.abort();
    const controller = new AbortController();
    searchController = controller;
    try {
      const res = await fetch(
        `/api/search?q=${encodeURIComponent(query)}&limit=${SEARCH_LIMIT}`,
        { signal: controller.signal },
      );
      const data = await res.json();
      if (controller.signal.aborted) return;
      renderDropdown(Array.isArray(data.results) ? data.results : []);
    } catch (err) {
      if (err.name === "AbortError") return;
      statusEl.textContent = "Search failed — is the server running?";
    }
  }

  input.addEventListener("input", () => {
    const query = input.value.trim();
    clearTimeout(debounceTimer);
    // Single characters hit a ~250k-row range scan; never fire below 2 chars.
    if (query.length < 2) {
      closeDropdown();
      statusEl.textContent = "";
      return;
    }
    debounceTimer = setTimeout(() => runSearch(query), DEBOUNCE_MS);
  });

  input.addEventListener("keydown", (e) => {
    if (!listbox.hidden && results.length) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive(active + 1);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive(active - 1);
        return;
      }
    }
    if (e.key === "Enter") {
      // No free-text submit: Enter only ever selects a highlighted row.
      // Selection works even if the dropdown was closed in the meantime
      // (e.g. transient blur), so a highlighted choice is never lost.
      e.preventDefault();
      if (active >= 0 && results[active]) selectResult(active);
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeDropdown();
    }
  });

  const searchWrap = document.querySelector(".combobox-wrap");

  input.addEventListener("blur", () => {
    // Defer so a click on an option still registers before the dropdown
    // closes; only close when focus truly leaves the whole widget.
    setTimeout(() => {
      if (!searchWrap.contains(document.activeElement)) closeDropdown();
    }, 120);
  });

  document.addEventListener("click", (e) => {
    if (!listbox.hidden && !listbox.contains(e.target) && e.target !== input) {
      closeDropdown();
    }
  });

  async function selectResult(index) {
    const row = results[index];
    if (!row) return;
    closeDropdown();
    input.value = row.form;
    await openAnalysis(row.id);
  }

  /* ---------------- analysis view ---------------- */

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function formCount(group) {
    return group.members.reduce((sum, m) => sum + m.forms.length, 0);
  }

  function memberKey(member) {
    return `${member.lemma}\u0000${member.forms.length}`;
  }

  /* tooltips must not break at hyphens inside feature labels ("first-person"):
     U+2011 keeps the visual hyphen but prevents a mid-word line break, so the
     tooltip stays within two lines and fits the chip-grid gap. */
  function tooltipText(features) {
    return features.replaceAll("-", "\u2011");
  }

  function chipEl(form) {
    const chip = el("span", "form-chip" + (form.is_lemma ? " citation" : ""), form.form);
    chip.title = tooltipText(form.features);
    chip.setAttribute("data-features", tooltipText(form.features));
    chip.tabIndex = 0;
    return chip;
  }

  function ruleMatches(rule, feature, form) {
    if (rule.p && rule.p.some((pfx) => form.startsWith(pfx))) return true;
    if (rule.suf && !rule.suf.some((s) => form.endsWith(s))) return false;
    if (rule.any && !rule.any.some((s) => feature.includes(s))) return false;
    if (rule.all && !rule.all.every((s) => feature.includes(s))) return false;
    return true;
  }

  /* Dash-only or blank forms are kaikki placeholders ("no form exists");
     the pipeline filters them at the source, but the UI must never render
     them as chips. */
  const PLACEHOLDER_FORMS = new Set(["-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"]);

  function isPlaceholder(form) {
    return !form || !form.trim() || PLACEHOLDER_FORMS.has(form);
  }

  function classifyForm(formView, table) {
    const rules = table.rules;
    const feats = formView.features.split(" \u00b7 ").filter(Boolean);
    const form = formView.form.toLowerCase();

    // Clitics are a verb-only absolute override: any analysis mentioning a
    // clitic, object or reflexive — or a proclitic pronoun on the surface
    // form — wins over every grammatical bucket. Checked across ALL analyses
    // because the data lists the plain analysis first for some reflexive
    // forms ('hacerse' -> "infinitive" first, "reflexive" later). Non-verb
    // tables have no clitics bucket, so the override is gated to verbs to
    // avoid silently dropping such forms into a bucket nothing renders.
    if (table === VERB_TABLE) {
      for (const f of feats) {
        const fl = f.toLowerCase();
        if (fl.includes("clitic") || fl.includes("object") || fl.includes("reflexive")) {
          return { b: "clitics", o: 0, feat: fl };
        }
      }
      if (["me ", "te ", "se ", "nos ", "os "].some((pfx) => form.startsWith(pfx))) {
        return { b: "clitics", o: 0, feat: "" };
      }
    }

    // Best analysis wins: score every analysis against the rule table and
    // take the highest-priority match. The table is ordered so the mood
    // precedence non-finite > indicative > subjunctive > imperative > other
    // equals the rule index order — a form that is both present subjunctive
    // and formal imperative files under Subjunctive no matter which analysis
    // the source lists first.
    let bestIdx = -1;
    let bestRule = null;
    let bestFeat = "";
    for (const f of feats) {
      const fl = f.toLowerCase();
      for (let i = 0; i < rules.length; i++) {
        if (ruleMatches(rules[i], fl, form)) {
          if (bestIdx === -1 || i < bestIdx) {
            bestIdx = i;
            bestRule = rules[i];
            bestFeat = fl;
          }
          break;
        }
      }
    }
    if (!bestRule) return { b: "other", o: 0, feat: bestFeat };
    return { b: bestRule.b, o: bestRule.o, feat: bestFeat };
  }

  /* Gender-then-number where any analysis exposes gender (participles,
     nouns and adjectives): masc sg, fem sg, masc pl, fem pl. Otherwise
     person order (1sg, 2sg, 3sg, 1pl, 2pl, 3pl), else alphabetical.
     The analysis that WON the bucket is checked first ('hagan' wins via its
     present-subjunctive analysis, so it ranks 3rd not 2nd despite the
     imperative "2nd 3rd plural" listed first); the remaining analyses are
     scanned as a fallback ('hecho' is "participle, past" first and
     "participle, singular, masculine, past" second — the gender comes from
     the second one). */
  function sortRankOf(formView, winningFeat) {
    const feats = formView.features.split(" \u00b7 ").filter(Boolean).map((f) => f.toLowerCase());
    const candidates = winningFeat ? [winningFeat].concat(feats) : feats;
    for (const fl of candidates) {
      if (fl.includes("feminine") || fl.includes("masculine")) {
        const g = fl.includes("feminine") ? 2 : 1;
        return g - 1 + (fl.includes("plural") ? 2 : 0);
      }
    }
    for (const fl of candidates) {
      let num = 0;
      if (fl.includes("1st")) num = 1;
      else if (fl.includes("2nd")) num = 2;
      else if (fl.includes("3rd")) num = 3;
      if (num) return num + (fl.includes("plural") ? 3 : 0);
    }
    return 7;
  }

  function formsContainer(member, table) {
    const wrap = el("div", "member-forms");
    const key = memberKey(member);
    const forms = member.forms.filter((f) => !isPlaceholder(f.form));
    const many = forms.length > COLLAPSE_THRESHOLD;
    const order = table.order;
    const labels = table.labels;

    function build() {
      // recomputed per build: the toggles mutate the sets and re-render
      const collapsedPreview = many && !expandedMembers.has(key);
      const buckets = new Map();
      for (const f of forms) {
        const c = classifyForm(f, table);
        const arr = buckets.get(c.b) || [];
        arr.push({ f, c });
        buckets.set(c.b, arr);
      }
      // A single Other bucket carries no information — the chips render as
      // one unlabelled group (no heading). Any other single bucket (Base,
      // Feminine, ...) keeps its heading: it tells the user what they are
      // looking at.
      const singleOther = buckets.size === 1 && buckets.has("other");
      for (const arr of buckets.values()) {
        arr.sort(
          (a, b) =>
            (b.f.is_lemma ? 1 : 0) - (a.f.is_lemma ? 1 : 0) || // citation form first
            a.c.o - b.c.o ||
            sortRankOf(a.f, a.c.feat) - sortRankOf(b.f, b.c.feat) ||
            (a.f.form < b.f.form ? -1 : 1),
        );
      }

      const frag = document.createDocumentFragment();
      for (const b of order) {
        let items = buckets.get(b);
        if (!items || !items.length) continue;
        if (collapsedPreview) {
          if (b === "nonfinite") {
            /* all non-finite forms */
          } else if (b === "indicative") {
            const present = items.filter((it) => it.c.o === 0);
            if (!present.length) continue;
            items = present;
          } else {
            continue;
          }
        }

        const noHead = singleOther && b === "other";
        const section = el("div", "paradigm-section" + (noHead ? " unlabelled" : ""));
        if (!noHead) {
          section.append(el("h4", "paradigm-head", labels[b]));
        }
        const grid = el("div", "forms-grid");
        const shown = items;
        if (b === "clitics" && !expandedClitics.has(key)) {
          const slice = shown.slice(0, CLITIC_PREVIEW);
          const sfrag = document.createDocumentFragment();
          for (const it of slice) sfrag.append(chipEl(it.f));
          grid.append(sfrag);
          const toggle = el("button", "show-all", `Show ${shown.length} clitic forms`);
          toggle.type = "button";
          toggle.addEventListener("click", () => {
            expandedClitics.add(key);
            wrap.replaceChildren(build());
          });
          section.append(grid);
          section.append(toggle);
        } else {
          const sfrag = document.createDocumentFragment();
          for (const it of shown) sfrag.append(chipEl(it.f));
          grid.append(sfrag);
          section.append(grid);
        }
        frag.append(section);
      }

      if (collapsedPreview) {
        const toggle = el("button", "show-all", `Show all ${forms.length} forms`);
        toggle.type = "button";
        toggle.addEventListener("click", () => {
          expandedMembers.add(key);
          wrap.replaceChildren(build());
        });
        frag.append(toggle);
      }
      return frag;
    }

    wrap.append(build());
    return wrap;
  }

  function memberCard(member, pos) {
    const card = el("article", "member-card" + (member.is_head ? " is-head" : ""));
    const head = el("div", "member-head");
    head.append(el("h3", "member-lemma", member.lemma));
    if (member.is_head) {
      head.append(el("span", "head-badge", "head"));
    } else if (member.relation_label && member.relation_label !== "root") {
      head.append(el("span", "relation-chip", member.relation_label));
    }
    card.append(head);
    card.append(el("p", "member-gloss", member.gloss));
    card.append(formsContainer(member, paradigmTableFor(pos)));
    return card;
  }

  function posSection(group, index) {
    const section = el("section", "pos-section");
    section.id = `pos-${index}`;
    section.setAttribute("aria-labelledby", `pos-head-${index}`);

    const heading = el("div", "pos-section-head");
    const h2 = el("h2", null, group.pos_label);
    h2.id = `pos-head-${index}`;
    heading.append(h2);
    // "1 lemma · 2 forms" is noise when the card right below shows those
    // forms in full; the badge earns its place for multi-member groups or
    // once a single member has more than a handful of forms.
    const totalForms = formCount(group);
    if (group.members.length > 1 || totalForms >= BADGE_MIN_FORMS) {
      heading.append(
        el(
          "span",
          "count-badge",
          `${group.members.length} lemma${group.members.length === 1 ? "" : "s"} \u00b7 ${totalForms} forms`,
        ),
      );
    }
    section.append(heading);

    const many = group.members.length > SECTION_COLLAPSE;
    const expanded = expandedSections.has(group.pos);
    const shown = many && !expanded ? group.members.slice(0, SECTION_COLLAPSE) : group.members;
    const frag = document.createDocumentFragment();
    for (const member of shown) frag.append(memberCard(member, group.pos));
    section.append(frag);

    if (many && !expanded) {
      const toggle = el("button", "show-all", `Show all ${group.members.length} lemmas`);
      toggle.type = "button";
      toggle.addEventListener("click", () => {
        expandedSections.add(group.pos);
        toggle.remove();
        for (const card of section.querySelectorAll(".member-card")) card.remove();
        const frag2 = document.createDocumentFragment();
        for (const member of group.members) frag2.append(memberCard(member, group.pos));
        section.append(frag2);
      });
      section.append(toggle);
    }
    return section;
  }

  /* ---------------- Map | List toggle ---------------- */

  function viewToggle() {
    const wrap = el("div", "view-toggle");
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", "Analysis view");
    const view = currentView();
    for (const v of ["map", "list"]) {
      const btn = el("button", "view-btn" + (view === v ? " active" : ""), v === "map" ? "Map" : "List");
      btn.type = "button";
      btn.dataset.view = v;
      btn.setAttribute("aria-pressed", String(view === v));
      btn.addEventListener("click", () => {
        if (currentView() === v) return;
        try {
          localStorage.setItem(VIEW_KEY, v);
        } catch {
          /* storage unavailable (private mode): the toggle still works for the session */
        }
        if (lastData) renderAnalysis(lastData);
      });
      wrap.append(btn);
    }
    return wrap;
  }

  /* ---------------- ancestry ribbon ---------------- */

  /* descent modes the backend can attach to an ancestry step; each one
     styles the arrow that LEAVES that step towards the next newer word */
  const RIBBON_LABELS = {
    inherited: "inherited",
    borrowed: "borrowed",
    derived: "derived",
  };

  function arrowSvg(mode) {
    /* wide enough that the dash/dot patterns repeat at least twice */
    const svg = svgEl("svg", {
      class: "anc-arrow mode-" + (mode || "inherited"),
      viewBox: "0 0 46 12",
      width: 46,
      height: 12,
      "aria-hidden": "true",
    });
    svg.append(svgEl("line", { x1: 1, y1: 6, x2: 34, y2: 6 }));
    svg.append(svgEl("polygon", { points: "38,6 31,2 31,10" }));
    return svg;
  }

  function ancestryRibbonView(steps) {
    const wrap = el("section", "ancestry-ribbon");
    wrap.setAttribute("aria-label", "Etymology");
    wrap.append(el("h3", "ribbon-title", "Etymology"));

    /* The frozen contract emits the chain newest-first (the Spanish word,
       then its etymon, then that word's etymon...) while the ribbon reads
       oldest -> newest, so reverse. A backend that already emits oldest
       first starts with a non-Spanish step and is left untouched. */
    const ordered = steps[0] && steps[0].lang === "es" ? steps.slice().reverse() : steps;

    const chain = el("div", "ribbon-chain");
    const modes = new Set();
    const modeOrder = [];
    ordered.forEach((step, i) => {
      if (step.mode && !modes.has(step.mode)) {
        modes.add(step.mode);
        modeOrder.push(step.mode);
      }
      const stepEl = el("div", "anc-step");
      stepEl.append(el("span", "step-lang", step.lang_label || step.lang || ""));
      stepEl.append(el("span", "step-word", step.word));
      if (step.note) stepEl.append(el("span", "step-note", `(${step.note})`));
      chain.append(stepEl);
      if (i < ordered.length - 1) chain.append(arrowSvg(ordered[i].mode));
    });
    wrap.append(chain);

    if (modes.size) {
      const legend = el("div", "anc-legend");
      for (const mode of modeOrder) {
        const item = el("span", "legend-item");
        item.append(arrowSvg(mode));
        item.append(el("span", null, RIBBON_LABELS[mode] || mode));
        legend.append(item);
      }
      wrap.append(legend);
    }
    return wrap;
  }

  /* ---------------- cousins strip ---------------- */

  function cousinsView(cousins) {
    const section = el("section", "cousins-strip");
    section.setAttribute("aria-label", "Etymological cousins");
    const etymon = cousins.shared_etymon || {};
    const title = `Also from ${[etymon.lang_label, etymon.word].filter(Boolean).join(" ")}`;
    section.append(el("h3", "cousins-title", title));
    if (cousins.note) section.append(el("p", "cousins-note", cousins.note));
    const chips = el("div", "cousins-chips");
    for (const member of cousins.members || []) {
      const btn = el("button", "cousin-chip");
      btn.type = "button";
      if (member.gloss) btn.title = member.gloss;
      btn.append(el("span", "cousin-word", member.lemma));
      if (member.path) btn.append(el("span", "cousin-path", member.path));
      btn.addEventListener("click", () => {
        if (member.entry_id) {
          input.value = member.lemma;
          openAnalysis(member.entry_id);
        }
      });
      chips.append(btn);
    }
    section.append(chips);
    return section;
  }

  /* ---------------- family map (hand-rolled inline SVG) ---------------- */

  /* Navigate to a tree node's own analysis by searching its exact lemma and
     picking the row that matches lemma + POS (the tree contract carries no
     entry_id, so the citation-form search is the navigation path). */
  async function openNode(node) {
    const lemma = node.lemma;
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(lemma)}&limit=25`);
      const data = await res.json();
      const rows = Array.isArray(data.results) ? data.results : [];
      const row =
        rows.find((r) => r.form === lemma && r.lemma === lemma && r.pos === node.pos) ||
        rows.find((r) => r.lemma === lemma) ||
        rows.find((r) => r.form === lemma) ||
        null;
      if (!row) {
        statusEl.textContent = `No entry found for ${lemma}.`;
        return;
      }
      input.value = row.form;
      await openAnalysis(row.id);
    } catch {
      statusEl.textContent = "Search failed — is the server running?";
    }
  }

  function familyMapView(tree, selectedLemma, selectedPos) {
    const nodes = tree.nodes || [];
    const byId = new Map();
    const children = new Map();
    const parentOf = new Map();
    let root = null;
    for (const node of nodes) {
      const id = String(node.lemma_id);
      byId.set(id, node);
      if (node.parent_id == null) {
        if (!root) root = node;
        continue;
      }
      const pid = String(node.parent_id);
      parentOf.set(id, pid);
      if (!children.has(pid)) children.set(pid, []);
      children.get(pid).push(node);
    }
    if (!root && nodes.length) root = nodes[0];
    const rootId = root ? String(root.lemma_id) : null;

    /* depth: trust the backend, fall back to a chain walk */
    const depthOf = new Map();
    for (const node of nodes) {
      if (node.depth != null) depthOf.set(String(node.lemma_id), node.depth);
    }
    for (const node of nodes) {
      const id = String(node.lemma_id);
      if (depthOf.has(id)) continue;
      let depth = 0;
      let cur = id;
      while (parentOf.has(cur)) {
        cur = parentOf.get(cur);
        depth += 1;
      }
      depthOf.set(id, depth);
    }

    /* Subtrees collapse behind +N badges, opened on click. Trees over the
       aggressive threshold start as the root plus its direct children only,
       so a very large family is never a wall of unreadable nodes; 25-30 node
       trees collapse the subtrees below depth 2 instead. */
    const collapsed = new Set();
    const aggressive = nodes.length > MAP_COLLAPSE_AGGRESSIVE;
    if (nodes.length > MAP_COLLAPSE_MIN) {
      for (const node of nodes) {
        const id = String(node.lemma_id);
        const depth = depthOf.get(id);
        if (aggressive) {
          if (depth === 1 && (children.get(id) || []).length) collapsed.add(id);
        } else if (depth === MAP_COLLAPSE_DEPTH - 1) {
          const kids = children.get(id) || [];
          if (kids.some((k) => depthOf.get(String(k.lemma_id)) >= MAP_COLLAPSE_DEPTH)) {
            collapsed.add(id);
          }
        }
      }
    }

    function isHidden(node) {
      let cur = String(node.lemma_id);
      while (parentOf.has(cur)) {
        cur = parentOf.get(cur);
        if (collapsed.has(cur)) return true;
      }
      return false;
    }

    function buildSvg() {
      const visible = nodes.filter((n) => !isHidden(n));
      if (!visible.length) return svgEl("svg", { class: "map-svg", width: 240, height: 80, viewBox: "0 0 240 80" });

      function posChipWidth(pos) {
        return Math.max(measureText((pos || "").toUpperCase(), 700, 10) + 20, 34);
      }

      /* node box widths from real text measurement (canvas), capped so a
         column always leaves room for the edge and its label */
      const widthOf = new Map();
      for (const node of visible) {
        const lemma = node.lemma || "";
        const pos = node.pos || "";
        const chipW = posChipWidth(pos);
        const countW = measureText(String(node.form_count ?? 0), 600, 11) + 16;
        const lemmaW = measureText(lemma, 700, 14);
        const w = Math.ceil(lemmaW + chipW + countW + 30);
        widthOf.set(String(node.lemma_id), Math.max(100, Math.min(w, 200)));
      }

      /* tidy layout: every leaf owns a row; a parent sits at the mean of
         its children's rows (left-to-right tree, root at the left) */
      let nextRow = 0;
      const rowY = new Map();
      function assignY(id) {
        const kids = (children.get(id) || []).filter((k) => !isHidden(k));
        if (!kids.length) {
          const y = nextRow * MAP_ROW_H;
          nextRow += 1;
          rowY.set(id, y);
          return y;
        }
        const ys = kids.map((k) => assignY(String(k.lemma_id)));
        const y = (ys[0] + ys[ys.length - 1]) / 2;
        rowY.set(id, y);
        return y;
      }
      assignY(rootId);

      const xOf = (id) => (depthOf.get(id) ?? 0) * MAP_COL_W + 30;
      const nodeX = new Map();
      for (const node of visible) nodeX.set(String(node.lemma_id), xOf(String(node.lemma_id)));

      /* canvas sized to the content so small families do not leave a dead
         scroll strip; wide/deep families scroll horizontally in .map-wrap */
      let rightEdge = 60;
      for (const node of visible) {
        rightEdge = Math.max(rightEdge, nodeX.get(String(node.lemma_id)) + widthOf.get(String(node.lemma_id)));
      }
      const svgW = Math.max(260, rightEdge + 40);
      const svgH = Math.max(120, nextRow * MAP_ROW_H + 24);

      const svg = svgEl("svg", {
        class: "map-svg",
        role: "tree",
        width: svgW,
        height: svgH,
        "aria-label": `Derivation family of ${root ? root.lemma : ""}: ${visible.length} of ${nodes.length} members shown; ${selectedLemma} is selected. Use arrow keys to move between words and Enter to open one.`,
        viewBox: `0 0 ${svgW} ${svgH}`,
      });

      /* node boxes are obstacles for labels: a label that would land on top
         of any node slides back along its edge until it clears */
      const nodeRects = [];
      for (const node of visible) {
        const nid = String(node.lemma_id);
        nodeRects.push({ x: nodeX.get(nid), y: rowY.get(nid), w: widthOf.get(nid), h: MAP_NODE_H });
      }
      function labelBoxClear(x, y, w) {
        const lx0 = x - w / 2 - 2;
        const lx1 = x + w / 2 + 2;
        const ly0 = y - 11;
        const ly1 = y + 2;
        for (const r of nodeRects) {
          if (lx0 < r.x + r.w && lx1 > r.x && ly0 < r.y + r.h && ly1 > r.y) return false;
        }
        return true;
      }

      /* edges (cubic bezier elbows) + labels */
      const labelData = [];
      for (const node of visible) {
        const id = String(node.lemma_id);
        if (!parentOf.has(id)) continue;
        const pid = parentOf.get(id);
        const x0 = nodeX.get(pid) + widthOf.get(pid) + 4;
        const y0 = rowY.get(pid) + MAP_NODE_H / 2;
        const x1 = nodeX.get(id) - 4;
        const y1 = rowY.get(id) + MAP_NODE_H / 2;
        const mx = (x0 + x1) / 2;
        const my = (y0 + y1) / 2;
        svg.append(
          svgEl("path", {
            class: "map-edge",
            d: `M ${x0} ${y0} C ${mx} ${y0}, ${mx} ${y1}, ${x1} ${y1}`,
            "data-from": pid,
            "data-to": id,
          }),
        );
        const run = x1 - x0;
        const rawLabel = node.label || "";
        if (rawLabel && rawLabel !== "root" && run > 46) {
          /* stagger the label along the edge by the child's index within its
             parent (30%-85%) so a fan spreads its labels horizontally instead
             of stacking them into a column */
          const kids = (children.get(pid) || []).filter((k) => !isHidden(k));
          const idx = kids.findIndex((k) => String(k.lemma_id) === id);
          const frac = kids.length > 1 ? 0.3 + 0.55 * (idx / (kids.length - 1)) : 0.62;
          /* long derivations truncate at a sane cap with an ellipsis; the
             full text rides in a title so hover still gives it */
          const maxW = Math.min(run - 14, 150);
          const text = measureText(rawLabel, 600, 11) > maxW ? truncateTo(rawLabel, maxW, 600, 11) : rawLabel;
          const w = measureText(text, 600, 11) + 8;
          const y = my + 2;
          let x = x0 + run * frac;
          if (!labelBoxClear(x, y, w)) {
            let cleared = false;
            for (let f = frac - 0.07; f >= 0.2 && !cleared; f -= 0.07) {
              x = x0 + run * f;
              if (labelBoxClear(x, y, w)) cleared = true;
            }
            if (!cleared) continue; // drop — the hover path reveals the relation
          }
          labelData.push({
            order: nodes.indexOf(node),
            parent: pid,
            nodeId: id,
            label: text,
            full: rawLabel,
            x,
            y,
            w,
          });
        }
      }
      /* repeated identical labels on sibling edges render once, on the middle
         edge of the bundle (the relation is the same for all of them) */
      const byParentLabel = new Map();
      for (const ld of labelData) {
        const key = `${ld.parent}\u0000${ld.label}`;
        if (!byParentLabel.has(key)) byParentLabel.set(key, []);
        byParentLabel.get(key).push(ld);
      }
      const deduped = [];
      for (const group of byParentLabel.values()) {
        if (group.length === 1) deduped.push(group[0]);
        else deduped.push(group[Math.floor((group.length - 1) / 2)]);
      }
      /* collision backstop: when two labels still overlap after staggering,
         keep the one that comes first in tree order */
      const keptLabels = [];
      for (const ld of deduped) {
        let collides = false;
        for (const other of keptLabels) {
          if (Math.abs(ld.x - other.x) < (ld.w + other.w) / 2 && Math.abs(ld.y - other.y) < 14) {
            collides = true;
            break;
          }
        }
        if (!collides) keptLabels.push(ld);
      }
      for (const ld of keptLabels) {
        const t = svgEl(
          "text",
          { class: "map-edge-label", "data-to": ld.nodeId, x: ld.x, y: ld.y, "text-anchor": "middle" },
          ld.label,
        );
        if (ld.full && ld.full !== ld.label) t.append(svgEl("title", {}, ld.full));
        svg.append(t);
      }

      /* nodes */
      let focusId = null;
      for (const node of visible) {
        const id = String(node.lemma_id);
        const x = nodeX.get(id);
        const y = rowY.get(id);
        const w = widthOf.get(id);
        const isRoot = id === rootId;
        const isSelected = !!node.is_selected;
        if (isSelected) focusId = id;
        const g = svgEl("g", {
          class: "map-node" + (isRoot ? " is-root" : "") + (isSelected ? " is-selected" : ""),
          role: "treeitem",
          tabindex: isSelected ? "0" : "-1",
          "aria-level": String((depthOf.get(id) ?? 0) + 1),
          "aria-selected": String(isSelected),
          "data-id": id,
        });
        if (collapsed.has(id)) g.setAttribute("aria-expanded", "false");
        g.append(
          svgEl(
            "title",
            {},
            `${node.lemma} — ${node.gloss || "no gloss"}\u00b7 ${node.form_count ?? 0} form${node.form_count === 1 ? "" : "s"}`,
          ),
        );
        g.append(svgEl("rect", { class: "box", x, y, width: w, height: MAP_NODE_H, rx: 8 }));
        const chipW = posChipWidth(node.pos);
        const countW = measureText(String(node.form_count ?? 0), 600, 11) + 16;
        const maxLemmaW = w - chipW - countW - 26;
        g.append(
          svgEl(
            "text",
            { class: "map-node-lemma", x: x + 13, y: y + MAP_NODE_H / 2 + 5 },
            truncateTo(node.lemma || "", maxLemmaW, 700, 14),
          ),
        );
        const countX = x + w - chipW - countW - 4;
        g.append(
          svgEl("text", { class: "map-node-count", x: countX + 6, y: y + MAP_NODE_H / 2 + 4 }, String(node.form_count ?? 0)),
        );
        const chip = svgEl("g", { class: "map-pos-chip " + (node.pos || "other") });
        chip.append(svgEl("rect", { x: x + w - chipW, y: y + 12, width: chipW, height: 20, rx: 10 }));
        chip.append(svgEl("text", { x: x + w - chipW / 2, y: y + 26, "text-anchor": "middle" }, (node.pos || "").toUpperCase()));
        g.append(chip);
        svg.append(g);
      }

      /* +N collapse badges (topmost so they stay clickable) */
      if (collapsed.size) {
        const hiddenCount = new Map();
        for (const node of nodes) {
          if (!isHidden(node)) continue;
          let cur = String(node.lemma_id);
          while (parentOf.has(cur)) {
            const parentId = parentOf.get(cur);
            if (collapsed.has(parentId)) {
              hiddenCount.set(parentId, (hiddenCount.get(parentId) || 0) + 1);
              break;
            }
            cur = parentId;
          }
        }
        for (const [id, count] of hiddenCount) {
          const node = byId.get(id);
          const x = nodeX.get(id) + widthOf.get(id) + 10;
          const y = rowY.get(id) + MAP_NODE_H / 2;
          const badge = svgEl("g", {
            class: "map-collapse-badge",
            role: "button",
            tabindex: "0",
            "aria-label": `Expand ${count} hidden descendant${count === 1 ? "" : "s"} of ${node.lemma}`,
            "data-id": id,
          });
          badge.append(svgEl("circle", { cx: x, cy: y, r: 11 }));
          badge.append(svgEl("text", { x, y: y + 4, "text-anchor": "middle" }, `+${count}`));
          badge.addEventListener("click", () => {
            collapsed.delete(id);
            render();
          });
          badge.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              collapsed.delete(id);
              render();
            }
          });
          svg.append(badge);
        }
      }

      /* ---- interaction: hover/focus highlights the path to the root ---- */
      function clearHighlight() {
        for (const g of svg.querySelectorAll(".map-node.is-path, .map-node.is-hovered")) {
          g.classList.remove("is-path", "is-hovered");
        }
        for (const path of svg.querySelectorAll(".map-edge.is-path")) path.classList.remove("is-path");
        for (const label of svg.querySelectorAll(".map-edge-label.is-path")) label.classList.remove("is-path");
      }

      function highlightPath(g) {
        clearHighlight();
        const chain = new Set();
        let cur = g.dataset.id;
        while (cur && byId.has(cur)) {
          chain.add(cur);
          g.classList.add("is-hovered");
          if (parentOf.has(cur)) cur = parentOf.get(cur);
          else break;
        }
        for (const cid of chain) {
          const nodeEl = svg.querySelector(`.map-node[data-id="${cid}"]`);
          if (nodeEl) nodeEl.classList.add("is-path");
        }
        for (const path of svg.querySelectorAll(".map-edge")) {
          if (chain.has(path.dataset.to)) path.classList.add("is-path");
        }
        for (const label of svg.querySelectorAll(".map-edge-label")) {
          if (chain.has(label.dataset.to)) label.classList.add("is-path");
        }
      }

      svg.addEventListener("mouseover", (e) => {
        const g = e.target.closest ? e.target.closest(".map-node") : null;
        if (g) highlightPath(g);
      });
      svg.addEventListener("mouseout", (e) => {
        const g = e.target.closest ? e.target.closest(".map-node") : null;
        if (g && g.contains(e.relatedTarget)) return;
        clearHighlight();
      });
      svg.addEventListener("focusin", (e) => {
        const g = e.target.closest ? e.target.closest(".map-node") : null;
        if (g) highlightPath(g);
      });
      svg.addEventListener("focusout", (e) => {
        if (svg.contains(e.relatedTarget)) return;
        clearHighlight();
      });

      svg.addEventListener("click", (e) => {
        /* the badge has its own listener; the delegated handler only opens nodes */
        if (e.target.closest && e.target.closest(".map-collapse-badge")) return;
        const g = e.target.closest ? e.target.closest(".map-node") : null;
        if (!g) return;
        const node = byId.get(g.dataset.id);
        if (!node || node.is_selected) return;
        openNode(node);
      });

      /* ---- keyboard: arrows move between nodes, Enter opens ---- */
      const dfsOrder = [];
      (function collect(id) {
        dfsOrder.push(id);
        for (const kid of children.get(id) || []) {
          if (!isHidden(kid)) collect(String(kid.lemma_id));
        }
      })(rootId);

      function focusNode(id) {
        const g = svg.querySelector(`.map-node[data-id="${id}"]`);
        if (!g) return;
        for (const other of svg.querySelectorAll('.map-node[tabindex="0"]')) other.setAttribute("tabindex", "-1");
        g.setAttribute("tabindex", "0");
        g.focus();
      }

      svg.addEventListener("keydown", (e) => {
        const active = document.activeElement;
        if (!active || !active.closest) return;
        const g = active.closest(".map-node");
        if (!g) return;
        if (["ArrowRight", "ArrowLeft", "ArrowUp", "ArrowDown", "Home"].includes(e.key)) e.preventDefault();
        const id = g.dataset.id;
        const node = byId.get(id);
        const idx = dfsOrder.indexOf(id);
        let next = null;
        switch (e.key) {
          case "ArrowRight": {
            const kid = (children.get(id) || []).find((k) => !isHidden(k));
            if (kid) next = String(kid.lemma_id);
            break;
          }
          case "ArrowLeft":
            if (parentOf.has(id)) next = parentOf.get(id);
            break;
          case "ArrowDown":
            if (idx >= 0 && idx < dfsOrder.length - 1) next = dfsOrder[idx + 1];
            break;
          case "ArrowUp":
            if (idx > 0) next = dfsOrder[idx - 1];
            break;
          case "Home":
            next = rootId;
            break;
          case "Enter":
            if (node && !node.is_selected) openNode(node);
            return;
          default:
            return;
        }
        if (next) focusNode(next);
      });

      return svg;
    }

    const wrap = el("div", "map-wrap");

    /* zoom toolbar: the map renders at natural (readable) size and the
       container scrolls; +/- zoom in place, Fit scales the whole tree into
       view as an explicit user choice */
    const ZOOM_MIN = 0.2;
    const ZOOM_MAX = 2.5;
    const ZOOM_STEP = 0.25;
    let zoom = 1;
    let currentSvg = null;
    let naturalW = 0;
    let naturalH = 0;

    const toolbar = el("div", "map-toolbar");
    toolbar.setAttribute("role", "toolbar");
    toolbar.setAttribute("aria-label", "Map zoom");
    const levelEl = el("span", "zoom-level", "100%");
    levelEl.setAttribute("aria-live", "polite");
    const outBtn = el("button", "zoom-btn", "\u2212");
    outBtn.type = "button";
    outBtn.setAttribute("aria-label", "Zoom out");
    outBtn.title = "Zoom out";
    const inBtn = el("button", "zoom-btn", "+");
    inBtn.type = "button";
    inBtn.setAttribute("aria-label", "Zoom in");
    inBtn.title = "Zoom in";
    const fitBtn = el("button", "zoom-fit", "Fit");
    fitBtn.type = "button";
    fitBtn.title = "Fit the whole tree into view";
    toolbar.append(outBtn, levelEl, inBtn, fitBtn);

    function applyZoom() {
      zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom));
      levelEl.textContent = `${Math.round(zoom * 100)}%`;
      if (currentSvg) currentSvg.style.transform = `scale(${zoom})`;
    }
    outBtn.addEventListener("click", () => {
      zoom -= ZOOM_STEP;
      applyZoom();
    });
    inBtn.addEventListener("click", () => {
      zoom += ZOOM_STEP;
      applyZoom();
    });
    fitBtn.addEventListener("click", () => {
      if (!currentSvg || !naturalW) return;
      const fitScale = Math.min(
        (wrap.clientWidth - 48) / naturalW,
        (wrap.clientHeight - 80) / naturalH,
        1,
      );
      zoom = Math.max(ZOOM_MIN, fitScale);
      applyZoom();
      wrap.scrollLeft = 0;
      wrap.scrollTop = 0;
    });

    let inited = false;
    function render() {
      currentSvg = buildSvg();
      naturalW = currentSvg.viewBox.baseVal.width;
      naturalH = currentSvg.viewBox.baseVal.height;
      currentSvg.style.transform = `scale(${zoom})`;
      wrap.replaceChildren(toolbar, currentSvg);
      if (!inited) {
        /* first paint: the root is at the tree's top-left, so pin the
           scrollport there instead of leaving it wherever the browser lands */
        wrap.scrollLeft = 0;
        wrap.scrollTop = 0;
        inited = true;
      }
    }
    render();
    return wrap;
  }

  function renderAnalysis(data) {
    const { selected, family } = data;
    analysisEl.replaceChildren();
    expandedMembers.clear();
    expandedSections.clear();
    expandedClitics.clear();
    lastData = data;

    /* header card */
    const header = el("article", "entry-card");
    header.dataset.entryId = selected.id;
    header.append(el("h2", "entry-form", selected.form));
    const lemmaLine = el("p", "entry-lemma");
    lemmaLine.append(el("span", "pos-chip " + selected.pos, selected.pos));
    if (selected.lemma !== selected.form) {
      lemmaLine.append(el("span", "entry-lemma-word", selected.lemma));
    }
    header.append(lemmaLine);
    header.append(el("p", "entry-gloss", selected.gloss));
    if (selected.features && selected.features.length) {
      const list = el("ul", "entry-features");
      for (const feat of selected.features) list.append(el("li", null, feat));
      header.append(list);
    }
    analysisEl.append(header);

    /* Map | List toggle — remembered in localStorage; the list stays the
       default until the map proves itself */
    analysisEl.append(viewToggle());

    /* the etymology ribbon sits above whichever family view is active; it
       needs at least two steps to be worth drawing */
    if (data.ancestry && data.ancestry.length >= 2) {
      analysisEl.append(ancestryRibbonView(data.ancestry));
    }

    if (currentView() === "map") {
      if (data.tree && data.tree.nodes && data.tree.nodes.length) {
        analysisEl.append(familyMapView(data.tree, selected.lemma, selected.pos));
      } else {
        analysisEl.append(el("p", "empty-note", "No derivation tree is available for this entry."));
      }
    } else {
      /* sticky mini-nav — skipped when there is only one POS group: a single
         button that scrolls to itself is pure noise */
      let nav = null;
      const navButtons = [];
      if (family.groups.length > 1) {
        nav = el("nav", "pos-nav");
        nav.setAttribute("aria-label", "Parts of speech");
        family.groups.forEach((group, i) => {
          const btn = el("button", null, group.pos_label);
          btn.type = "button";
          btn.addEventListener("click", () => {
            document.getElementById(`pos-${i}`).scrollIntoView({ behavior: "smooth", block: "start" });
          });
          nav.append(btn);
          navButtons.push(btn);
        });
        analysisEl.append(nav);
      }

      /* pos sections */
      const sections = family.groups.map((group, i) => posSection(group, i));
      for (const section of sections) analysisEl.append(section);

      analysisEl.hidden = false;

      /* scrollspy: highlight the nav button of the section currently in view */
      if (nav) {
        const onScroll = () => {
          const offset = nav.offsetHeight + 48;
          let current = 0;
          sections.forEach((section, i) => {
            if (section.getBoundingClientRect().top <= offset) current = i;
          });
          navButtons.forEach((btn, i) => btn.classList.toggle("active", i === current));
        };
        if (scrollspyHandler) window.removeEventListener("scroll", scrollspyHandler);
        scrollspyHandler = onScroll;
        window.addEventListener("scroll", onScroll, { passive: true });
        onScroll();
      }
    }

    if (family.note) analysisEl.append(el("p", "family-note", family.note));

    /* cousins are context, not family: clearly separated and visually
       secondary, and only when the backend found any */
    if (data.cousins) analysisEl.append(cousinsView(data.cousins));

    analysisEl.hidden = false;
  }

  async function openAnalysis(id) {
    analysisEl.hidden = true;
    loadingEl.hidden = false;
    statusEl.textContent = "";
    // The SQLite store can briefly fail while the pipeline rebuilds the DB
    // in place; retry once before surfacing the error to the user.
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await fetch(`/api/analyze?id=${encodeURIComponent(id)}`);
        if (res.status === 404) {
          statusEl.textContent = "That entry is no longer available.";
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderAnalysis(data);
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      } catch (err) {
        if (attempt === 0) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          continue;
        }
        statusEl.textContent = "Analysis failed — is the server running?";
      } finally {
        loadingEl.hidden = true;
      }
    }
  }
})();
