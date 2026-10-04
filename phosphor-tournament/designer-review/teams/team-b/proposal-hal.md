# Proposal: Hal

**The idea:** A calm, modern app in which phosphor green is the machine's voice: whatever Vera says or works out glows on a green screen, and everything the family reads, types and presses is plain and easy to read.

## The look
- **Type.** There are two typefaces, each with one job. A clean sans (Plex Sans or similar) is used for everything the family writes, reads and presses. A green monospace, with faint scanlines and a soft glow, is used only for what the machine says: Vera's name tag, readouts, counts and the monitors. Page titles are set in a tall condensed sans, each followed by its count in the accent colour ("Ideas 12", "Things to do 4 · 3 late").
- **Colour.** The page is a near-black green, with panels one step lighter. The only accent is phosphor green. Amber, as on an amber terminal, means only "late" or "needs a look". There is no other colour: no slate-blue selected states and no rainbow of section colours.
- **Structure.** There is one navigation: a top bar on the desktop and bottom tabs on the phone. The bar shows the brand followed by a blinking block cursor. Each page has a title with its count, then one instrument, then content in plain rows.
- **Rules it keeps:**
  1. Each page has one instrument, it shows real data, and its meaning is clear in words within two seconds.
  2. Body text is never set in a pixel or monospace font.
  3. A line, rail or node must mean something (time or distance), or it is not drawn.
  4. Text on a monitor is never clipped. The monitor sizes itself to its readout.
  5. The focus state is a 2px phosphor ring with glow, the same everywhere.

## The pages
- **Home.** "Tell Vera what to plan." heads the writing box, with the ways to start as buttons under it. To the right is the Next up monitor: radar rings at 1, 2 and 4 weeks, "Oaks Park roller rink · Sun 13:00 [tomorrow]", and "3 more" beneath. Under that is a readout strip: Today Sat 3 Oct · Plans 4 · To do 4 · Late 3 (amber) · Ideas 12. Setup is a single-line stepper (1, 2, 3, then "Next: choose your password →"). Below are three columns, Coming up, To do and Lately added. At the bottom is an "Around the house" strip with Wishes, Memory, Family, Status and Settings, each with a single line.
- **Chat.** The conversation is one centred column of about 680px. Vera's messages sit on a faintly green-lit panel with her mono name tag. The family's messages are plain sans, aligned right. A single date line runs down the side. The box to write in stays pinned at the bottom. The kids' conversations are tabs above the thread.
- **Ideas.** The instrument is "The line from home": a horizontal green scale from home to 3 h, with each idea a numbered dot. The numbers match the "#" column of the table below. Each idea is one row: icon, name, kind, drive, who it is for and its number. Filters take one row (search, kind, for), and the rest sits behind "More".
- **To do.** The instrument is a small tally screen showing Late 3, This week 0, Later 0 and No date 1. The list has one row per task, with a checkbox, the task, who it is for, the due date (amber if late) and Edit. A green NOW rule separates what is late from what is not.
- **Plans.** The instrument is the Next up monitor. Below it, the month calendar shows today with a lit border, and plans appear as chips with a green edge, the time in mono and the name in sans. A toggle switches between List and Month.
- **Status.** The instrument is the spending gauge: an arc with a needle, reading "$0.00 today · limit $2.00 · average $0.04". Below it are three columns, Who answers, Keys and Connected to, each item with a lit or unlit dot and a meter such as "3 of 4".
- **Settings.** A three-by-three grid of cards, each with an icon, a name, a one-line state and an arrow. "Needs a look" shows in amber.

## Taken from / refused
- **Taken from:** D35, the spending gauge, the to-do tally, and numbered dots that match the list; D30, the line from home in place of a radar; D36, the title with its count, the setup stepper and the summary strip; D17, the readout strip under the box; D34, the Next up monitor with week rings; D37, the bezel's power light as a touch of character.
- **Refused:** two navigations (D34); pixel fonts for anything people must read (D37); off-palette selected states (D36); decorative rails and timelines that mark nothing (D35, D37); charts you have to study (D35's Home dot plot); in-jokes like "Sommaire"; walls of filter chips; making the whole page green and monospace.

## Why it wins
The other designs either glow everywhere and are tiring to read, or play it safe and lose the character. This design gives the green screen a single meaning, the machine talking. That keeps the character on every page while leaving everything the family touches as modern and plain as a good app should be. Each instrument tells the family something true, so the nostalgia earns its place.
