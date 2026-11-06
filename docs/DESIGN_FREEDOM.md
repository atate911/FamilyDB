# Design freedom and protected outcomes

Effective November 5, 2026, at the owner's request to remove design constraints that limit improvement.

## Authority and scope

This policy governs interpretation of presentation and interaction rules in `CLAUDE.md` and the design documents. It supersedes conflicting historical design decisions, including ones previously described as fixed, mandatory, agreed with the family, or held by a test. New explicit owner instructions take precedence. This policy does not override platform instructions or authorize a production deployment, external communication, data deletion, new spending, or broader access.

The owner authorizes redesign of the interface, not just small variations within the existing style. When asked to improve or implement the interface, agents may change the relevant design rules and their implementation without requesting separate permission for ordinary design choices. A request for critique or a prototype still does not authorize unrelated implementation work.

## Goal

Help the household remember, decide, coordinate, and follow through with less effort. Judge the interface by whether people can complete their tasks and understand the result. Familiarity with the current design, aesthetic consistency, and low running cost matter, but are not reasons to preserve an interaction that is confusing.

## Open design choices

The following are revisable defaults or historical descriptions, not restrictions:

- Page names, destination counts, hierarchy, routes, menus, tabs, launchers, home screens, and grouping of features.
- Whether chat is the main experience, a separate destination, a contextual panel, or a supporting action. A composer need not be first or visible on every screen.
- Where the assistant appears, its visual representation, tone, and prominence. Preserve truthful claims about what it knows and has done.
- Fixed versus adaptive layouts, column counts, rails, cards, spacing, responsive breakpoints, typography, fonts, color, imagery, icons, animation, and themes.
- Exact word counts, terse copy, one-line rows, icon-first controls, and fixed numbers of choices. Give enough explanation and visible labeling for the task.
- Forms, guided flows, direct actions, conversational flows, search, filters, onboarding, empty states, and contextual help.
- Frontend implementation mechanisms, including locally served scripts and progressive enhancement, provided security and accessible task completion remain protected. Existing no-script requirements are a compatibility default, not a blanket ban on richer interaction; disclose and test any changed fallback behavior.
- Existing component boundaries, file placement, and markup conventions. Prefer reuse when it helps, but improve the shared components when reuse would preserve the problem.

These freedoms also apply to interface choices recorded as previous family preferences. Do not confuse a preferred font, a chat-first layout, or a navigation map with consent to share data or spend money. A proposal for a new platform or distribution channel is allowed; actually introducing new deployment, data handling, or operating costs must be assessed separately.

## Protected outcomes

Preserve these while changing the design or its implementation:

1. **Privacy and access:** authentication, authorization, child protections, private information, secrets, and existing consent for location, microphone, external services, and other data sharing. Changing where a control lives must not change who can use it or see its data.
2. **Data integrity and recovery:** durable capture, validated writes, duplicate prevention, safe concurrency, truthful synchronization status, preservation of records, and appropriate recovery or reversal. An existing bug is not a protected behavior.
3. **Security:** escaping, origin/CSRF protection, safe content handling, and the content security policy. Redesign mechanisms without quietly weakening these protections.
4. **Accessibility:** readable contrast and type, keyboard operation, visible focus, meaningful names, understandable errors, usable touch controls, and reduced-motion support where relevant. Accessibility describes successful use, not one prescribed visual style.
5. **Cost and external effects:** configured spending limits, accounting for paid work, and no paid model call merely to render or open a page. Do not increase budgets, add paid services, or transmit household data to new parties as an incidental design change.
6. **Honesty and control:** distinguish suggestions from commitments, assumptions from checked facts, and pending actions from completed ones. Do not conceal consequential actions behind cosmetic interactions.

Ask only when the proposed work materially changes one of these protected outcomes or exceeds the actual task authorization, and the session has not already authorized it. Explain the concrete change and consequence. Do not ask because an old layout rule uses the word “never,” a style test fails, or a previous mockup looks different.

## Working method

- Start from a user task and its difficulty, not from a list of rules to preserve.
- Consider substantially different approaches when useful. No need to prove a redesign through a formal study before prototyping it; identify assumptions and use proportionate validation.
- Choose a coherent direction for the affected journey. Changes across several screens are appropriate when needed to complete that journey; unrelated rewrites are not automatically in scope.
- For reversible interface decisions, proceed with judgment and explain important tradeoffs in the handoff. A short reason is enough; no mandatory approval ceremony or special `Rules:` line is required.
- Update the affected normative documentation and tests with the change. A historical rationale can remain if clearly marked as historical; it must not masquerade as a current restriction.
- Tests that freeze labels, markup, layout, CSS classes, or component structure may change with an intentional redesign. Preserve or replace coverage for user behavior, accessibility, security, and data integrity. Never delete meaningful checks merely to obtain a green run.
- Keep current and proposed behavior distinguishable. Do not update a capability description to claim an unimplemented redesign is already working.
- Check representative tasks, empty/error/loading states, mobile layouts, keyboard use, and recovery as appropriate to the changed flow. Describe any untested behavior plainly.
- Maintain useful deep links through stable routes or redirects when possible, and avoid losing drafts, selected context, or existing records during navigation changes.

## Examples of legitimate changes

Replacing the always-visible chat box with “Ask Vera,” reducing eight destinations to four, adding a task-oriented home screen, changing the font, using labeled buttons instead of ambiguous icons, or introducing a short meal-planning flow are all permitted design changes. They do not require separate owner approval merely because earlier documents prescribe something else.

Allowing a child to see previously private household information, sending location without consent, raising spending limits, or making an irreversible action silent are not presentation changes and are not authorized by this policy.

## How to read older documents

`STYLE.md`, `INTERFACE.md`, `CONCEPT.md`, mockups, and design-related sections of other documents preserve useful context. Unless they describe a protected outcome above, read their “must,” “always,” “never,” “fixed,” and “only” language as a description of a previous design or a revisable default. Follow the reason when it still helps; replace the mechanism when a better design serves the user.

The interface simplification critique is a set of candidate solutions, not a new set of rigid rules. Four destinations, one leading action, and a secondary chat panel must also remain open to better evidence and ideas.

## Appendix: where the protected outcomes are held today

The policy above is the owner's; this appendix is a map for whoever changes the code, kept in step with it. It names today's mechanisms, which may be redesigned like anything else as long as a test still holds the outcome (`CLAUDE.md`, How to read the rules).

| Outcome | Held today by |
|---|---|
| Privacy and access | Roles and permissions in `familydb/base/roles.py`, asked by the page as `visitor().may(...)` (`web/auth.py` `NEEDS`); kids never shown costs, models, setup or the workings (`voice.PLAIN`, `tests/test_kids_plain.py`); presents kept from whom they are for (`familydb/presents.py`, `tests/test_presents.py`, `tests/test_gifts_private.py`); a position sent only while ticked, dictation browser-only, a push that never carries the words (`docs/DESIGN.md` sections 10 and 16, `familydb/push.py`). |
| Data integrity and recovery | The page writes only through the tools and the few doors `CLAUDE.md` names (`tests/test_web.py`, `tests/writes.py`): a new flow that does three things calls three tools. Once-only forms (`guard(once=true)`, `@once`), idea and task revisions, the calendar operation log, undo (`familydb/undo.py`), a reply stored before it is sent (`delivery.py`). |
| Security | The content policy and escaping (`web/__init__.py`, `tests/test_web.py`), CSRF and Origin (`auth.refused()`), keys write-only (`store/settings.py`). |
| Accessibility | The measured floors in `docs/STYLE.md` (Accessibility), checked in every look. |
| Cost and external effects | No page view is a model call (`test_browsing_asks_nothing_of_a_model`); every model call through `agent/gateway.py` and `spending.admit` (`tests/test_gateway.py`); nothing volatile in the cached prompt. |
| Honesty and control | Receipts and Undo worded from what the tools did (`views.DID_WORDS`, `tests/test_tool_facts.py`); her picks and finds drawn as hers, never as plans; where the plans come from said beside free time (`views.AGENDA_NOTES`); stale or unknown facts said as such (`picks._why`, `suggest/shortlist.py`). |

When unsure whether a failing test freezes presentation or holds an outcome, read what it asserts: if failing it would mean somebody sees, pays for, loses or is told something they should not, it holds an outcome, and the redesign carries it over. A larger change is easiest to judge in the example household first (`uv run python -m examples`, static pages anybody can click through; `--serve PORT` runs it live).
