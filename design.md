# Spanish Morphological Analyzer — UI Design Specification

## 1. Product Overview

This interface is designed for a Spanish morphological analyzer that helps users understand a word not only as an isolated dictionary entry, but as part of a larger linguistic family.

The analyzer should surface:

- The normalized lemma or base word.
- Morphological analysis of the searched form.
- Related Spanish words from the same family.
- Historical origin and etymological development.
- Latin roots and intermediate historical forms.
- English cognates or derivatives that share the same historical root.
- Mnemonics that use those relationships to make vocabulary easier to remember.
- Relevant inflected forms and conjugations.

The core design problem is **information density**.

A single analyzed word can potentially produce a very large amount of linguistic information. The interface should therefore show a high amount of information on one screen without feeling like a spreadsheet, dictionary dump, or academic database.

The design principle is:

> **Show the linguistic story first. Reveal the linguistic database second.**

The first screen should answer the most useful questions immediately. Deeper morphology, full conjugations, extended etymology, and large word-family trees should remain available behind lightweight interactions.

---

# 2. Design Goals

## Primary Goals

1. Fit a large amount of useful information into one desktop viewport.
2. Maintain a clear visual hierarchy.
3. Make the searched word the visual anchor of the page.
4. Make relationships between words easy to understand.
5. Avoid overwhelming users with every available field.
6. Make advanced linguistic information accessible without making the app feel academic or intimidating.
7. Encourage exploration between related words.
8. Treat etymology and cognates as learning tools rather than trivia.

## Secondary Goals

- Make the interface useful to language learners and linguistically curious users.
- Allow advanced users to inspect detailed morphology.
- Make word-family exploration feel interactive.
- Support future expansion into other Romance languages.
- Allow deep linking to analyzed words.

---

# 3. Core UX Principle: Progressive Disclosure

Information should be divided into three levels.

## Level 1 — Immediate

Visible without interaction.

Examples:

- searched word
- lemma
- part of speech
- grammatical interpretation
- root or lexeme
- a small word-family preview
- Latin root
- several high-value English cognates
- one mnemonic
- a few common related forms

This level should contain roughly **80% of what a normal learner wants to know**.

## Level 2 — Expandable

Revealed with a button, accordion, popover, or panel expansion.

Examples:

- full morphological decomposition
- larger word family
- historical sound changes
- more cognates
- alternate mnemonic explanations
- complete conjugation

## Level 3 — Deep Exploration

Dedicated views, modals, drawers, or full pages.

Examples:

- complete derivational tree
- historical etymology graph
- all conjugated forms
- ambiguous analyses
- detailed morphology metadata
- sources
- corpus examples
- linguistic notes

This prevents the primary page from becoming a wall of linguistic metadata.

---

# 4. Overall Page Structure

Desktop layout:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Logo        Search input                     Recent      Theme       │
├─────────┬───────────────────────────────────────────────────────────┤
│         │                                                           │
│ Sidebar │   Morphological Analysis      Word Family                 │
│         │                                                           │
│         ├──────────────────┬──────────────────┬─────────────────────┤
│         │ Origin           │ English Cognates │ Mnemonic            │
│         │                  │                  │                     │
│         ├───────────────────────────────────────────────────────────┤
│         │ Other Forms / Quick Conjugation                           │
│         │                                                           │
└─────────┴───────────────────────────────────────────────────────────┘
```

The content should visually read in this order:

1. Search
2. Analyzed word
3. Morphological interpretation
4. Word family
5. Origin
6. English root relatives
7. Mnemonic
8. Other forms

---

# 5. Page Container

## Desktop

Recommended maximum content width:

```css
max-width: 1600px;
```

The layout should fill most of the viewport on large monitors rather than sitting inside a narrow centered website column.

Recommended page padding:

```css
padding: 24px 32px 32px;
```

Main page background:

```css
#F8F9FC
```

or another extremely light neutral with a subtle blue/purple undertone.

Avoid pure white for the entire canvas because cards should remain visually distinguishable.

---

# 6. Global Grid

Use a 12-column content grid.

Recommended gap:

```css
gap: 16px;
```

Main upper row:

```text
Morphology panel: 6 columns
Word family panel: 6 columns
```

Second row:

```text
Origin:          4 columns
English Cognates:4 columns
Mnemonic:        4 columns
```

Bottom row:

```text
Other forms: 12 columns
```

This structure provides a strong rhythm and keeps information dense without becoming chaotic.

---

# 7. Header

The header is a utility surface, not a decorative navigation bar.

Recommended height:

```css
72px
```

Contents:

```text
Logo / Product Name
Search Field
Analyze Button
Recent Results
Theme Toggle
```

## Search Field

The search field is the most important global action.

Recommended dimensions:

```css
height: 44px;
max-width: 760px;
```

Visual treatment:

- white background
- subtle border
- 10–12px corner radius
- search icon on left
- no unnecessary helper text
- prominent Analyze button attached or immediately adjacent

Example:

```text
🔍  hablábamos                             [ Analizar ]
```

Keyboard behavior:

- Enter submits.
- `/` or `Cmd/Ctrl + K` may focus the field.
- Search results should not require a page reload.

---

# 8. Sidebar Navigation

The sidebar should remain compact.

Recommended width:

```css
112px
```

Navigation items:

- Analysis
- Word Family
- Origin
- English Cognates
- Mnemonic
- Favorites

Settings should sit at the bottom.

Each item consists of:

```text
icon
label
```

Recommended icon size:

```css
22px
```

Labels should use a small font:

```css
12px–13px
```

The active item can use:

```css
background: rgba(79, 70, 229, 0.07);
color: #4338CA;
border-radius: 12px;
```

The sidebar should not visually compete with the linguistic content.

On smaller screens, convert it into:

- a top tab bar
- a compact hamburger drawer
- or hide it completely in favor of page anchors

---

# 9. Card System

Most content lives inside cards.

Base card:

```css
background: #FFFFFF;
border: 1px solid #E7E9F0;
border-radius: 14px;
box-shadow: 0 1px 2px rgba(16, 24, 40, 0.02);
```

Avoid strong shadows.

Spacing:

```css
padding: 24px 28px;
```

Dense cards may use:

```css
padding: 20px 24px;
```

Cards should primarily be separated through whitespace and borders.

---

# 10. Typography

Recommended fonts:

- Inter
- Geist
- Manrope
- SF Pro
- IBM Plex Sans

For broad platform consistency, **Inter** or **Geist** are ideal.

## Type Scale

### Main analyzed word

```css
font-size: 52px;
font-weight: 700;
line-height: 1.05;
letter-spacing: -0.03em;
```

Example:

```text
hablábamos
```

### Card headings

```css
font-size: 13px;
font-weight: 650;
text-transform: uppercase;
letter-spacing: 0.06em;
color: #4338CA;
```

### Major etymological word

```css
font-size: 22px;
font-weight: 650;
```

### Body

```css
font-size: 14px;
line-height: 1.5;
```

### Secondary metadata

```css
font-size: 12px–13px;
color: #667085;
```

---

# 11. Color System

The interface should be mostly neutral.

Suggested palette:

```text
Background         #F8F9FC
Surface            #FFFFFF
Border             #E6E8F0

Primary Text       #101828
Secondary Text     #667085
Muted Text         #98A2B3

Primary Accent     #4F46E5
Accent Hover       #4338CA
Accent Soft        #EEF2FF

Success            #16A34A
Warning            #D97706
Error              #DC2626
```

The accent color should mainly communicate:

- active state
- clickable linguistic terms
- selected nodes
- important relationships
- current search word

Avoid coloring every grammatical category differently by default.

If grammatical color coding is added later, keep it extremely restrained.

---

# 12. Main Morphological Analysis Card

This is the highest-priority card.

It should occupy the upper-left half of the screen.

Structure:

```text
ANÁLISIS MORFOLÓGICO

hablábamos  🔊

verb · indicative · imperfect · first person plural

────────────────────────────────────

Lexeme            habl-
Inflection        -ábamos
Lemma             hablar
Category          Verb
Conjugation       First (-ar)

[ View morphological decomposition ▾ ]
```

## Word Header

The searched form is the strongest visual element.

Example:

```text
hablábamos
```

Audio playback can be a small icon button next to the word.

Do not give the button equal visual weight to the word.

---

# 13. Morphological Summary Line

Immediately below the word, display the most meaningful interpretation.

Example:

```text
verb · indicative · imperfect · 1st person plural
```

This should use the primary accent.

Avoid presenting this information as five separate badges unless badges become necessary for interaction.

Plain inline metadata is visually cleaner.

---

# 14. Morphology Table

The summary table should be compact.

Example:

| Field | Value | Explanation |
|---|---|---|
| Lexeme | habl- | lexical stem |
| Inflection | -ábamos | imperfect + first-person plural |
| Lemma | hablar | infinitive |
| Category | Verb | inflecting word |
| Conjugation | First (-ar) | hablar, cantar, caminar |

The third column can be hidden on smaller screens.

Rows should not have heavy borders.

Use subtle separators:

```css
border-bottom: 1px solid #EEF0F4;
```

---

# 15. Full Morphological Decomposition

The button:

```text
View morphological decomposition
```

opens an accordion inside the card.

Example expanded state:

```text
hablábamos

habl      +      á      +      ba      +      mos
stem             theme vowel   TAM            person/number
```

The expanded section can include:

- root
- derivational morphemes
- theme vowel
- tense/aspect/mood marker
- person
- number
- clitics

Advanced linguistic terminology should include tooltips.

Example:

```text
TAM ⓘ
```

Tooltip:

```text
Tense, Aspect and Mood
```

---

# 16. Ambiguous Analyses

Some forms may have multiple valid analyses.

Example:

```text
creo
```

could theoretically relate to multiple lemmas depending on context.

If ambiguity exists, show:

```text
Most likely analysis

creer
verb · first person singular · present

Other possible analysis (1)
```

Clicking the secondary option expands alternatives.

Never display all possible analyses equally unless confidence is unavailable.

---

# 17. Word Family Card

This is the second most important card.

The visual goal is to communicate:

> “These words belong to the same Spanish family.”

Do not attempt to show the entire family in the default state.

Instead show the central lemma plus roughly 6–10 meaningful relationships.

Example:

```text
             hablante

inhablable —— hablar —— hablador

            hablado

habladuría        hablador
```

---

# 18. Word Family Graph

Central node:

```text
hablar
```

Use strong accent fill.

Related nodes use:

```css
background: #FFFFFF;
border: 1px solid #DCE0EA;
```

The currently searched form may use a soft highlighted node:

```css
background: #EEF2FF;
border-color: #C7D2FE;
```

Connections should be extremely subtle.

Example:

```css
stroke: #E5E7EB;
stroke-width: 1;
```

No arrows unless the relationship direction is meaningful.

---

# 19. Relationship Types

When a user clicks a node, show the relationship.

Example:

```text
hablador
derived from hablar + -dor

Type:
Agent noun

Meaning:
a person who speaks
```

Relationship categories may include:

- inflected form
- derivative
- prefix derivative
- suffix derivative
- compound
- learned borrowing
- historical relative
- semantic relative

The UI should avoid exposing these categories until requested.

---

# 20. Full Word Family

Button:

```text
View entire family →
```

opens either:

1. a large modal graph, or
2. a dedicated `/family/hablar` page.

For large families such as:

```text
hacer
```

the graph should support filtering.

Example filters:

```text
All
Common
Verbs
Nouns
Adjectives
Learned forms
Historical relatives
```

---

# 21. Etymology / Origin Card

This card tells the historical story of the word.

Default structure:

```text
ORIGIN

From Latin

fabulāre

to speak, converse, tell stories

fabulāre
   ↓
fablar
   ↓
hablar
```

The etymological chain should be visually readable even by someone with no linguistic training.

---

# 22. Historical Timeline

A compact vertical timeline is preferable to a paragraph.

Example:

```text
Latin
fabulāre

↓ consonant change

Old Spanish
fablar

↓ /f/ → /h/

Modern Spanish
hablar
```

Clicking a transformation can reveal details.

Example:

```text
Why did f become h?
```

Expanded explanation:

```text
Many Latin words beginning in /f/ developed an aspirated sound in early
Castilian, which later became silent h in modern Spanish.
```

This turns etymology into an educational interaction.

---

# 23. English Cognates / Root Relatives

This section must **not** show direct translations.

Its purpose is to reveal English words related through a historical root.

For example:

```text
Spanish hacer
Latin facere
English factory
English manufacture
English fact
```

The purpose is memory association.

Preferred title:

```text
ENGLISH COGNATES
```

or

```text
ENGLISH ROOT RELATIVES
```

"Cognates" is more linguistically precise but may need a tooltip for casual learners.

---

# 24. English Cognate Card Structure

Example:

```text
ENGLISH COGNATES

Latin root: facere

factory
from Latin factor / facere
“something made”

fact
from Latin factum
“something done”

manufacture
manu + facere
“make by hand”

[ Show more cognates ▾ ]
```

The relationship should be explicit.

Do not imply that Spanish and English forms derived directly from each other.

Visually, show the shared source:

```text
                Latin facere
                /           \
           Spanish hacer    English factory
```

A tiny visual tree is often clearer than explanatory prose.

---

# 25. Cognate Confidence

Some etymological relationships may be uncertain or indirect.

If the data contains confidence information, it may be represented as:

```text
Direct cognate
Shared Latin root
Related learned borrowing
Possible historical relation
```

Avoid percentages unless the underlying data genuinely supports numerical confidence.

---

# 26. Mnemonic Card

The mnemonic should transform linguistic relationships into memorable associations.

It should be short.

Example for `hacer`:

```text
Remember:

hacer comes from Latin facere.

English factory also comes from the same root.

A factory is where things are MADE → hacer = to make/do.
```

This is stronger than an arbitrary mnemonic because it teaches real linguistic structure.

---

# 27. Mnemonic Design

Mnemonic cards may use:

- short emphasized words
- tiny illustrations
- arrows
- word bridges
- shared-root highlights

Example:

```text
facere
  ↓
factory → things are MADE
  ↓
hacer → to make / do
```

The mnemonic should never become a large paragraph.

Target:

```text
2–4 lines
```

Button:

```text
Show another mnemonic
```

may generate alternative memory hooks.

---

# 28. Other Forms / Quick Conjugation

The bottom horizontal card provides immediate access to nearby forms.

Example:

```text
OTHER FORMS OF THE VERB

hablo     hablas     habla     hablamos     habláis     hablan

present   present    present   present      present     present

[ View complete conjugation ▾ ]
```

The goal is quick recognition, not complete conjugation.

Limit the default row to approximately:

```text
6–8 forms
```

---

# 29. Complete Conjugation

The full conjugation should appear in:

- a modal
- a large drawer
- or a dedicated expandable section

Recommended grouping:

```text
Indicative
Subjunctive
Imperative
Non-finite forms
```

Within each:

```text
Present
Preterite
Imperfect
Future
Conditional
etc.
```

Avoid displaying the entire conjugation table in the primary page by default.

---

# 30. Clickable Linguistic Terms

Nearly every meaningful word in the interface should be explorable.

Examples:

```text
hablador
fabulāre
factory
-dor
```

Click behavior depends on context.

Spanish word:

```text
Analyze this word
```

Latin word:

```text
Show root information
```

English cognate:

```text
Show connection
```

Suffix:

```text
Explain suffix
```

Cursor:

```css
cursor: pointer;
```

Hover:

```css
color: #4338CA;
text-decoration: underline;
text-decoration-color: #C7D2FE;
```

---

# 31. Microinteractions

Animations should be subtle.

Recommended:

```css
transition: 120ms–180ms ease;
```

Use animation for:

- card expansion
- graph node focus
- hover
- dropdown opening
- search result replacement

Avoid decorative motion.

Word-family nodes may shift slightly or highlight their paths when selected.

---

# 32. Hover State for Word-Family Nodes

When hovering:

```text
hablador
```

highlight:

```text
hablar → hablador
```

while dimming unrelated connections slightly.

Example:

```css
opacity: 0.45;
```

for unrelated nodes.

This allows complex graphs to remain readable.

---

# 33. Search Result Transition

When analyzing a new word:

1. Keep page structure fixed.
2. Replace content in place.
3. Use a short skeleton state.
4. Avoid full-screen loaders.

Skeleton duration should only reflect actual loading.

Do not artificially delay results.

---

# 34. Loading Skeleton

Example:

```text
████████████████
████████

───────────────
██████  ███████
██████  ███████
```

Use skeletons independently per card if data is fetched from multiple sources.

For example:

- morphology can appear first
- etymology can appear later
- word family can appear later

This makes the interface feel faster.

---

# 35. Empty States

If no etymology exists:

```text
No reliable historical origin is currently available.
```

If no English cognates exist:

```text
No useful English root relatives found.
```

Do not force weak or speculative relationships purely to fill the card.

---

# 36. Error States

Example:

```text
We couldn't analyze “xyzabc”.

Try:
• checking the spelling
• searching the base form
```

If partial data exists, show it rather than failing the entire page.

Example:

```text
Morphology available
Etymology unavailable
```

---

# 37. Responsive Design

## Large Desktop

```text
≥ 1440px
```

Use the full multi-column layout.

---

## Standard Desktop

```text
1024px–1439px
```

Keep:

```text
Morphology + Family
```

side by side.

Second row can remain 3-column if space allows.

---

## Tablet

```text
768px–1023px
```

Recommended:

```text
Morphology
Word Family

Origin + Cognates
Mnemonic

Other Forms
```

Sidebar becomes compact icons or horizontal navigation.

---

## Mobile

```text
< 768px
```

Single column.

Order:

```text
Search
Morphology
Word Family
Mnemonic
Origin
English Cognates
Other Forms
```

The mnemonic moves above deeper historical data because it is more useful to most learners.

Word-family graph may become a horizontally scrollable node strip or simplified tree.

---

# 38. Mobile Search

The header should collapse.

Example:

```text
Analizador             ☰

[ Search Spanish word               ]

[ Analyze ]
```

Recent searches can move into the navigation drawer.

---

# 39. Mobile Word Family

Do not attempt to render a large radial graph on a narrow screen.

Instead use:

```text
hablar

Related:
[hablante] [hablado] [hablador]
[inhablable] [habladuría]

View full family →
```

The full graph may open in a dedicated landscape-friendly view.

---

# 40. Accessibility

Minimum target size:

```css
44px × 44px
```

for major interactive controls.

Text contrast should meet WCAG AA.

Do not rely exclusively on color.

Example:

Bad:

```text
purple = verb
green = noun
```

Better:

```text
Verb · purple accent
Noun · green accent
```

Graph relationships should remain understandable using labels and structure.

---

# 41. Keyboard Navigation

Recommended shortcuts:

```text
/              Focus search
Enter          Analyze
Esc            Close modal / drawer
↑ ↓            Navigate search suggestions
Cmd/Ctrl + K   Global search
```

All graph nodes should be keyboard-focusable.

---

# 42. Tooltip System

Tooltips are useful for linguistic terminology.

Examples:

```text
Lexeme ⓘ
Lemma ⓘ
Morpheme ⓘ
Cognate ⓘ
TAM ⓘ
```

Tooltips should explain concepts using learner-friendly language.

Example:

```text
Lemma

The dictionary form of a word.
For “hablábamos”, the lemma is “hablar”.
```

---

# 43. Information Priority

Visual priority should roughly be:

## Priority 1

- searched word
- meaning / grammatical role
- lemma

## Priority 2

- family
- morphology
- mnemonic

## Priority 3

- origin
- useful English cognates

## Priority 4

- full inflection tables
- advanced historical notes
- edge-case morphology
- references and citations

This hierarchy should influence both layout and typography.

---

# 44. Why the Word Family Is Large

The family graph deserves a large card because it is one of the product's most distinctive features.

Traditional dictionaries already provide:

```text
word
definition
conjugation
```

The analyzer should visually emphasize its differentiator:

```text
word → family → origin → related vocabulary
```

This makes the app feel more like a linguistic map than a dictionary.

---

# 45. Card Density Rules

To prevent clutter:

## Rule 1

A card should ideally contain **one dominant concept**.

## Rule 2

No default card should require significant scrolling.

## Rule 3

If content exceeds roughly 8–10 rows, truncate it.

## Rule 4

Use:

```text
Show more
View full family
View history
View complete conjugation
```

instead of shrinking typography.

## Rule 5

Avoid nested borders wherever possible.

---

# 46. Borders vs Backgrounds

Use borders to separate major cards.

Use backgrounds to indicate selection.

Example:

```text
Normal card:
white + light border

Selected word-family node:
soft purple background

Main lemma node:
solid purple background
```

Do not put every row inside an individual pill or box.

Excessive containers create visual noise.

---

# 47. Pills

Pills should only represent:

- selectable categories
- filters
- compact statuses
- graph nodes

Avoid turning normal text metadata into pills.

Good:

```text
[ Verb ]
[ Noun ]
[ Adjective ]
```

when used as filters.

Less good:

```text
[ Indicative ] [ Imperfect ] [ First Person ] [ Plural ]
```

if they are purely descriptive.

Inline text is calmer.

---

# 48. Suggested Component Architecture

Example frontend hierarchy:

```text
AnalyzerPage
│
├── AppHeader
│   ├── Logo
│   ├── AnalyzerSearch
│   ├── RecentSearches
│   └── ThemeToggle
│
├── Sidebar
│
└── AnalyzerDashboard
    │
    ├── MorphologyCard
    │   ├── WordHeader
    │   ├── MorphologySummary
    │   ├── MorphologyTable
    │   └── MorphologyBreakdown
    │
    ├── WordFamilyCard
    │   ├── FamilyGraph
    │   ├── FamilyNode
    │   └── FamilyDetailsPopover
    │
    ├── OriginCard
    │   └── EtymologyTimeline
    │
    ├── CognatesCard
    │   ├── CognateItem
    │   └── RootRelationship
    │
    ├── MnemonicCard
    │
    └── QuickFormsCard
        └── ConjugationDrawer
```

---

# 49. Suggested Data Model Mapping

The UI should consume structured data rather than formatted text.

Example:

```ts
interface AnalysisResult {
  query: string
  lemma: string

  morphology: {
    partOfSpeech: string
    lexeme?: string
    morphemes: Morpheme[]
    features: MorphologicalFeature[]
    conjugationClass?: string
    alternatives?: MorphologicalAnalysis[]
  }

  family: {
    primary: RelatedWord[]
    totalCount: number
  }

  etymology?: {
    sourceLanguage: string
    sourceWord: string
    meaning?: string
    stages: EtymologyStage[]
  }

  englishRelatives?: EnglishRelative[]

  mnemonics?: Mnemonic[]

  nearbyForms?: WordForm[]
}
```

---

# 50. Example English Relative Model

```ts
interface EnglishRelative {
  word: string
  sharedRoot: string
  relationType:
    | "direct-cognate"
    | "shared-latin-root"
    | "learned-borrowing"
    | "historical-relative"

  explanation: string
}
```

Example:

```ts
{
  word: "factory",
  sharedRoot: "facere",
  relationType: "shared-latin-root",
  explanation: "Factory ultimately comes from Latin facere, 'to make or do'."
}
```

---

# 51. Interaction: Clicking an English Cognate

Example:

User clicks:

```text
factory
```

Open a small side popover:

```text
factory

Latin:
facere
to make / do

Spanish relative:
hacer

Connection:
Both descend from forms built from the Latin root fac-.

Mnemonic:
A factory is a place where things are MADE.
```

This interaction makes the cognate section part of the learning system.

---

# 52. Mnemonic Generator UX

If mnemonics are dynamically generated:

```text
Mnemonic

A factory is where things are made.
factory ← facere → hacer

[ Another mnemonic ]
```

Clicking `Another mnemonic` should replace only the mnemonic content.

Optional rating controls:

```text
Helpful
Not helpful
```

This could later train ranking or personalization.

---

# 53. Favorites

Users may favorite:

- words
- families
- mnemonics

Default behavior should favorite the analyzed lemma rather than the exact inflected search form.

Example:

Searching:

```text
hablábamos
```

favorites:

```text
hablar
```

unless the user explicitly chooses the form.

---

# 54. Recent Searches

Recent searches should be lightweight.

Example popover:

```text
Recent

hacer
hablar
satisfacer
hecho
poner
```

Show perhaps 8–10.

A full history page can exist separately.

---

# 55. Dark Mode

Dark mode palette example:

```text
Background       #0F1117
Surface          #161922
Border           #272B36

Primary Text     #F5F7FA
Secondary Text   #AAB0BE

Accent           #818CF8
Accent Soft      #25284A
```

Avoid pure black.

Word-family graph lines should remain subtle but visible.

---

# 56. Suggested Iconography

Use one consistent icon set.

Recommended:

- Lucide
- Phosphor
- Heroicons

Possible icons:

```text
Analysis           Search / ScanText
Family             GitFork / Network
Origin             Landmark / History
English Cognates   Languages / Globe
Mnemonic           Lightbulb
Favorites          Star
Settings           Settings
Audio              Volume2
History            Clock3
```

Use outline icons rather than mixed filled styles.

---

# 57. Avoid

Do not:

- put every feature into tabs
- use giant tables
- display the complete conjugation immediately
- show dozens of family nodes by default
- use excessive gradients
- use heavy card shadows
- overuse badges
- make morphology look like raw JSON
- treat the English section as translation
- use academic jargon without explanations
- use multiple competing accent colors
- put every interaction inside a modal

---

# 58. Desktop Target Layout Example

At approximately 1536 × 1024:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Analizador     [ hablábamos                     ] [ Analizar ]   ◷ ☼ │
├───────────┬───────────────────────────────┬──────────────────────────┤
│           │                               │                          │
│ Analysis  │ ANÁLISIS MORFOLÓGICO          │ FAMILIA DE PALABRAS      │
│ Family    │                               │                          │
│ Origin    │ hablábamos                    │         hablante         │
│ English   │                               │            │             │
│ Mnemonic  │ verb · indicative...          │ inhablable─hablar─...    │
│           │                               │                          │
│           │ Lexeme       habl-            │                          │
│           │ Inflection   -ábamos          │                          │
│           │ Lemma        hablar           │                          │
│           │                               │                          │
│           │ [ decomposition ▾ ]           │ [ full family → ]        │
│           │                               │                          │
│           ├───────────────┬───────────────┼──────────────────────────┤
│           │ ORIGIN        │ COGNATES      │ MNEMONIC                 │
│           │               │               │                          │
│           │ fabulāre      │ fable         │ Latin facere → factory   │
│           │ ↓             │ fabulous      │ factory = things MADE    │
│           │ fablar        │ affable       │ hacer = make/do          │
│           │ ↓             │               │                          │
│           │ hablar        │               │                          │
│           ├──────────────────────────────────────────────────────────┤
│           │ OTHER FORMS                                             │
│           │ hablo  hablas  habla  hablamos  habláis  hablan         │
└───────────┴──────────────────────────────────────────────────────────┘
```

---

# 59. Design Philosophy

The product should feel somewhere between:

- a modern dictionary
- a knowledge graph
- a language-learning tool
- an interactive etymology atlas

It should **not** feel like:

- a linguistic research database
- a spreadsheet
- an academic paper
- a traditional dictionary page

The page should provide a sense that every word has a structure and a history that can be explored.

The visual hierarchy should reinforce that idea:

```text
WORD
↓
STRUCTURE
↓
FAMILY
↓
HISTORY
↓
RELATED VOCABULARY
↓
MEMORY
```

---

# 60. Final UX Principle

When deciding whether information belongs on the default page, use this test:

> Does this information help the user understand, recognize, remember, or explore the word immediately?

If yes, surface it.

If it is primarily useful for linguistic completeness, hide it behind an interaction.

This allows the analyzer to contain a very deep linguistic dataset while keeping the interface clean, modern, and approachable.
