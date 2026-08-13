# Spanish Morphological Analyzer
## Product Structure and Interaction Reference

**Document type:** Product architecture / UX behavior specification  
**Primary audience:** Product managers, designers, coding agents, frontend developers, QA  
**Purpose:** Define how the analyzer is structured as a product, what each section is responsible for, what information is shown by default, what is progressively disclosed, and how users move through the interface.

---

# 1. Purpose of This Document

This document defines the product logic of the Spanish Morphological Analyzer interface.

It is intentionally **not** an engineering implementation document.

It does not prescribe:

- framework choice
- database structure
- API architecture
- state-management libraries
- rendering libraries
- graph libraries
- caching strategy
- backend service boundaries

Instead, it explains:

- what the user sees
- why the page is divided into its current sections
- which information belongs in each section
- what is visible immediately
- what is hidden initially
- what happens when the user asks for more detail
- which interactions stay in-place
- which interactions deserve a larger view
- how the page should behave when information is missing or ambiguous
- which product principles must remain stable even if the implementation changes

A coding agent should be able to use this document as a behavioral source of truth when modifying the interface.

---

# 2. Product Definition

The analyzer is a **word-exploration product**, not merely a morphological parser.

A traditional morphological analyzer might return:

```text
hablábamos
lemma: hablar
POS: verb
mood: indicative
tense: imperfect
person: first
number: plural
```

This product goes further.

It aims to answer several related questions in one place:

1. **What is this word grammatically?**
2. **What is its base form?**
3. **How is it internally constructed?**
4. **What other Spanish words belong to the same family?**
5. **Where did this word come from historically?**
6. **Which English words share the same historical root?**
7. **Can those historical relationships help me remember the Spanish word?**
8. **What nearby grammatical forms should I recognize?**

The product therefore combines four roles:

- morphological analyzer
- word-family explorer
- etymology explorer
- language-learning memory aid

The UI should make these feel like one coherent product rather than four disconnected tools.

---

# 3. Core Product Thesis

The core thesis is:

> A word is easier to understand and remember when the user can see its structure, family, history, and cross-language relationships together.

The product should therefore present a word as a small knowledge system.

A user should not experience the page as:

```text
definition
table
table
table
etymology
conjugation
```

They should experience it as:

```text
this is the word
↓
this is what it is
↓
this is how it is built
↓
these words are related to it
↓
this is where the family came from
↓
these English words share that history
↓
this connection can help you remember it
```

That narrative is the organizing logic of the page.

---

# 4. The Main Product Problem

The application can produce much more information than can comfortably fit on one screen.

Potential information includes:

- lexical root
- lemma
- stem
- inflection
- derivational morphemes
- tense
- aspect
- mood
- person
- number
- gender
- grammatical category
- clitics
- alternate analyses
- confidence
- related forms
- derived words
- compounds
- historical relatives
- learned borrowings
- Latin root
- Proto-Romance or earlier forms
- Old Spanish forms
- sound changes
- semantic shifts
- English cognates
- cognate explanations
- mnemonics
- conjugations
- sources
- corpus examples

Displaying all of this at once would create a dense academic dashboard.

The product therefore uses **progressive disclosure**.

The page should contain a large amount of information, but only the most useful portion of each information category is visible by default.

---

# 5. Progressive Disclosure Model

The interface has three information depths.

## 5.1 Layer One: Immediate Understanding

This is the default screen.

It should answer the most useful questions without requiring any clicks.

Typical content:

- searched form
- lemma
- part of speech
- grammatical analysis
- basic morphological segmentation
- representative word-family members
- Latin origin
- several useful English historical relatives
- one mnemonic
- several nearby verb forms where relevant

The user should leave with a useful understanding even if they never interact with the page.

---

## 5.2 Layer Two: Local Expansion

Layer Two adds detail **without moving the user away from the current word**.

It appears through:

- accordion expansion
- inline expansion
- popover
- small contextual panel
- local "show more" controls

Examples:

- full morpheme decomposition
- explanations of linguistic terms
- more English cognates
- detailed word-family relationship for one node
- another mnemonic
- more historical steps
- alternative morphological interpretations

Layer Two is still part of the main analyzer page.

---

## 5.3 Layer Three: Deep Exploration

Layer Three is for information too large or specialized for the dashboard.

It may appear as:

- large drawer
- modal workspace
- dedicated route
- expanded full-screen graph
- full conjugation view
- complete family browser
- detailed etymology view

Examples:

- 100+ member word family
- complete Spanish conjugation
- historical derivation graph
- extensive source notes

Layer Three should be used when preserving the small dashboard format would force excessive compression.

---

# 6. Information Hierarchy

Not all information has equal importance.

The page should prioritize information in this order.

## Tier A: Identity

The user needs to know:

- what word was analyzed
- what lemma it belongs to
- what grammatical form it is

These are the strongest visual elements.

---

## Tier B: Relationships

The product's distinctive value is showing relationships.

These include:

- Spanish family relationships
- internal morphological relationships
- historical relationships
- English root relationships

These deserve prominent visual space.

---

## Tier C: Learning Value

Information that helps memory and recognition:

- mnemonic
- useful related forms
- accessible explanations

These should be easy to reach and visually friendly.

---

## Tier D: Completeness

Information that exists primarily for completeness:

- full inflection paradigms
- low-frequency relatives
- technical etymological notes
- uncommon alternative analyses
- source metadata

These should remain available but should not dominate the default screen.

---

# 7. Main Page Architecture

The product is organized as a single analysis dashboard.

At desktop size, the conceptual arrangement is:

```text
┌──────────────────────────────────────────────────────────────┐
│ Global Header                                                │
│ Search + recent analyses + global actions                    │
├───────────┬─────────────────────────┬────────────────────────┤
│           │                         │                        │
│           │ Morphological Analysis  │ Word Family            │
│           │                         │                        │
│ Navigation│                         │                        │
│           ├─────────────┬───────────┼────────────────────────┤
│           │ Origin      │ English   │ Mnemonic               │
│           │             │ relatives │                        │
│           ├──────────────────────────────────────────────────┤
│           │ Nearby Forms / Quick Conjugation                 │
└───────────┴──────────────────────────────────────────────────┘
```

This arrangement is not arbitrary.

The top row contains the two strongest product concepts:

- **What is this word?**
- **What other words belong with it?**

The second row explains:

- **Where did it come from?**
- **How is that history visible in English?**
- **How can I use that connection to remember it?**

The bottom row provides nearby grammatical forms.

---

# 8. Global Header

## Purpose

The header controls the analysis session.

It is not meant to carry extensive navigation.

Its primary responsibilities are:

- entering a word
- starting an analysis
- reopening recent analyses
- accessing lightweight global preferences

---

## Default Contents

The header should contain:

1. product identity
2. word search
3. Analyze action
4. recent results
5. optional theme control

The search field should dominate the header visually.

---

## Search Behavior

The user enters a Spanish word or form.

Examples:

```text
hacer
hecho
hacíamos
hablábamos
satisfacer
miento
```

The analyzer should accept both lemmas and inflected forms.

On submission:

- the current page becomes the new analysis
- the overall layout stays stable
- each card updates its content
- the page should not visually reset into an unrelated layout

The product should feel like a persistent linguistic workspace.

---

# 9. Sidebar Navigation

## Purpose

The sidebar acts as an **orientation tool**, not as the main way to access separate pages.

Each item corresponds to a major conceptual region of the current analysis:

- Analysis
- Word Family
- Origin
- English Relatives
- Mnemonic
- Favorites

The user should understand that these are aspects of the same word.

---

## Expected Behavior

On desktop, selecting a section may:

- scroll to that section
- visually focus it
- open a larger version if appropriate

The sidebar should not imply that every card is a separate application.

On narrow screens, this navigation can collapse because the same information is naturally available through vertical scrolling.

---

# 10. Morphological Analysis Section

## Product Role

This section establishes the identity of the searched word.

It should answer:

- What word did I search?
- What is its lemma?
- What grammatical form is it?
- How is it morphologically structured?

This is the primary interpretation card.

---

## Default Content

A default verb analysis might show:

```text
hablábamos

verb · indicative · imperfect · first person plural

Lexeme       habl-
Inflection   -ábamos
Lemma        hablar
Category     Verb
Conjugation  First (-ar)
```

The card should show only the most useful fields by default.

---

## Why the Word Is Large

The searched word is the visual anchor of the product.

The page is not about "a dataset entry for hablar."

It is about the user's current word.

Therefore:

```text
hablábamos
```

should visually dominate the analysis card.

The lemma is important, but it should not replace the searched form as the main identity.

---

# 11. Morphological Summary Line

Immediately below the searched word, the interface presents a plain-language grammatical summary.

Example:

```text
verb · indicative · imperfect · first person plural
```

This is the fastest way for most users to understand the form.

The summary should be preferred over exposing every internal field separately.

The detailed table exists for inspection.

The summary exists for comprehension.

---

# 12. Morphological Field Table

The compact field table provides a structured view.

Its default fields should depend on the word type.

For verbs:

- lemma
- lexical stem
- inflection
- tense
- mood
- person
- number
- conjugation class

For nouns:

- lemma
- gender
- number
- root
- derivational structure if relevant

For adjectives:

- lemma
- gender
- number
- derivational structure
- degree where relevant

The product should not force the same field schema onto every word.

---

# 13. Morphological Decomposition Expansion

The default card contains a control similar to:

```text
View morphological decomposition
```

This expands **inside the same card**.

It should not open a new page.

Why?

Because morpheme-level detail is a deeper explanation of the current analysis, not a new task.

---

## Expanded State

The expanded version may show:

```text
habl + á + ba + mos

habl-
lexical stem

-á-
theme vowel

-ba-
imperfect marker

-mos
first-person plural
```

The exact segmentation may vary by linguistic model.

The product behavior should remain the same:

- visually break the form into meaningful units
- label those units
- explain them in learner-friendly language

---

# 14. Technical Linguistic Terms

Terms such as:

- lexeme
- morpheme
- TAM
- clitic
- derivation
- cognate

should not be removed simply because beginners may not know them.

Instead, the product should support two layers:

```text
technical term
+
short accessible explanation
```

Example:

```text
Lexeme ⓘ
The stable lexical part of the word.
```

The goal is to teach terminology without forcing it on the user.

---

# 15. Morphological Ambiguity

Some forms can map to multiple analyses.

The product should avoid presenting all interpretations with equal visual weight unless there is no meaningful ranking.

Preferred structure:

```text
Most likely analysis
creer
verb · present · first person singular

Other possible analyses (1)
```

The alternatives remain collapsed.

---

## Expansion

Selecting "Other possible analyses" reveals additional interpretations inside the card or in a compact secondary panel.

Each alternative should clearly show:

- lemma
- part of speech
- grammatical analysis
- any contextual reason for the ranking if available

The product should avoid pretending uncertainty does not exist.

It should also avoid making ambiguity the first thing a learner sees.

---

# 16. Word Family Section

## Product Role

The word-family section is one of the analyzer's primary differentiators.

Its purpose is to answer:

> What other modern Spanish words belong to the same useful lexical family?

This section is not merely a list of inflected forms.

It should prioritize **derivational and lexical relationships**.

Examples for a family could include:

- base verb
- noun derivatives
- adjectives
- agent nouns
- prefixed derivatives
- common learned relatives
- historical family members when relevant

---

# 17. Word Family Preview

The main card shows only a representative subset.

Typical target:

```text
6–10 visible nodes
```

The central node should usually be the lemma.

Example:

```text
             hablante

inhablable — hablar — hablador

             hablado
```

The purpose of the preview is not completeness.

The purpose is to establish that the searched word belongs to a network.

---

# 18. Choosing Which Family Members Appear

The preview should favor high-value relationships.

Ranking considerations may include:

1. frequency
2. semantic transparency
3. closeness to the lemma
4. usefulness to learners
5. morphological diversity
6. confidence of relationship

The preview should not simply show the first N items returned by a data source.

A word-family preview is curated product output.

---

# 19. Search Form Within the Family

If the user searched an inflected form such as:

```text
hablábamos
```

that form may appear as a highlighted peripheral node.

The central node should still normally be:

```text
hablar
```

This visually communicates:

```text
hablábamos → belongs to → hablar family
```

---

# 20. Clicking a Family Node

Clicking a related word should not immediately replace the entire page unless the user explicitly chooses to analyze it.

First interaction should expose the relationship.

Example:

```text
hablador

Derived from:
hablar + -dor

Type:
agent noun

Meaning:
a person who speaks a lot

[ Analyze hablador ]
```

This prevents accidental navigation and keeps the family graph educational.

---

# 21. Full Family Expansion

The card contains:

```text
View entire family
```

This is a Layer Three action.

For a small family, it may simply expand the card.

For a large family, it should open a more spacious family browser.

The full family view may support:

- filtering
- zooming
- grouping
- searching within the family
- inspecting relationships
- selecting a word for analysis

---

# 22. Word Family Filters

Large families need organization.

Useful categories may include:

```text
All
Common
Verbs
Nouns
Adjectives
Prefixed forms
Learned forms
Historical relatives
```

These categories should only appear when necessary.

A family with eight words does not need a filter toolbar.

---

# 23. Origin / Etymology Section

## Product Role

This section answers:

> Where did this Spanish word come from?

Its role is explanatory and historical.

It should not attempt to reproduce a full scholarly etymological dictionary entry in the default card.

---

## Default State

The card should show:

- source language
- source form
- rough source meaning
- major historical stages
- one or two important changes

Example:

```text
Latin

fabulāre
to speak, converse, tell stories

fabulāre
↓
fablar
↓
hablar
```

The sequence is more important than dense prose.

---

# 24. Etymology as a Story

The origin section should behave like a timeline.

Users should see:

```text
older form
↓
intermediate form
↓
modern form
```

This helps them understand linguistic change visually.

Where relevant, a step may include a short note:

```text
f → h
```

The default card should keep those explanations minimal.

---

# 25. Historical Step Expansion

A user can click a transition or "View historical evolution."

Example:

```text
Why did f become h?
```

Expanded explanation:

```text
In early Castilian, many Latin words beginning with /f/
developed an aspirated sound, which later became silent h.
```

This expansion belongs in the origin card or a larger etymology view.

The base card should remain a narrative summary.

---

# 26. Full Etymology View

A complete etymology view may include:

- inherited vs learned forms
- intermediate Romance forms
- Old Spanish spellings
- sound changes
- morphological restructuring
- semantic shifts
- references
- related Latin forms
- competing etymological hypotheses

This is Layer Three.

The dashboard should only link to it.

---

# 27. English Root Relatives Section

## Product Role

This section is frequently misunderstood and must have a strict product definition.

It does **not** provide English translations.

It provides English words that share a historical root with the Spanish word, usually through Latin or another common ancestor.

Example:

```text
Spanish: hacer
Latin: facere
English relative: factory
```

The relationship exists because both are historically connected to Latin forms built on the same root.

---

# 28. Why This Section Exists

This section serves two purposes.

## Linguistic Purpose

It shows cross-language historical relationships.

## Learning Purpose

It gives English-speaking learners an existing mental anchor.

Example:

```text
factory
→ place where things are made
→ facere = make/do
→ hacer = make/do
```

This is much more valuable than simply showing:

```text
hacer = do/make
```

because the user probably already has a translation tool.

---

# 29. Naming the Section

Preferred product labels:

- English Cognates
- English Root Relatives

If the product uses "Cognates," provide a tooltip.

Example:

```text
Cognate
A word historically related to another word through a shared ancestor.
```

The term "English Derivatives" should be avoided when it implies that the English word derives from the Spanish word.

---

# 30. Default English Relative List

The main card should show only a few strong examples.

Typically:

```text
3–5 words
```

Each item should contain:

```text
factory
from Latin factor / facere
connected through the idea of making
```

The goal is not to maximize quantity.

The goal is to maximize mnemonic value.

---

# 31. Showing the Shared Root

The shared root should be explicit.

Preferred structure:

```text
             Latin facere
              /         \
         Spanish hacer   English factory
```

or a compact textual equivalent:

```text
hacer ← facere → factory
```

This prevents users from assuming the English word came through Spanish.

---

# 32. Expanding an English Relative

Clicking an English word opens a relationship explanation.

Example:

```text
factory

Shared source:
Latin facere

Spanish:
hacer

Historical connection:
factory ultimately comes from Latin forms related to facere,
"to make or do."

Memory link:
A factory is a place where things are made.
```

This should appear as:

- popover
- inline expansion
- compact side panel

It should not replace the main analysis.

---

# 33. More English Relatives

The default card ends with:

```text
Show more cognates
```

This is Layer Two if the list remains modest.

If there are many relatives, the control may open a larger list.

The ranking should favor:

- familiar English words
- clear historical relationships
- memorable semantic links

Obscure cognates are lower priority even if linguistically valid.

---

# 34. Mnemonic Section

## Product Role

The mnemonic section converts the analysis into a memory tool.

It should answer:

> How can I remember this word using the linguistic relationships already shown?

The mnemonic is not a separate trivia generator.

It should reuse:

- etymology
- cognates
- morphology
- family relationships

---

# 35. Mnemonic Style

Preferred mnemonic:

```text
hacer comes from Latin facere.

Factory comes from the same root.

A factory is where things are MADE.

hacer = to make / do
```

This creates a meaningful chain.

The product should prefer **true linguistic relationships** over arbitrary invented associations whenever possible.

---

# 36. Default Mnemonic State

Only one mnemonic should appear by default.

It should be:

- short
- scannable
- based on the current word
- understandable without linguistic training
- connected to another section of the page

A mnemonic card should not become a paragraph-heavy explanation.

---

# 37. Mnemonic Expansion

Possible controls:

```text
Show another mnemonic
Explain this mnemonic
```

"Show another mnemonic" replaces the current mnemonic within the card.

"Explain this mnemonic" may reveal why the relationship is historically valid.

The card should not accumulate multiple mnemonics vertically.

One visible mnemonic at a time keeps the page calm.

---

# 38. Nearby Forms / Quick Conjugation

## Product Role

This section helps users recognize forms closely related to the current search.

It is especially useful for verbs.

The default row is not intended to replace a conjugation dictionary.

It is a **quick recognition strip**.

---

## Example

For `hablábamos`, the page might show nearby forms such as:

```text
hablo
hablas
habla
hablamos
habláis
hablan
```

The exact selection may depend on the search.

---

# 39. Choosing Nearby Forms

The product should prefer forms that help establish the pattern.

For a verb, this might mean:

- same tense paradigm
- common present forms
- forms nearest the searched form
- forms useful for contrast

The selection should be limited.

Recommended:

```text
6–8 items
```

---

# 40. Full Conjugation Expansion

The strip ends with:

```text
View complete conjugation
```

This is Layer Three.

Complete conjugation is too large for the dashboard.

The full view should organize forms by:

```text
Mood
→ Tense
→ Person
```

Example:

```text
Indicative
  Present
  Preterite
  Imperfect
  Future

Subjunctive
  Present
  Imperfect

Imperative

Non-finite
```

The user should be able to return to the word analysis easily.

---

# 41. Cross-Section Relationships

The cards should not behave as isolated widgets.

The interface is strongest when the sections reinforce one another.

Example for `hacer`:

```text
Morphology
hacer

Origin
facere

English Root Relative
factory

Mnemonic
factory → making → facere → hacer
```

The product should intentionally reuse the same root across these sections.

This creates coherence.

---

# 42. Cross-Highlighting

When useful, selecting an item in one section may visually connect it to another.

Examples:

- clicking `facere` in Origin highlights the `facere` root in English Relatives
- clicking `factory` highlights the shared root
- selecting `hacedor` in the family identifies its derivational connection to `hacer`

Cross-highlighting should be lightweight.

It should not cause the page to rearrange.

---

# 43. Section Expansion Rules

Every "show more" interaction should follow one of three patterns.

## Pattern A: Inline Accordion

Use when:

- information is a direct elaboration of the card
- expansion is modest
- user should keep surrounding context visible

Examples:

- morpheme breakdown
- etymology explanation
- alternate analyses

---

## Pattern B: Contextual Detail Panel

Use when:

- user clicked a single item
- detail is about that item
- the main card should remain visible

Examples:

- family node details
- English cognate explanation
- suffix explanation

---

## Pattern C: Dedicated Deep View

Use when:

- content becomes large
- user may spend time exploring
- the dashboard would become unwieldy

Examples:

- full word family
- complete conjugation
- complete etymology graph

---

# 44. Expansion Should Not Cause Chaos

When a card expands:

- other cards should not jump unpredictably
- the user should not lose scroll position
- the expanded content should feel attached to the action that opened it
- closing the expansion should restore the previous state

Expansion should reveal information, not transform the interface into a different product.

---

# 45. Default Screen Density

The dashboard should aim to make one desktop viewport highly informative.

However, fitting more content is not the same as shrinking everything.

Density should come from:

- good hierarchy
- compact typography
- restrained padding
- selective summaries
- meaningful truncation
- horizontal use of space
- progressive disclosure

Density should **not** come from:

- 11px body text
- 30 visible graph nodes
- full conjugation tables
- nested accordions everywhere
- excessive pill badges
- multi-line metadata in every row

---

# 46. The Rule for Default Visibility

A field belongs on the default dashboard if it strongly helps one of these jobs:

1. identify the form
2. understand the grammar
3. recognize the family
4. understand the origin
5. create a memory connection
6. recognize nearby forms

If a field primarily exists for completeness, it belongs behind an expansion.

---

# 47. Search History

Recent analyses are a utility, not a major product surface.

The user should be able to quickly return to previously explored words.

A compact popover might show:

```text
Recent

hacer
hecho
satisfacer
hablar
poner
```

Selecting one reloads that analysis.

The list should remain short.

A longer history can exist elsewhere.

---

# 48. Favorites

Favorites allow the user to save useful words or families.

The default object to favorite should normally be the lemma.

Example:

```text
searched: hablábamos
favorite: hablar
```

This avoids a favorites list full of separate inflections.

The product may later allow users to save:

- a family
- a mnemonic
- a specific form

but lemma-level saving should be the simplest default.

---

# 49. Audio

Where pronunciation is available, audio belongs close to the primary word.

It should remain a secondary action.

Audio should not be duplicated across every related node by default.

For related words, audio can appear on hover or inside the item detail.

---

# 50. Unknown or Unsupported Words

The analyzer should degrade gracefully.

If the word is not recognized:

```text
We couldn't confidently analyze “x”.

Try:
- checking the spelling
- searching the lemma
```

If partial information exists, show it.

Example:

```text
Morphological analysis available
Etymology unavailable
```

The page should not fail as a whole because one enrichment source is missing.

---

# 51. Missing Word Family

If no reliable family can be produced:

```text
No reliable word family is available for this entry yet.
```

Do not fill the space with speculative relationships.

The same rule applies to cognates and etymology.

Accuracy is more important than visual completeness.

---

# 52. Missing English Relatives

The product should explicitly allow:

```text
No useful English root relatives found.
```

This is preferable to showing weak, remote, or misleading relationships.

The English section exists to provide value, not to guarantee content for every Spanish word.

---

# 53. Confidence and Uncertainty

When the linguistic data contains uncertainty, the product should communicate it.

Useful labels include:

```text
Most likely
Alternative analysis
Possible historical relation
Disputed origin
Uncertain
```

Avoid pretending linguistic analysis is always binary.

However, uncertainty should remain proportional.

A high-confidence everyday form should not be covered in warning labels.

---

# 54. Sources

Sources are important for trust but low priority for the main page.

They should be accessible through:

```text
Sources
```

at the card or analysis level.

Sources should typically be Layer Two or Layer Three.

The default dashboard should not visually resemble an academic citation system.

---

# 55. Mobile Product Structure

Mobile uses the same information architecture but a different priority order.

Suggested sequence:

```text
Search
Morphological Analysis
Word Family
Mnemonic
Origin
English Root Relatives
Nearby Forms
```

Mnemonic moves upward because its immediate learning value is high.

---

# 56. Mobile Family Representation

A radial graph should not be forced into a narrow screen.

Instead, the preview can become:

```text
hablar

Related words
[ hablante ]
[ hablado ]
[ hablador ]
[ inhablable ]

View full family
```

The full graph can open in a dedicated view.

The product concept remains unchanged even though the visualization changes.

---

# 57. Mobile Expansion Behavior

Inline expansions should generally become vertical.

Contextual popovers may become bottom sheets.

Large views remain dedicated.

The information hierarchy must remain the same.

---

# 58. Product Navigation Philosophy

The analyzer should minimize hard navigation.

The user should feel that they are exploring a connected linguistic object.

Most actions should therefore be:

- reveal
- inspect
- expand
- compare
- analyze related word

not:

- open unrelated page
- switch application mode
- leave the analysis context

---

# 59. Analyzing a Related Word

When the user chooses:

```text
Analyze hablador
```

the main page becomes an analysis of `hablador`.

The previous word should remain easy to return to through history.

This creates an exploration loop:

```text
hablar
→ hablador
→ hablar
→ palabra
→ etc.
```

The product should encourage this kind of traversal.

---

# 60. Product Mental Model

The simplest mental model is:

```text
Every analyzed word is a hub.
```

Around it are:

```text
Grammar
Family
History
English relationships
Memory
Forms
```

The dashboard is a visualization of that hub.

Any future feature should fit into this model or justify why it deserves a new mental category.

---

# 61. Page State Model

The analyzer page can exist in several product states.

## Empty State

Before analysis:

- prominent search
- short product explanation
- optional examples

## Loading State

After submission:

- persistent layout
- card-level skeletons
- no full-screen interruption

## Complete State

All major cards populated.

## Partial State

Some enrichment sections unavailable.

## Ambiguous State

Primary interpretation plus alternate possibilities.

## Error State

Unable to analyze the word meaningfully.

The layout should remain recognizable across states.

---

# 62. Initial Empty State

The empty page should not show meaningless blank cards.

Instead:

```text
Analyze a Spanish word

Try:
hacer
hablábamos
hecho
satisfacer
```

Optionally explain:

```text
See morphology, word families, origins, English root relatives,
and memory connections.
```

Once analysis begins, the full dashboard appears.

---

# 63. Loading Philosophy

The user should see results incrementally if different sections become ready at different times.

For example:

```text
Morphology appears
Word family appears
Origin appears
Cognates appear
```

This reinforces that the sections are enrichments around a central analysis.

The product should not hide an already-useful morphological result while waiting for etymology.

---

# 64. Section Ownership

Each section must have a clear job.

This prevents duplicate information.

## Morphology owns:

- grammatical interpretation
- lemma
- internal form structure

## Word Family owns:

- modern Spanish lexical relationships

## Origin owns:

- historical development

## English Relatives owns:

- English words sharing the historical root

## Mnemonic owns:

- memory connection derived from the analysis

## Nearby Forms owns:

- quick recognition of neighboring inflections

If two sections begin showing the same information, one of them should be simplified.

---

# 65. Product Rules for Word Family vs Conjugation

This distinction is especially important.

## Word family:

```text
hacer
hacedor
deshacer
rehacer
hecho
hechura
```

## Conjugation / forms:

```text
hago
haces
hace
hacemos
hacía
hicieron
```

Inflected forms can appear in the family context when relevant to the user's query, but they should not dominate the family view.

The product must preserve the distinction between:

```text
same lexical family
```

and:

```text
same lexeme, different grammatical form
```

---

# 66. Product Rules for English Relationships

The English section should never become:

```text
Spanish → English dictionary
```

Bad:

```text
hacer
do
make
perform
```

Good:

```text
hacer ← facere → factory
hacer ← factum → fact
hacer ← facere → manufacture
```

The shared historical relationship is the feature.

---

# 67. Product Rules for Mnemonics

Mnemonics should preferably derive from real information already on the page.

Preferred sources:

1. English cognate
2. Latin root
3. recognizable Spanish derivative
4. morphological structure
5. semantic evolution

Arbitrary sound-alike mnemonics should be a fallback, not the default.

---

# 68. Product Rules for Etymology

The default origin card should communicate:

```text
source
path
important transformation
```

It should not attempt to communicate every scholarly nuance.

The deeper view can contain technical detail.

---

# 69. Product Rules for Graphs

Graphs are useful when relationships are the content.

They should not be used merely because the product has data.

Use a graph for:

- word families
- etymological branches
- shared-root relationships

Do not use graphs for:

- conjugation tables
- simple morphology fields
- definitions

---

# 70. Product Rules for Labels

Use plain language first.

Examples:

Preferred:

```text
Other possible analyses
View entire family
View historical evolution
Show more cognates
View complete conjugation
```

Avoid:

```text
Expand derivational ontology
Inspect alternate parsing candidates
Render extended lexical graph
```

The product can be linguistically sophisticated without making its controls academic.

---

# 71. Product Rules for Terminology

Technical terms are allowed in content when they are useful.

Controls should remain approachable.

Example:

Content:

```text
Lexeme
Morpheme
Cognate
```

Control:

```text
View morphological decomposition
```

not:

```text
Inspect morphemic segmentation
```

---

# 72. Section Size Philosophy

Card size should reflect conceptual importance.

Largest:

- Morphology
- Word Family

Medium:

- Origin
- English Relatives
- Mnemonic

Compact:

- Nearby Forms
- utility sections

This hierarchy should remain even if the visual design changes.

---

# 73. Interaction Priority

The most valuable interactions are:

1. search another word
2. inspect a family relationship
3. analyze a related word
4. inspect morphological decomposition
5. understand origin
6. inspect English connection
7. open complete family
8. open complete conjugation

The interface should not bury the first four beneath secondary controls.

---

# 74. Hover vs Click

Hover may preview.

Click should commit to inspection.

Example family node:

Hover:

```text
highlight path to lemma
```

Click:

```text
open relationship details
```

This distinction allows the graph to feel responsive without triggering unwanted navigation.

---

# 75. Deep-Linking Behavior

Each analyzed lemma or form should ideally have a stable route.

Conceptually:

```text
/analyze/hablabamos
```

or similar.

A user should be able to bookmark or share the current analysis.

The document does not prescribe URL structure, only the product behavior.

---

# 76. Returning From Deep Views

If the user opens:

- full family
- conjugation
- etymology detail

they should return to the same word and the same approximate dashboard position.

Deep exploration should feel reversible.

---

# 77. Future Features and Placement

When adding future capabilities, place them according to their conceptual job.

Examples:

## Corpus sentences

Likely belongs to a new usage/examples layer or within Morphology.

## Frequency

May appear as lightweight metadata near the word.

## Register

May appear near lexical information.

## Synonyms

Should not be mixed into Word Family because synonymy is not morphological relationship.

## Translation

If added, keep it distinct from English Root Relatives.

This separation is important.

---

# 78. Product Anti-Patterns

Avoid these product mistakes.

## Anti-pattern 1: Everything visible

Showing every available field by default destroys hierarchy.

## Anti-pattern 2: Everything hidden

If users must click five times to understand the word, the dashboard loses its value.

## Anti-pattern 3: Card duplication

If Origin, Cognates, and Mnemonic repeat identical paragraphs, the product feels padded.

## Anti-pattern 4: Graph overload

A 70-node family graph on the dashboard is not informative.

## Anti-pattern 5: Translation confusion

English relatives must not look like translation equivalents.

## Anti-pattern 6: Academic tone everywhere

The product should expose linguistic depth without requiring linguistic expertise.

## Anti-pattern 7: Excessive page changes

Small questions should be answered in place.

---

# 79. Product Acceptance Criteria: Main Dashboard

A successful default analysis should allow a new user to answer, within a few seconds:

- What word did I search?
- What is its base form?
- What grammatical form is it?
- What are several important related Spanish words?
- What historical word did it come from?
- Is there a useful English word connected to that origin?
- Is there an easy memory connection?

If the default screen does not answer these questions, the information hierarchy should be reconsidered.

---

# 80. Product Acceptance Criteria: Morphology

The Morphology card is successful if:

- searched form is immediately obvious
- lemma is visible without expansion
- main grammatical interpretation is readable at a glance
- detailed segmentation exists but does not dominate
- ambiguity is represented without overwhelming the user

---

# 81. Product Acceptance Criteria: Family

The Family card is successful if:

- lemma is visually central
- 6–10 useful relatives can be scanned quickly
- user's searched form can be located when relevant
- clicking a node explains the relationship
- complete family is available through a deliberate expansion

---

# 82. Product Acceptance Criteria: Origin

The Origin card is successful if:

- source language is obvious
- source form is visible
- historical path is understandable
- deeper explanation is optional
- card does not become a dense etymological essay

---

# 83. Product Acceptance Criteria: English Relatives

The English section is successful if:

- user understands these are historical relatives, not translations
- shared root is visible
- examples are familiar and useful
- each relationship can be explained
- low-quality speculative relationships are omitted

---

# 84. Product Acceptance Criteria: Mnemonic

The mnemonic is successful if:

- it is short
- it uses information from the analysis
- it helps connect Spanish to something memorable
- it does not require a long explanation
- another mnemonic can be requested without cluttering the page

---

# 85. Product Acceptance Criteria: Forms

The forms strip is successful if:

- user sees useful neighboring forms
- complete conjugation is easy to access
- default view remains compact
- it does not duplicate the word-family function

---

# 86. Coding Agent Reference Rules

When a coding agent makes changes, it should preserve the following rules unless the product specification is explicitly changed.

1. **The searched word remains the main visual anchor.**
2. **Morphology and Word Family remain the two strongest default sections.**
3. **English content represents shared historical roots, not direct translation.**
4. **The dashboard shows representative subsets, not exhaustive datasets.**
5. **Small expansions stay local.**
6. **Large explorations get dedicated space.**
7. **Word family and conjugation remain conceptually separate.**
8. **Mnemonic content should use real linguistic relationships whenever possible.**
9. **Missing data should be admitted rather than filled with weak guesses.**
10. **The layout should feel like one connected analysis, not a collection of unrelated widgets.**
11. **Deep detail must remain available without becoming default clutter.**
12. **A user should receive meaningful value without clicking anything after search.**

---

# 87. Summary Product Model

The entire product can be reduced to the following structure:

```text
SEARCHED WORD

1. WHAT IS IT?
   Morphological Analysis

2. WHAT IS IT RELATED TO IN SPANISH?
   Word Family

3. WHERE DID IT COME FROM?
   Origin / Etymology

4. WHERE ELSE CAN I SEE THAT ROOT?
   English Root Relatives

5. HOW CAN I REMEMBER IT?
   Mnemonic

6. WHAT OTHER FORMS SHOULD I RECOGNIZE?
   Nearby Forms / Conjugation
```

And each category follows the same interaction rule:

```text
Useful summary
↓
Local explanation
↓
Deep exploration
```

That hierarchy is the core of the product.

As the analyzer becomes more sophisticated, the amount of linguistic data may grow dramatically. The default page should not grow at the same rate.

The product should become **deeper**, not merely **busier**.
