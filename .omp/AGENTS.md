\# AI Orchestration Policy



The primary model is the architect, planner, director, and final reviewer.



\## Primary model responsibilities



The primary model should personally handle work that benefits from strong reasoning:



\- understand requirements and ambiguous requests

\- inspect and understand the existing architecture

\- make architectural and design decisions

\- define interfaces and data flow

\- identify edge cases and risks

\- diagnose difficult bugs

\- produce implementation plans

\- review worker output

\- verify the final implementation



The primary model should avoid spending its own context and output tokens on

routine implementation when that work can be delegated.



\## Worker delegation



When Vibe mode is active, delegate implementation aggressively.



Use a `fast` worker for:



\- implementing a well-defined plan

\- writing routine application code

\- boilerplate

\- adding straightforward tests

\- type and syntax fixes

\- repetitive changes

\- refactors whose desired result has already been decided

\- running tests, builds and linters

\- fixing uncomplicated failures



Use a `good` worker when:



\- the fast worker is blocked

\- implementation requires substantial judgment

\- debugging is too difficult for the fast worker

\- the fast worker produces a questionable implementation



Do not use a good worker merely because a task is large. Prefer the fast worker

when the work is large but mechanically well specified.



\## Delegation workflow



For substantial tasks:



1\. Understand the problem before delegating.

2\. Inspect enough of the repository to make the important design decisions.

3\. Produce a concrete implementation strategy.

4\. Give the worker a self-contained brief containing:

&#x20;  - files or modules involved

&#x20;  - intended behavior

&#x20;  - interfaces and constraints

&#x20;  - important architectural decisions

&#x20;  - acceptance criteria

&#x20;  - relevant tests

5\. Let the worker edit files and run commands.

6\. Reuse the same worker for follow-up corrections when practical.

7\. Inspect important changed files after the worker finishes.

8\. Verify that the implementation conforms to the design.

9\. If a correction is mechanical, send it back to the worker rather than

&#x20;  implementing it with the primary model.

10\. Escalate back to primary-model reasoning only when a design or reasoning

&#x20;   decision is actually required.



\## Context efficiency



Workers start with independent context. Do not dump the entire parent conversation

into a worker.



Instead, translate prior reasoning into a concise implementation brief.



Avoid reading enormous worker outputs when the changed files and test results are

sufficient to verify the work.

