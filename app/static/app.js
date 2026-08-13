"use strict";

/* Spanish Morphological Analyser — frontend logic.
   Combobox dropdown (no free-text submit) + family analysis view. */

(() => {
  const input = document.getElementById("search-input");
  const listbox = document.getElementById("search-listbox");
  const statusEl = document.getElementById("search-status");
  const loadingEl = document.getElementById("loading");
  const kbdHint = document.getElementById("kbd-hint");
  const analyzeBtn = document.getElementById("analyze-btn");

  /* dashboard (primary view) */
  const dashboardEl = document.getElementById("dashboard");

  /* Layer 3 (deep views) */
  const layer3El = document.getElementById("layer3");
  const layer3Body = document.getElementById("layer3-body");
  const layer3Title = document.getElementById("layer3-title");
  const layer3Back = document.getElementById("layer3-back");

  /* subviews */
  const favouritesView = document.getElementById("favourites-view");
  const favouritesList = document.getElementById("favourites-list");
  const favouritesEmpty = document.getElementById("favourites-empty");
  const settingsView = document.getElementById("settings-view");
  const errorView = document.getElementById("error-view");

  /* header widgets */
  const recentBtn = document.getElementById("recent-btn");
  const recentPopover = document.getElementById("recent-popover");
  const recentList = document.getElementById("recent-list");
  const recentEmpty = document.getElementById("recent-empty");
  const themeBtn = document.getElementById("theme-btn");

  const RECENT_KEY = "sma.recent";
  const FAV_KEY = "sma.favorites";
  const THEME_KEY = "sma.theme";

  const SEARCH_LIMIT = 25;
  const DEBOUNCE_MS = 120;
  const COLLAPSE_THRESHOLD = 40; // members with more forms start collapsed
  const COLLAPSE_SHOW = 24;      // ...showing this many initially
  const SECTION_COLLAPSE = 12;   // POS groups with more lemmas start collapsed
  const CLITIC_PREVIEW = 12;     // clitic forms shown before the "show N clitic forms" toggle
  const BADGE_MIN_FORMS = 6;     // single-member groups show a count badge only past this many forms

  /* ------------------------------------------------------------------
     Dashboard vocabulary. Spanish display strings are a static closed
     mapping (plan §A2/A9); empty states are the documented strings from
     docs/DESIGN_IMPLEMENTATION_PLAN.md §C verbatim (design.md §35,
     product spec §50–52).
     ------------------------------------------------------------------ */

  const POS_LABELS_ES = {
    verb: "verbo",
    noun: "sustantivo",
    adj: "adjetivo",
    adv: "adverbio",
    name: "nombre propio",
    phrase: "locución",
    pron: "pronombre",
    det: "determinante",
    article: "artículo",
    num: "numeral",
    intj: "interjección",
    prep: "preposición",
    conj: "conjunción",
    aux: "verbo auxiliar",
    prefix: "prefijo",
    suffix: "sufijo",
    other: "palabra",
  };

  const EMPTY_ORIGIN = "No se dispone de un origen histórico fiable.";
  const EMPTY_COGNATES = "No se han encontrado relaciones útiles con raíces en inglés.";
  const EMPTY_FAMILY = "Todavía no hay una familia de palabras fiable para esta entrada.";
  /* No documented mnemonic empty-state string exists in the specs; written in
     the same voice as the §51 family string (plan B3: "the §35/§51 empty
     states exist for exactly this") and translated like the other empty
     states (the product UI is Spanish; design.md §35's English strings are
     examples, not chrome). */
  const EMPTY_MNEMONIC = "Todavía no hay una mnemotecnia fiable para esta entrada.";
  const ERROR_UNKNOWN = "No hemos podido analizar con seguridad";

  /* features (English, closed vocabulary from pipeline/tags.py humanize)
     -> Spanish, for the morphology summary line. Both the sqlite
     humanize output ("imperfect indicative, 1st plural") and the fixture's
     hand-authored variant ("present indicative, first-person singular")
     must parse. */
  const FEATURE_ES = {
    infinitive: "infinitivo",
    gerund: "gerundio",
    participle: "participio",
    present: "presente",
    preterite: "pretérito",
    imperfect: "pretérito imperfecto",
    future: "futuro",
    conditional: "condicional",
    past: "pasado",
    perfect: "perfecto",
    indicative: "modo indicativo",
    subjunctive: "modo subjuntivo",
    imperative: "imperativo",
    "1st": "1ª persona",
    "first-person": "1ª persona",
    "2nd": "2ª persona",
    "second-person": "2ª persona",
    "3rd": "3ª persona",
    "third-person": "3ª persona",
    singular: "del singular",
    plural: "del plural",
    masculine: "masculino",
    feminine: "femenino",
    formal: "formal",
    informal: "informal",
    vos: "voseo",
    "with-vos": "voseo",
    "with-voseo": "voseo",
    "with-tú": "con tú",
    "-se": "(-se)",
    negative: "negativo",
    alternative: "alternativo",
    archaic: "arcaico",
    clitic: "con clítico",
  };

  const FEATURE_ABBREV = {
    infinitive: "inf.",
    gerund: "ger.",
    participle: "part.",
    present: "pres.",
    preterite: "pret.",
    imperfect: "impf.",
    future: "fut.",
    conditional: "cond.",
    past: "pas.",
    perfect: "perf.",
    indicative: "ind.",
    subjunctive: "subj.",
    imperative: "imper.",
    "1st": "1ª",
    "first-person": "1ª",
    "2nd": "2ª",
    "second-person": "2ª",
    "3rd": "3ª",
    "third-person": "3ª",
    singular: "sing.",
    plural: "plur.",
    masculine: "masc.",
    feminine: "fem.",
    formal: "form.",
    informal: "inf.",
    vos: "vos",
    "with-tú": "tú",
    "with-vos": "vos",
    "with-voseo": "vos",
    "-se": "-se",
    negative: "neg.",
    alternative: "alt.",
    archaic: "arcaico",
  };

  /* language codes + the fixture's English lang_labels -> Spanish, for the
     origin chain fallback (the backend `origin.stages` carries its own
     Spanish labels). */
  const LANG_LABELS_ES = {
    es: "español",
    la: "latín",
    grc: "griego antiguo",
    osp: "español antiguo",
    os: "español antiguo",
    roa: "romance",
    fr: "francés",
    it: "italiano",
    pt: "portugués",
    ca: "catalán",
    en: "inglés",
    de: "alemán",
    ar: "árabe",
    Spanish: "español",
    Latin: "latín",
    "Old Spanish": "español antiguo",
    "Medieval Spanish": "español medieval",
    French: "francés",
    Italian: "italiano",
    Portuguese: "portugués",
    Catalan: "catalán",
    English: "inglés",
    German: "alemán",
    Arabic: "árabe",
    "Ancient Greek": "griego antiguo",
    Greek: "griego",
  };

  function langLabelEs(lang, langLabel) {
    if (langLabel && LANG_LABELS_ES[langLabel]) return LANG_LABELS_ES[langLabel];
    if (lang && LANG_LABELS_ES[lang]) return LANG_LABELS_ES[lang];
    return langLabel || lang || "";
  }

  function foldEs(text) {
    const decomposed = String(text).normalize("NFKD").toLowerCase();
    return decomposed.replace(/[\u0300-\u036f]/g, "");
  }

  /* Closed verbal-desinence inventory mirroring pipeline/paradigm.py
     (fallback only — the backend `morphology` key supersedes it). */
  const DESINENCES = [
    "ando", "iendo", "yendo", "ado", "ido", "aba", "abas", "ábamos", "abais", "aban",
    "ía", "ías", "íamos", "íais", "ían", "ara", "aras", "áramos", "arais", "aran",
    "iera", "ieras", "iéramos", "ierais", "ieran", "ase", "ases", "ásemos", "aseis", "asen",
    "iese", "ieses", "iésemos", "ieseis", "iesen", "are", "ares", "áremos", "areis", "aren",
    "iere", "ieres", "iéremos", "iereis", "ieren", "aré", "arás", "ará", "aremos", "aréis", "arán",
    "eré", "erás", "erá", "eremos", "eréis", "erán", "iré", "irás", "irá", "iremos", "iréis", "irán",
    "aría", "arías", "aríamos", "aríais", "arían", "ería", "erías", "eríamos", "eríais", "erían",
    "iría", "irías", "iríamos", "iríais", "irían", "aste", "asteis", "aron", "iste", "isteis", "ieron",
    "é", "ó", "í", "ió", "a", "as", "amos", "áis", "an", "es", "e", "emos", "éis", "en",
    "imos", "ís", "ad", "ed", "id", "o", "s", "to", "so", "cho", "ar", "er", "ir",
  ].sort((a, b) => b.length - a.length);

  function splitDesinence(form) {
    const folded = foldEs(form);
    for (const des of DESINENCES) {
      const stemLen = folded.length - des.length;
      if (folded.endsWith(des) && stemLen >= 3) {
        return { lexeme: form.slice(0, stemLen), inflection: des };
      }
    }
    return null;
  }

  /* Parse one humanized feature string into Spanish summary tokens.
     Group order follows pipeline/tags.py: impersonal, tense, mood, person,
     number, gender, formality, voseo, aspect, variant, extra, clitic.
     Parts arrive space-joined ("imperfect indicative, 1st plural"), so each
     comma-part is split into words before lookup. */
  function featureTokensEs(feature) {
    const parts = feature.split(",").map((p) => p.trim()).filter(Boolean);
    const out = [];
    let person = null;
    let number = null;
    for (const part of parts) {
      for (const word of part.split(/\s+/)) {
        const key = word.toLowerCase().replace(/^\(|\)$/g, "");
        const es = FEATURE_ES[key];
        if (es === undefined) continue;
        if (key === "1st" || key === "first-person" || key === "2nd" || key === "second-person" ||
            key === "3rd" || key === "third-person") {
          person = es;
        } else if (key === "singular" || key === "plural") {
          number = es === "del singular" ? "singular" : "plural";
        } else {
          out.push(es);
        }
      }
    }
    if (person) out.push(number ? `${person} del ${number}` : person);
    else if (number) out.push(`del ${number}`);
    return out;
  }

  function summaryLineEs(posLabel, features) {
    if (!features || !features.length) return posLabel;
    const first = features[0];
    const tokens = featureTokensEs(first);
    // prefer the cleanest analysis (plan F12): skip junk analyses whose
    // tokens are empty or contradictory (e.g. "present preterite ...")
    let clean = tokens;
    if (tokens.includes("presente") && tokens.includes("pretérito")) {
      clean = tokens.filter((t) => t !== "pretérito");
    }
    return [posLabel].concat(clean).join(" \u00b7 ");
  }

  function featureAbbreviation(feature) {
    /* multiple analyses join with " · " (fixture style); the caption shows
       the first/cleanest one, the full string stays in the title */
    const first = String(feature).split(" \u00b7 ")[0];
    const parts = first.split(",").map((p) => p.trim()).filter(Boolean);
    const tokens = [];
    let person = null;
    let number = null;
    for (const part of parts) {
      for (const word of part.split(/\s+/)) {
        const key = word.toLowerCase().replace(/^\(|\)$/g, "");
        const ab = FEATURE_ABBREV[key];
        if (ab === undefined) continue;
        if (key === "1st" || key === "first-person" || key === "2nd" || key === "second-person" ||
            key === "3rd" || key === "third-person") {
          person = ab;
        } else if (key === "singular" || key === "plural") {
          number = ab;
        } else {
          tokens.push(ab);
        }
      }
    }
    const head = tokens.join(" ");
    if (person || number) {
      const tail = [person, number].filter(Boolean).join(" ");
      return head ? `${head} ${tail}` : tail;
    }
    return head || "\u2014";
  }

  function conjugationClassEs(lemma, pos) {
    if (pos !== "verb" || !lemma) return null;
    const folded = foldEs(lemma);
    if (folded.endsWith("ar")) return "Primera (-ar)";
    if (folded.endsWith("er")) return "Segunda (-er)";
    if (folded.endsWith("ir")) return "Tercera (-ir)";
    return null;
  }

  const MORPH_DESC = {
    lexeme: "raíz o base léxica",
    inflection: "desinencia flexiva",
    base: "infinitivo",
    baseOther: "forma de cita",
    category: "palabra variable",
    categoryOther: "clase de palabra",
    conjugation: "patrón de conjugación del infinitivo",
  };

  function readJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function writeJson(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false; // storage unavailable (private mode): session-only behaviour
    }
  }

  function storedWord(data) {
    return data.selected ? data.selected.form : (data.query || "");
  }

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
    nonfinite: "No personales",
    indicative: "Indicativo",
    subjunctive: "Subjuntivo",
    imperative: "Imperativo",
    clitics: "Con clíticos",
    other: "Otros",
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
    chip.textContent = POS_LABELS_ES[row.pos] || row.pos;
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
      statusEl.textContent = "Sin resultados";
      return;
    }
    statusEl.textContent = items.length === 1 ? "1 resultado" : `${items.length} resultados`;
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
      statusEl.textContent = "Error de búsqueda: ¿está el servidor en marcha?";
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
      // Highlighted row wins when the dropdown is open (combobox contract);
      // otherwise Enter resolves the typed string to the top-ranked match.
      e.preventDefault();
      if (!listbox.hidden && results.length && active >= 0 && results[active]) {
        selectResult(active);
      } else {
        resolveFreeText(input.value);
      }
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

  /* "Analizar" button = free-text submit: resolve the typed string to the
     top-ranked match (design.md §7, plan F4 — owner sign-off). */
  analyzeBtn.addEventListener("click", () => {
    closeDropdown();
    resolveFreeText(input.value);
  });

  /* `/` or Ctrl/Cmd+K focuses the search field from anywhere (§41). */
  document.addEventListener("keydown", (e) => {
    const tag = document.activeElement && document.activeElement.tagName;
    const inField = tag === "INPUT" || tag === "TEXTAREA";
    if ((e.key === "/" && !inField) || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k")) {
      e.preventDefault();
      input.focus();
      input.select();
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
          const toggle = el("button", "show-all", `Mostrar ${shown.length} formas con clítico`);
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
        const toggle = el("button", "show-all", `Mostrar las ${forms.length} formas`);
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
      head.append(el("span", "head-badge", "cabeza"));
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
    const h2 = el("h2", null, POS_LABELS_ES[group.pos] || group.pos_label);
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
      const toggle = el("button", "show-all", `Mostrar los ${group.members.length} lemas`);
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
    wrap.setAttribute("aria-label", "Vista del análisis");
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
    const title = `También del ${[langLabelEs(etymon.lang, etymon.lang_label), etymon.word].filter(Boolean).join(" ")}`;
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
      statusEl.textContent = "Error de búsqueda: ¿está el servidor en marcha?";
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
        return Math.max(measureText((POS_LABELS_ES[pos] || pos || "").toUpperCase(), 700, 10) + 20, 34);
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
        "aria-label": `Familia de derivación de ${root ? root.lemma : ""}: se muestran ${visible.length} de ${nodes.length} miembros; ${selectedLemma} está seleccionado. Usa las flechas para moverte entre las palabras e Intro para abrir una.`,
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
            `${node.lemma} — ${node.gloss || "sin glosa"}\u00b7 ${node.form_count ?? 0} forma${node.form_count === 1 ? "" : "s"}`,
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
        chip.append(svgEl("text", { x: x + w - chipW / 2, y: y + 26, "text-anchor": "middle" }, (POS_LABELS_ES[node.pos] || node.pos || "").toUpperCase()));
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
            "aria-label": `Expandir ${count} descendiente${count === 1 ? "" : "s"} oculto${count === 1 ? "" : "s"} de ${node.lemma}`,
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

  function renderListView(data, target) {
    const { selected, family } = data;
    target.replaceChildren();
    expandedMembers.clear();
    expandedSections.clear();
    expandedClitics.clear();
    lastData = data;

    /* header card */
    const header = el("article", "entry-card");
    header.dataset.entryId = selected.id;
    header.append(el("h2", "entry-form", selected.form));
    const lemmaLine = el("p", "entry-lemma");
    lemmaLine.append(el("span", "pos-chip " + selected.pos, POS_LABELS_ES[selected.pos] || selected.pos));
    if (selected.lemma !== selected.form) {
      lemmaLine.append(el("span", "entry-lemma-word", selected.lemma));
    }
    header.append(lemmaLine);
    header.append(el("p", "entry-gloss", selected.gloss));
    if (selected.features && selected.features.length) {
      const list = el("ul", "entry-features");
      for (const feat of selected.features) {
        list.append(el("li", null, featureTokensEs(feat).join(" \u00b7 ") || feat));
      }
      header.append(list);
    }
    target.append(header);

    /* Map | List toggle — remembered in localStorage; the list stays the
       default until the map proves itself */
    target.append(viewToggle());

    /* the etymology ribbon sits above whichever family view is active; it
       needs at least two steps to be worth drawing */
    if (data.ancestry && data.ancestry.length >= 2) {
      target.append(ancestryRibbonView(data.ancestry));
    }

    if (currentView() === "map") {
      if (data.tree && data.tree.nodes && data.tree.nodes.length) {
        target.append(familyMapView(data.tree, selected.lemma, selected.pos));
      } else {
        target.append(el("p", "empty-note", "No hay un árbol de derivación disponible para esta entrada."));
      }
    } else {
      /* sticky mini-nav — skipped when there is only one POS group: a single
         button that scrolls to itself is pure noise */
      let nav = null;
      const navButtons = [];
      if (family.groups.length > 1) {
        nav = el("nav", "pos-nav");
        nav.setAttribute("aria-label", "Categorías gramaticales");
        family.groups.forEach((group, i) => {
          const btn = el("button", null, POS_LABELS_ES[group.pos] || group.pos_label);
          btn.type = "button";
          btn.addEventListener("click", () => {
            document.getElementById(`pos-${i}`).scrollIntoView({ behavior: "smooth", block: "start" });
          });
          nav.append(btn);
          navButtons.push(btn);
        });
        target.append(nav);
      }

      /* pos sections */
      const sections = family.groups.map((group, i) => posSection(group, i));
      for (const section of sections) target.append(section);

      target.hidden = false;

      /* scrollspy: highlight the nav button of the section currently in view */
      if (nav) {
        const onScroll = () => {
          const offset = nav.offsetHeight + 84;
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

    if (family.note) target.append(el("p", "family-note", family.note));

    /* cousins are context, not family: clearly separated and visually
       secondary, and only when the backend found any */
    if (data.cousins) target.append(cousinsView(data.cousins));

    target.hidden = false;
  }

  async function openAnalysis(id) {
    loadingEl.hidden = false;
    statusEl.textContent = "";
    dashboardEl.hidden = true; // a new analysis starts: hide the stale dashboard
    layer3El.hidden = true;
    // The SQLite store can briefly fail while the pipeline rebuilds the DB
    // in place; retry once before surfacing the error to the user.
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await fetch(`/api/analyze?id=${encodeURIComponent(id)}`);
        if (res.status === 404) {
          statusEl.textContent = "Esa entrada ya no está disponible.";
          loadingEl.hidden = true;
          return;
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderAnalysis(data);
        return;
      } catch (err) {
        if (attempt === 0) {
          await new Promise((resolve) => setTimeout(resolve, 1500));
          continue;
        }
        statusEl.textContent = "Error al analizar: ¿está el servidor en marcha?";
      } finally {
        loadingEl.hidden = true;
      }
    }
  }

  /* ------------------------------------------------------------------
     Dashboard (primary view). The six regions mirror design.md §4–11 and
     the mockup: Análisis morfológico + Familia de palabras (row 1),
     Origen | Cognados en inglés | Mnemotecnia (row 2), Otras formas del
     verbo (row 3). Every card handles its empty state — the §C strings.
     ------------------------------------------------------------------ */

  const ICONS = {
    landmark:
      '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">' +
      '<path d="M4 20.5 L20 20.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' +
      '<path d="M5.5 20.5 L5.5 12 L4 13.5 L3 10.5 L12 4.5 L21 10.5 L20 13.5 L18.5 12 L18.5 20.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
    globe:
      '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">' +
      '<circle cx="12" cy="12" r="8.2" fill="none" stroke="currentColor" stroke-width="1.7"/>' +
      '<ellipse cx="12" cy="12" rx="3.6" ry="8.2" fill="none" stroke="currentColor" stroke-width="1.7"/>' +
      '<line x1="4.2" y1="8.6" x2="19.8" y2="8.6" stroke="currentColor" stroke-width="1.7"/>' +
      '<line x1="4.2" y1="15.4" x2="19.8" y2="15.4" stroke="currentColor" stroke-width="1.7"/></svg>',
    bulb:
      '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">' +
      '<path d="M12 3.5 A 6.3 6.3 0 0 0 12 16 L12 20.5 M9.5 18.5 L14.5 18.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>' +
      '<line x1="10" y1="12" x2="11" y2="12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>' +
      '<line x1="13" y1="12" x2="14" y2="12" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>' +
      '<line x1="12" y1="10" x2="12" y2="11" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
    star:
      '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">' +
      '<path d="M12 4 L14.6 9.3 L20.5 10.2 L16.2 14.3 L17.3 20.1 L12 17.2 L6.7 20.1 L7.8 14.3 L3.5 10.2 L9.4 9.3 Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>',
    chevronDown:
      '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">' +
      '<polyline points="6 9 12 15 18 9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    chevronRight:
      '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">' +
      '<polyline points="9 6 15 12 9 18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    arrowDown:
      '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" focusable="false">' +
      '<line x1="12" y1="3" x2="12" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>' +
      '<polyline points="6 13 12 19 18 13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };

  function iconEl(name, cls) {
    const span = el("span", cls || "card-icon");
    span.innerHTML = ICONS[name] || "";
    return span;
  }

  function cardWithHead(id, eyebrow, body, iconName, actions) {
    const card = el("article", "card");
    card.id = id;
    const head = el("div", "card-head");
    if (iconName) head.append(iconEl(iconName));
    head.append(el("h2", "card-eyebrow", eyebrow));
    if (actions) head.append(actions);
    card.append(head);
    const bodyWrap = el("div", "card-body");
    bodyWrap.append(body);
    card.append(bodyWrap);
    return card;
  }

  /* ---- favourites (product spec §48: default object is the lemma) ---- */

  function readFavourites() {
    return readJson(FAV_KEY, []);
  }

  function isFavourite(lemma) {
    return readFavourites().some((f) => f.lemma === lemma);
  }

  function favouriteButton(selected) {
    const lemma = (selected && (selected.lemma || selected.form)) || "";
    const btn = el("button", "fav-btn" + (isFavourite(lemma) ? " active" : ""));
    btn.type = "button";
    btn.setAttribute("aria-pressed", String(isFavourite(lemma)));
    btn.title = "Guardar en favoritos";
    btn.setAttribute("aria-label", `Guardar ${lemma} en favoritos o quitarlo`);
    btn.innerHTML = ICONS.star;
    btn.addEventListener("click", () => {
      toggleFavourite(selected);
      btn.classList.toggle("active", isFavourite(lemma));
      btn.setAttribute("aria-pressed", String(isFavourite(lemma)));
    });
    return btn;
  }

  function toggleFavourite(selected) {
    const lemma = (selected && (selected.lemma || selected.form)) || "";
    if (!lemma) return;
    let list = readFavourites();
    const idx = list.findIndex((f) => f.lemma === lemma);
    if (idx >= 0) {
      list.splice(idx, 1);
    } else {
      list.unshift({
        lemma,
        pos: selected.pos || "",
        form: selected.form || "",
        gloss: selected.gloss || "",
        ts: Date.now(),
      });
      list = list.slice(0, 100);
    }
    writeJson(FAV_KEY, list);
    renderFavourites();
  }

  function renderFavourites() {
    const list = readFavourites();
    favouritesList.replaceChildren();
    favouritesEmpty.hidden = list.length > 0;
    for (const f of list) {
      const li = el("li", "favourite-card");
      const main = el("div", "favourite-main");
      const h = el("p", "favourite-lemma");
      h.append(el("span", "lemma", f.lemma));
      if (f.pos) h.append(el("span", "pos-chip " + f.pos, POS_LABELS_ES[f.pos] || f.pos));
      if (f.form && f.form !== f.lemma) h.append(el("span", "form", f.form));
      main.append(h);
      if (f.gloss) main.append(el("p", "favourite-gloss", f.gloss));
      li.append(main);
      const actions = el("div", "favourite-actions");
      const openBtn = el("button", "card-link", "Analizar");
      openBtn.type = "button";
      openBtn.addEventListener("click", () => analyzeByWord(f.lemma));
      actions.append(openBtn);
      const del = el("button", "card-link", "Quitar");
      del.type = "button";
      del.addEventListener("click", () => {
        writeJson(FAV_KEY, readFavourites().filter((x) => x.lemma !== f.lemma));
        renderFavourites();
      });
      actions.append(del);
      li.append(actions);
      favouritesList.append(li);
    }
  }

  /* ---- recent results (product spec §47, design.md §54) ---- */

  function addRecent(item) {
    const list = readJson(RECENT_KEY, []);
    const filtered = list.filter((r) => r.word !== item.word);
    filtered.unshift({ word: item.word, lemma: item.lemma || item.word });
    writeJson(RECENT_KEY, filtered.slice(0, 10));
    renderRecentPopover();
  }

  function renderRecentPopover() {
    const list = readJson(RECENT_KEY, []);
    recentList.replaceChildren();
    recentEmpty.hidden = list.length > 0;
    for (const r of list) {
      const li = document.createElement("li");
      const btn = el("button", "popover-word-btn", r.word);
      btn.type = "button";
      if (r.lemma && r.lemma !== r.word) btn.append(el("span", "popover-word-lemma", r.lemma));
      btn.addEventListener("click", () => {
        recentPopover.hidden = true;
        recentBtn.setAttribute("aria-expanded", "false");
        analyzeByWord(r.word);
      });
      li.append(btn);
      recentList.append(li);
    }
  }

  recentBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    const show = recentPopover.hidden;
    recentPopover.hidden = !show;
    recentBtn.setAttribute("aria-expanded", String(show));
    if (show) renderRecentPopover();
  });

  document.addEventListener("click", (e) => {
    if (!recentPopover.hidden && !recentPopover.contains(e.target) && !recentBtn.contains(e.target)) {
      recentPopover.hidden = true;
      recentBtn.setAttribute("aria-expanded", "false");
    }
  });

  /* ---- theme (design.md §55; explicit toggle + prefers-color-scheme) ---- */

  function currentTheme() {
    return readJson(THEME_KEY, "system");
  }

  function effectiveTheme() {
    const t = currentTheme();
    if (t === "light" || t === "dark") return t;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function applyTheme(t) {
    document.documentElement.dataset.theme = t;
    writeJson(THEME_KEY, t);
    for (const radio of document.querySelectorAll('input[name="theme"]')) {
      radio.checked = radio.value === t;
    }
    themeBtn.setAttribute("aria-label", t === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro");
  }

  themeBtn.addEventListener("click", () => {
    applyTheme(effectiveTheme() === "dark" ? "light" : "dark");
  });

  for (const radio of document.querySelectorAll('input[name="theme"]')) {
    radio.addEventListener("change", () => applyTheme(radio.value));
  }

  /* ---- morphology card ---- */

  function morphologyBody(data) {
    const selected = data.selected || {};
    const morphology = data.morphology || null;
    const isVerb = selected.pos === "verb";
    const posLabel =
      morphology && morphology.posLabel
        ? morphology.posLabel
        : POS_LABELS_ES[selected.pos] || selected.pos || "palabra";
    const summary =
      morphology && morphology.summary
        ? morphology.summary
        : summaryLineEs(posLabel, selected.features);
    const split =
      morphology && morphology.lexeme != null
        ? { lexeme: morphology.lexeme, inflection: morphology.inflection }
        : isVerb
          ? splitDesinence(selected.form)
          : null;
    const conjugation =
      morphology && morphology.conjugationClass
        ? morphology.conjugationClass
        : conjugationClassEs(selected.lemma, selected.pos);

    const frag = document.createDocumentFragment();

    const headRow = el("div", "morph-head-row");
    const wordWrap = el("div");
    wordWrap.append(el("h2", "entry-form", selected.form));
    const summaryP = el("p", "morph-summary");
    summaryP.textContent = summary;
    wordWrap.append(summaryP);
    if (selected.gloss) wordWrap.append(el("p", "entry-gloss", selected.gloss));
    headRow.append(wordWrap);
    frag.append(headRow);

    /* ambiguity (§16 / product §15): most likely analysis + collapsible
       alternatives, never a flat list */
    const alternatives = (morphology && morphology.alternatives) || [];
    if (alternatives.length) {
      const amb = el("div", "ambiguity");
      amb.append(el("p", "ambiguity-main", "Análisis más probable"));
      const toggle = el("button", "ambiguity-toggle", `Otras interpretaciones posibles (${alternatives.length})`);
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      const list = el("ul", "ambiguity-list");
      list.hidden = true;
      for (const alt of alternatives) {
        const li = document.createElement("li");
        const btn = el("button", "ambiguity-alt");
        btn.type = "button";
        btn.append(el("span", "lemma", alt.lemma || ""));
        if (alt.pos) btn.append(el("span", "pos-chip " + alt.pos, POS_LABELS_ES[alt.pos] || alt.pos));
        if (alt.summary) btn.append(el("span", "morph-desc", alt.summary));
        btn.addEventListener("click", () => {
          if (alt.entry_id) openAnalysis(alt.entry_id);
        });
        li.append(btn);
        list.append(li);
      }
      toggle.addEventListener("click", () => {
        list.hidden = !list.hidden;
        toggle.setAttribute("aria-expanded", String(!list.hidden));
      });
      amb.append(toggle, list);
      frag.append(amb);
    }

    /* field table: Lexema / Morfema flexivo / Base / Categoría / Conjugación
       (verbs); §12 says not to force the verb schema onto other word types.
       The Morfema flexivo explanation comes from the backend's own
       decomposition label ("desinencia de pretérito imperfecto, 1ª persona
       del plural" — the mockup's third column) when present, else the
       generic one. */
    const desinenceDesc =
      morphology && Array.isArray(morphology.decomposition)
        ? (morphology.decomposition.find((d) => d.kind === "desinence") || {}).label
        : null;
    const table = el("table", "morph-table");
    table.setAttribute("aria-label", "Campos morfológicos");
    const tbody = el("tbody");
    function addRow(label, value, desc) {
      const tr = el("tr");
      tr.append(el("td", "morph-label", label));
      const td = el("td", "morph-value");
      if (value == null || value === "") {
        td.append(el("span", "empty", "\u2014"));
      } else {
        td.textContent = value;
      }
      tr.append(td);
      tr.append(el("td", "morph-desc", desc));
      tbody.append(tr);
    }
    if (isVerb) {
      addRow("Lexema", split ? split.lexeme : null, MORPH_DESC.lexeme);
      addRow("Morfema flexivo", split ? split.inflection : null, desinenceDesc || MORPH_DESC.inflection);
      addRow("Base", selected.lemma, MORPH_DESC.base);
      addRow("Categoría", posLabel, MORPH_DESC.category);
      addRow("Conjugación", conjugation, MORPH_DESC.conjugation);
    } else {
      addRow("Base", selected.lemma, MORPH_DESC.baseOther);
      addRow("Categoría", posLabel, MORPH_DESC.categoryOther);
    }
    table.append(tbody);
    frag.append(table);

    /* decomposition accordion (§15 / plan B1: 2-way split; the backend
       `morphology.decomposition` supersedes the fallback) */
    let segments =
      morphology && Array.isArray(morphology.decomposition) && morphology.decomposition.length
        ? morphology.decomposition
        : [];
    if (!segments.length && split) {
      segments = [
        { segment: split.lexeme, label: "raíz o base léxica", kind: "stem" },
        { segment: split.inflection, label: "desinencia flexiva", kind: "desinence" },
      ];
    }
    if (segments.length) {
      const decompose = el("div", "decompose-wrap");
      const toggle = el("button", "decompose-toggle", "Ver descomposición morfológica");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      const chev = el("span", "chevron");
      chev.innerHTML = ICONS.chevronDown;
      toggle.append(chev);
      const body = el("div", "decompose-body");
      body.hidden = true;
      body.append(el("p", "decompose-word", selected.form));
      const chips = el("div", "decompose-chips");
      segments.forEach((seg, i) => {
        if (i > 0) chips.append(el("span", "decompose-plus", "+"));
        const chip = el("div", "decompose-chip");
        chip.append(el("span", "seg kind-" + (seg.kind || "stem"), seg.segment));
        chip.append(el("span", "seg-label", seg.label || ""));
        chips.append(chip);
      });
      body.append(chips);
      toggle.addEventListener("click", () => {
        const opening = body.hidden;
        body.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));
        decompose.classList.toggle("open", opening);
      });
      decompose.append(toggle, body);
      frag.append(decompose);
    }

    return frag;
  }

  function morphologyCard(data) {
    const card = el("article", "card");
    card.id = "region-morphology";
    const head = el("div", "card-head");
    head.append(el("h2", "card-eyebrow", "ANÁLISIS MORFOLÓGICO"));
    const actions = el("div", "card-actions");
    actions.append(favouriteButton(data.selected || {}));
    head.append(actions);
    card.append(head);
    card.append(morphologyBody(data));
    return card;
  }

  /* ---- family radial (design.md §17–19, product spec §17–21) ---- */

  function familyPreviewData(data) {
    const selected = data.selected || {};
    const fp = data.familyPreview;
    if (fp && fp.hub) {
      /* the backend includes the hub itself as the first node and can emit
         two entries for one surface (hecho noun + hecho adj); satellites
         are the distinct remaining lemmas, capped at 10 (design.md §17) */
      const seen = new Set();
      const nodes = [];
      for (const n of fp.nodes || []) {
        if (!n.lemma || n.lemma === fp.hub || seen.has(n.lemma)) continue;
        seen.add(n.lemma);
        nodes.push({
          lemma: n.lemma,
          pos: n.pos,
          relationLabel: n.relationLabel || "",
          gloss: n.gloss || "",
          isSelected: !!n.isSelected,
        });
        if (nodes.length >= 10) break;
      }
      return { hub: fp.hub, total: fp.totalCount != null ? fp.totalCount : 1, nodes };
    }
    /* fallback: derive from family.groups + tree (same ranking idea as
       plan F11: relation type, then freq, then POS diversity) */
    const family = data.family;
    if (!family || !family.groups) return null;
    const members = [];
    const seen = new Set();
    for (const group of family.groups) {
      for (const m of group.members) {
        const key = `${m.lemma}\u0000${group.pos}`;
        if (seen.has(key)) continue;
        seen.add(key);
        members.push({
          lemma: m.lemma,
          pos: group.pos,
          relationLabel: m.relation_label || "",
          gloss: m.gloss || "",
          isHead: !!m.is_head,
          relation: m.relation || "",
        });
      }
    }
    const hub =
      (family.head && family.head.lemma) ||
      ((members.find((m) => m.isHead) || {}).lemma) ||
      (members[0] ? members[0].lemma : "") ||
      "";
    const nodeFreq = new Map();
    if (data.tree && data.tree.nodes) {
      for (const n of data.tree.nodes) nodeFreq.set(`${n.lemma}\u0000${n.pos || ""}`, n.freq || 0);
    }
    const relPriority = (r) => {
      if (!r || r === "root") return 0;
      if (/^(prefix|suffix|participle)/.test(r)) return 1;
      if (/^same paradigm/.test(r)) return 3;
      return 2;
    };
    const rest = members.filter((m) => !m.isHead && m.lemma !== hub);
    rest.sort(
      (a, b) =>
        relPriority(a.relation) - relPriority(b.relation) ||
        (nodeFreq.get(`${b.lemma}\u0000${b.pos}`) || 0) - (nodeFreq.get(`${a.lemma}\u0000${a.pos}`) || 0) ||
        (a.lemma < b.lemma ? -1 : 1),
    );
    /* one pill per lemma: the same surface can hold several entries
       (hecho noun + hecho adj) and the radial shows words, not rows */
    const byLemma = new Map();
    for (const m of rest) {
      if (!byLemma.has(m.lemma)) byLemma.set(m.lemma, m);
    }
    const distinct = [...byLemma.values()];
    let nodes = distinct.slice(0, 9);
    const selectedKey = `${selected.lemma}\u0000${selected.pos || ""}`;
    if (selected.lemma && selected.lemma !== hub) {
      const inList = nodes.some((n) => n.lemma === selected.lemma);
      if (!inList) {
        const target = distinct.find((n) => n.lemma === selected.lemma);
        if (target) {
          nodes = nodes.filter((n) => n.lemma !== target.lemma);
          nodes = [target].concat(nodes.slice(0, 8));
        }
      }
    }
    nodes = nodes.map((n) => ({
      lemma: n.lemma,
      pos: n.pos,
      relationLabel: n.relationLabel,
      gloss: n.gloss,
      isSelected: !!selected.lemma && n.lemma === selected.lemma,
    }));
    return { hub, total: byLemma.size + 1, nodes };
  }

  function showNodePopover(node, hub, wrap) {
    const old = wrap.querySelector(".node-popover");
    if (old) old.remove();
    const pop = el("div", "node-popover");
    pop.setAttribute("role", "group");
    pop.setAttribute("aria-label", `Relación de ${node.lemma} con ${hub}`);
    const head = el("p", "node-popover-head", node.lemma);
    if (node.relationLabel && node.relationLabel !== "root") {
      head.append(el("span", "rel", node.relationLabel));
    }
    pop.append(head);
    if (node.gloss) pop.append(el("p", "node-popover-gloss", node.gloss));
    const actions = el("div", "node-popover-actions");
    const analyze = el("button", "card-link", `Analizar ${node.lemma}`);
    analyze.type = "button";
    analyze.addEventListener("click", () => analyzeByWord(node.lemma));
    actions.append(analyze);
    const close = el("button", "card-link", "Cerrar");
    close.type = "button";
    close.addEventListener("click", () => pop.remove());
    actions.append(close);
    pop.append(actions);
    wrap.append(pop);
    analyze.focus();
  }

  function radialFamilyView(data) {
    const preview = familyPreviewData(data);
    const wrap = el("div", "radial-wrap");
    if (!preview || !preview.hub) {
      wrap.append(el("p", "radial-empty", EMPTY_FAMILY));
      return wrap;
    }
    const nodes = preview.nodes || [];
    const hubText = preview.hub;
    const hubW = Math.max(measureText(hubText, 700, 21) + 44, 124);
    const hubH = 48;
    const pillH = 32;
    const pillW = nodes.map((n) => measureText(n.lemma, 600, 12.5) + 28);
    const maxPillW = Math.max(20, ...pillW);
    const count = nodes.length;
    const radius = Math.max(116, hubW / 2 + maxPillW / 2 + 26, 124);
    const padX = maxPillW / 2 + 20;
    const padY = hubH / 2 + 12;
    const W = Math.ceil((radius + padX) * 2);
    const H = Math.ceil((radius + padY) * 2);
    const cx = W / 2;
    const cy = H / 2;

    const names = nodes.map((n) => n.lemma).join(", ");
    const svg = svgEl("svg", {
      class: "radial-svg",
      role: "img",
      width: W,
      height: H,
      viewBox: `0 0 ${W} ${H}`,
      "aria-label": `Familia de palabras de ${hubText}${nodes.length ? `: ${names}` : ""}.`,
    });

    /* connector lines first (drawn under the pills, like the mockup) */
    nodes.forEach((n, i) => {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(count, 1);
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);
      svg.append(svgEl("line", { class: "radial-edge", x1: cx, y1: cy, x2: x, y2: y }));
    });

    /* hub: solid accent pill */
    const hub = svgEl("g", { class: "radial-hub" });
    hub.append(svgEl("rect", { x: cx - hubW / 2, y: cy - hubH / 2, width: hubW, height: hubH, rx: hubH / 2 }));
    hub.append(svgEl("text", { x: cx, y: cy + 8, "text-anchor": "middle" }, hubText));
    svg.append(hub);

    /* satellites: white pills, searched form highlighted */
    nodes.forEach((n, i) => {
      const angle = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(count, 1);
      const x = cx + radius * Math.cos(angle);
      const y = cy + radius * Math.sin(angle);
      const w = pillW[i];
      const g = svgEl("g", {
        class: "radial-node" + (n.isSelected ? " is-selected" : ""),
        role: "button",
        tabindex: "0",
        "aria-label": `${n.lemma}${n.relationLabel ? ` \u2014 ${n.relationLabel}` : ""}`,
      });
      g.append(svgEl("rect", { class: "pill", x: x - w / 2, y: y - pillH / 2, width: w, height: pillH, rx: pillH / 2 }));
      g.append(svgEl("text", { class: "word", x, y: y + 5, "text-anchor": "middle" }, n.lemma));
      g.addEventListener("click", () => showNodePopover(n, hubText, wrap));
      g.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          showNodePopover(n, hubText, wrap);
        } else if (e.key === "Escape") {
          const pop = wrap.querySelector(".node-popover");
          if (pop) pop.remove();
        }
      });
      svg.append(g);
    });

    wrap.append(svg);
    if (!count) wrap.append(el("p", "radial-empty", EMPTY_FAMILY));

    const link = el("button", "card-link", "Ver toda la familia");
    link.type = "button";
    const chev = el("span", "chevron");
    chev.innerHTML = ICONS.chevronRight;
    link.append(chev);
    link.addEventListener("click", () => openLayer3(data, "map"));
    wrap.append(link);
    return wrap;
  }

  function familyCard(data) {
    const card = el("article", "card");
    card.id = "region-family";
    const head = el("div", "card-head");
    head.append(el("h2", "card-eyebrow", "FAMILIA DE PALABRAS"));
    const preview = familyPreviewData(data);
    if (preview && preview.total != null) {
      head.append(el("span", "count-badge", String(preview.total)));
    }
    card.append(head);
    card.append(radialFamilyView(data));
    return card;
  }

  /* ---- origin card (design.md §21–22, plan F6: real cited forms) ---- */

  function arrowDownEl() {
    const span = el("span", "arrow-ico");
    span.innerHTML = ICONS.arrowDown;
    return span;
  }

  function originView(data) {
    const frag = document.createDocumentFragment();
    const origin = data.origin;
    const ancestry = Array.isArray(data.ancestry) ? data.ancestry : [];
    let stages = null;
    if (origin && Array.isArray(origin.stages) && origin.stages.length) {
      stages = origin.stages.map((s) => ({
        word: s.word,
        lang: s.lang,
        langLabel: s.langLabel || langLabelEs(s.lang, null),
        mode: s.mode,
        note: s.note,
      }));
    } else if (ancestry.length) {
      stages = ancestry.map((s) => ({
        word: s.word,
        lang: s.lang,
        langLabel: langLabelEs(s.lang, s.lang_label),
        mode: s.mode,
        note: s.note,
      }));
    }
    if (!stages || stages.length < 2) {
      frag.append(el("p", "empty-state", EMPTY_ORIGIN));
      return frag;
    }
    /* backend stages arrive newest-first ("oldest last" in the payload);
       the card reads oldest -> newest like the mockup chain */
    const ordered = stages.slice().reverse();
    const oldest = ordered[0];
    if (oldest.lang === "es") {
      frag.append(el("p", "empty-state", EMPTY_ORIGIN));
      return frag;
    }
    const sourceLang = origin && origin.sourceLanguage ? origin.sourceLanguage : langLabelEs(oldest.lang, oldest.langLabel);
    frag.append(el("p", "origin-lead", `Del ${sourceLang}`));
    frag.append(el("p", "origin-source-word", origin && origin.sourceWord ? origin.sourceWord : oldest.word));
    if (origin && origin.sourceMeaning) {
      frag.append(el("p", "origin-source-meaning", origin.sourceMeaning));
    }
    const chain = el("div", "origin-chain");
    ordered.forEach((s, i) => {
      const stage = el("div", "origin-stage");
      stage.append(el("span", "word", s.word));
      if (s.langLabel) stage.append(el("span", "lang", s.langLabel));
      if (s.note) stage.append(el("span", "note", `(${s.note})`));
      chain.append(stage);
      if (i < ordered.length - 1) {
        /* plain ↓ between stages (mockup style); the derivation modes live
           in the Layer-3 ribbon legend, not as English labels here */
        const arrow = el("div", "origin-arrow");
        arrow.append(arrowDownEl());
        chain.append(arrow);
      }
    });
    frag.append(chain);
    const link = el("button", "card-link", "Ver evolución histórica");
    link.type = "button";
    const chev = el("span", "chevron");
    chev.innerHTML = ICONS.chevronDown;
    link.append(chev);
    link.addEventListener("click", () => openEtymologyLayer3(data));
    frag.append(link);
    return frag;
  }

  /* ---- cognates (Phase 3 data; §52 empty state before) ---- */

  function cognatesView(data) {
    const frag = document.createDocumentFragment();
    const rel = data.englishRelatives;
    if (!rel || !Array.isArray(rel.items) || !rel.items.length) {
      frag.append(el("p", "empty-state", EMPTY_COGNATES));
      return frag;
    }
    const intro = el("p", "origin-lead", `Palabras en inglés emparentadas con el latín ${rel.sharedRoot || ""}.`);
    frag.append(intro);
    const list = el("ul", "cognate-list");
    for (const it of rel.items) {
      const li = document.createElement("li");
      li.className = "cognate-item";
      li.append(el("span", "cognate-word", it.word));
      if (it.gloss) li.append(el("span", "cognate-gloss", it.gloss));
      if (it.explanation) li.title = it.explanation;
      list.append(li);
    }
    frag.append(list);
    return frag;
  }

  /* ---- mnemonic (Phase 4 data; honest empty state before, per §35/§51) ---- */

  function mnemonicsView(data) {
    const frag = document.createDocumentFragment();
    const m = data.mnemonics;
    if (!m || !m.length || !m[0].text) {
      frag.append(el("p", "empty-state", EMPTY_MNEMONIC));
      return frag;
    }
    frag.append(el("p", "mnemonic-text", m[0].text));
    return frag;
  }

  /* ---- other forms strip (design.md §28–29, product spec §38–40) ---- */

  function nearbyFormsData(data) {
    if (Array.isArray(data.nearbyForms) && data.nearbyForms.length) {
      return data.nearbyForms.map((f) => ({
        form: f.form,
        features: typeof f.features === "string" ? f.features : (f.features || []).join(" \u00b7 "),
        isLemma: !!f.isLemma,
      }));
    }
    const selected = data.selected || {};
    if (selected.pos !== "verb") return [];
    const family = data.family;
    if (!family || !family.groups) return [];
    let member = null;
    for (const group of family.groups) {
      if (group.pos !== selected.pos) continue;
      member = group.members.find((m) => m.lemma === selected.lemma) || null;
      if (member) break;
    }
    if (!member || !Array.isArray(member.forms)) return [];
    const forms = member.forms;
    const present = forms.filter((f) => /present/i.test(f.features) && /indicative/i.test(f.features));
    const pickedList = present.length ? present.slice() : forms.slice();
    const personRank = (feat) => {
      /* rank the present-indicative analysis when present (a form like
         "satisface" may list imperative first); else the first analysis */
      const feats = String(feat).split(" \u00b7 ");
      const chosen = feats.find((f) => /present/i.test(f) && /indicative/i.test(f)) || feats[0];
      const f = chosen.toLowerCase();
      let num = 0;
      if (f.includes("first-person") || f.includes("1st")) num = 1;
      else if (f.includes("second-person") || f.includes("2nd")) num = 2;
      else if (f.includes("third-person") || f.includes("3rd")) num = 3;
      return num + (f.includes("plural") ? 3 : 0);
    };
    pickedList.sort(
      (a, b) =>
        personRank(a.features) - personRank(b.features) ||
        (a.form < b.form ? -1 : 1),
    );
    return pickedList.slice(0, 8).map((f) => ({
      form: f.form,
      features: typeof f.features === "string" ? f.features : (f.features || []).join(" \u00b7 "),
      isLemma: !!f.is_lemma,
    }));
  }

  function otherFormsView(data) {
    const frag = document.createDocumentFragment();
    const forms = nearbyFormsData(data);
    const selected = data.selected || {};
    if (!forms.length) {
      frag.append(
        el(
          "p",
          "forms-empty",
          selected.pos === "verb"
            ? "No hay formas cercanas disponibles para este verbo."
            : "Esta entrada no es un verbo: no hay formas conjugadas que mostrar.",
        ),
      );
      return frag;
    }
    const body = el("div", "forms-card-body");
    const strip = el("div", "forms-strip");
    for (const f of forms) {
      const item = el("div", "form-item");
      item.append(el("span", "form-word" + (f.isLemma ? " is-lemma" : ""), f.form));
      item.append(el("span", "form-feat", featureAbbreviation(f.features)));
      strip.append(item);
    }
    body.append(strip);
    const link = el("button", "card-link", "Ver conjugación completa");
    link.type = "button";
    const chev = el("span", "chevron");
    chev.innerHTML = ICONS.chevronDown;
    link.append(chev);
    link.addEventListener("click", () => openLayer3(data, "list"));
    body.append(link);
    frag.append(body);
    return frag;
  }

  /* ---- dashboard assembler ---- */

  function renderDashboard(data) {
    const frag = document.createDocumentFragment();
    frag.append(morphologyCard(data));
    frag.append(familyCard(data));
    frag.append(cardWithHead("region-origin", "ORIGEN", originView(data), "landmark"));
    frag.append(cardWithHead("region-cognates", "COGNADOS EN INGLÉS", cognatesView(data), "globe"));
    frag.append(cardWithHead("region-mnemonics", "MNEMOTECNIA", mnemonicsView(data), "bulb"));
    const formsCard = el("article", "card");
    formsCard.id = "region-forms";
    const fHead = el("div", "card-head");
    fHead.append(el("h2", "card-eyebrow", "OTRAS FORMAS DEL VERBO"));
    formsCard.append(fHead);
    formsCard.append(otherFormsView(data));
    frag.append(formsCard);
    return frag;
  }

  let spyEnabled = true;

  function updateSidebarSpy() {
    if (!spyEnabled) return;
    const ids = ["region-morphology", "region-family", "region-origin", "region-cognates", "region-mnemonics"];
    let current = "region-morphology";
    for (const id of ids) {
      const r = document.getElementById(id);
      if (!r || r.hidden) continue;
      if (r.getBoundingClientRect().top <= 120) current = id;
    }
    for (const btn of document.querySelectorAll(".side-item")) {
      btn.classList.toggle("active", btn.dataset.target === current);
    }
  }

  window.addEventListener("scroll", updateSidebarSpy, { passive: true });

  /* ---- Layer 3 deep views ---- */

  function openLayer3(data, initialView) {
    lastData = data;
    try {
      localStorage.setItem(VIEW_KEY, initialView);
    } catch {
      /* storage unavailable: the toggle still works for the session */
    }
    renderListView(data, layer3Body);
    const selected = data.selected || {};
    layer3Title.textContent =
      initialView === "map"
        ? `Familia completa de ${selected.lemma || ""}`
        : `Conjugación y formas de ${selected.lemma || ""}`;
    dashboardEl.hidden = true;
    favouritesView.hidden = true;
    settingsView.hidden = true;
    errorView.hidden = true;
    layer3El.hidden = false;
    spyEnabled = false;
    for (const btn of document.querySelectorAll(".side-item")) {
      btn.classList.toggle("active", btn.dataset.target === "region-family");
    }
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function openEtymologyLayer3(data) {
    lastData = data;
    const frag = document.createDocumentFragment();
    if (data.ancestry && data.ancestry.length >= 1) {
      frag.append(ancestryRibbonView(data.ancestry));
    }
    if (data.cousins) frag.append(cousinsView(data.cousins));
    layer3Body.replaceChildren(frag);
    const selected = data.selected || {};
    layer3Title.textContent = `Evolución histórica de ${selected.lemma || ""}`;
    dashboardEl.hidden = true;
    favouritesView.hidden = true;
    settingsView.hidden = true;
    errorView.hidden = true;
    layer3El.hidden = false;
    spyEnabled = false;
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  layer3Back.addEventListener("click", () => {
    showDashboard();
  });

  /* ---- subviews (favourites / settings / error) ---- */

  function showSubview(view) {
    dashboardEl.hidden = true;
    layer3El.hidden = true;
    errorView.hidden = true;
    favouritesView.hidden = view !== favouritesView;
    settingsView.hidden = view !== settingsView;
    spyEnabled = false;
    const target = view === favouritesView ? "view-favourites" : "view-settings";
    for (const btn of document.querySelectorAll(".side-item")) {
      btn.classList.toggle("active", btn.dataset.target === target);
    }
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function showErrorState(query) {
    layer3El.hidden = true;
    favouritesView.hidden = true;
    settingsView.hidden = true;
    dashboardEl.hidden = true;
    errorView.hidden = false;
    errorView.replaceChildren();
    const box = el("div", "error-state");
    box.append(el("h2", null, `${ERROR_UNKNOWN} \u201c${query}\u201d.`));
    box.append(el("p", "subview-note", "Puedes probar:"));
    const ul = el("ul");
    ul.append(el("li", null, "comprobar la ortografía"));
    ul.append(el("li", null, "buscar el lema"));
    box.append(ul);
    errorView.append(box);
    spyEnabled = false;
    for (const btn of document.querySelectorAll(".side-item")) {
      btn.classList.toggle("active", btn.dataset.target === "region-morphology");
    }
  }

  /* ---- sidebar navigation ---- */

  for (const btn of document.querySelectorAll(".side-item")) {
    btn.addEventListener("click", () => {
      const target = btn.dataset.target;
      if (target === "view-favourites") {
        renderFavourites();
        showSubview(favouritesView);
      } else if (target === "view-settings") {
        showSubview(settingsView);
      } else {
        const region = document.getElementById(target);
        if (!region) return;
        if (!lastData) {
          /* no analysis yet: the regions do not exist, send the user to search */
          input.focus();
          return;
        }
        if (dashboardEl.hidden) showDashboard();
        region.scrollIntoView({ behavior: "smooth", block: "start" });
        region.setAttribute("tabindex", "-1");
        region.focus({ preventScroll: true });
      }
    });
  }

  /* ---- resolution: Enter / Analizar -> top-ranked match (plan §D + F4) ---- */

  async function analyzeByWord(word) {
    const query = String(word || "").trim();
    if (!query) {
      input.focus();
      return;
    }
    closeDropdown();
    input.value = query;
    loadingEl.hidden = false;
    statusEl.textContent = "";
    dashboardEl.hidden = true;
    layer3El.hidden = true;
    /* 1) backend word resolution (`/api/analyze?word=`, plan §D) when the
       backend has landed it; 404/422 falls through to search. */
    try {
      const res = await fetch(`/api/analyze?word=${encodeURIComponent(query)}`);
      if (res.ok) {
        const data = await res.json();
        renderAnalysis(data);
        loadingEl.hidden = true;
        return;
      }
    } catch {
      /* fall through to the search path */
    }
    /* 2) fallback: top-ranked search match -> analyze by id */
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=${SEARCH_LIMIT}`);
      const data = await res.json();
      const rows = Array.isArray(data.results) ? data.results : [];
      if (!rows.length) {
        showErrorState(query);
        return;
      }
      await openAnalysis(rows[0].id);
    } catch {
      statusEl.textContent = "Error al analizar: ¿está el servidor en marcha?";
    } finally {
      loadingEl.hidden = true;
    }
  }

  function resolveFreeText(text) {
    analyzeByWord(text);
  }

  /* ---- primary analysis entry point ---- */

  function showDashboard(data) {
    layer3El.hidden = true;
    favouritesView.hidden = true;
    settingsView.hidden = true;
    errorView.hidden = true;
    dashboardEl.hidden = false;
    dashboardEl.replaceChildren(renderDashboard(data || lastData));
    spyEnabled = true;
    updateSidebarSpy();
  }

  function renderAnalysis(data) {
    lastData = data;
    showDashboard(data);
    const selected = data.selected || {};
    if (selected.form) {
      input.value = selected.form;
      addRecent({ word: selected.form, lemma: selected.lemma || selected.form });
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* ---- init: theme, deep links (design.md §75 / product spec §75) ---- */

  function init() {
    applyTheme(currentTheme());
    renderRecentPopover();
    renderFavourites();
    const params = new URLSearchParams(window.location.search);
    const word = params.get("word");
    if (word && word.trim()) {
      analyzeByWord(word.trim());
    } else if (params.get("id")) {
      openAnalysis(params.get("id"));
    }
  }

  init();
})();

