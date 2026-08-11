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

  function renderAnalysis(data) {
    const { selected, family } = data;
    analysisEl.replaceChildren();
    expandedMembers.clear();
    expandedSections.clear();
    expandedClitics.clear();

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

    if (family.note) analysisEl.append(el("p", "family-note", family.note));

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
