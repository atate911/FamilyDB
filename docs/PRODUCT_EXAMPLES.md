# Examples of the intended FamilyDB experience

Captured from the owner's product discussion.

These are illustrative requests, not an exhaustive feature list, a committed roadmap, or a
claim about what the app supports today. They describe the breadth of the intended experience
and should inform design decisions as the app grows. They are not actual scheduling or reminder
instructions, verified event listings, or personal health facts to enter into household memory.

## Guiding scenario

> I'm bored. What should I do this afternoon?

The aspiration is for the app to bring together the preferences of everyone involved, location,
saved ideas, calendar commitments, previously generated options, current real-world opening
hours and availability, travel and traffic, and novel possibilities that fit the people asking.
It should do the useful research and reasoning a thoughtful person would do, then offer a small
number of practical choices with clear reasons and uncertainties.

This is a guiding light, not the app's single focus. Remembering intentions, helping with
ordinary decisions, arranging plans, and following through on errands and obligations matter too.

## Requests in the owner's words

- "what restaurants did we want to try that we should consider now?"
- "The girls are bored an want something fun, what did they want to do?"
- "Give me something expected we could do right now that we'd love."
- "I need a restaurant for Friday night, something date-night worthy but not too expensive or pretentious"
- "I want sushi, what are some good options that are open now"
- "we don't know what type of food we should look for in a restaurant, can you make a reasonable recommendation?"
- "I heard there's a good movie at the Kiggens theater, should be book it?"
- "Beck is playing at the Crystal Ballroom on the 18th of November. Add this to my schedule and set a reminder a week before."
- "remind me on Tuesday that we need paper towels."
- "One of these Saturday mornings I need to get my knife sharpened at the Farmer's Market."
- "Don't let me forget to make a dentist appointment."
- "Next time I have some free time, I need to schedule my colonoscopy"

Wording is preserved, including "expected"; do not silently treat it as a confirmed request for
"unexpected." Novel discovery is separately part of the guiding scenario above. Relative dates,
event details, participants, and reminder times are intentionally unresolved in these examples.

## Design implications to explore

The examples span recalling saved wishes, choosing between options, discovering new ones,
checking feasibility now or later, scheduling confirmed plans, delivering timed reminders,
and retaining flexible tasks until there is a suitable opportunity. A request to schedule an
appointment is distinct from the appointment itself; a someday intention is distinct from a
confirmed calendar commitment.

The owner favors a layered design: specialized parts handle specific responsibilities, pass
work between layers, and return useful results. The highest-level decision-making approach is
still an open design question: how should the app interpret a broad request, decide which
specialists and information sources to consult, and coordinate them for the best outcome?

The approach taken so far is AI interpretation and delegation within program-enforced
permissions, budgets, and recovery rules (`docs/AI_CALLS.md`). The experience should make clear
what was checked, why an option fits, what remains uncertain, and what was actually done.

Use these examples to keep future proposals grounded in the owner's intended experience.
Choose implementation priorities separately; do not assume their order here implies priority
or that every example needs its own feature, model call, or architectural layer.

## Free-form capture and contextual recall

People must be able to save unfinished thoughts without picking a category first.
Restaurants, bars, cuisines, food carts and pods, neighborhoods, McMenamins passport
locations, special occasions, kids activities, specific places and general directions
all belong. A single idea may fit several contexts. Preserve original wording and
attribute who suggested it; infer supported tags without inventing facts.

When asked what to do or where to eat, retrieve relevant saved ideas before considering
new discoveries. An idea about a neighborhood need not become a specific venue.
A task kept for a window is brought up when that window comes round free (the `nudges` job);
nudging a saved idea when the context fits is a later capability.
