# Brief standard

The owner reads the brief the morning before the meeting, on their phone, in a minute. It tells them who they are
meeting, what that person told us, where referrals could fit, the owner's own notes for the meeting and one practical
point. Then 5 questions they can ask.

## The brief: five short paragraphs, 120 to 220 words in all
1. **Identity line.** `<Full name>, <role>, <business>, <town or area>. <networking group>.` If the role is not
   confirmed, say so in the line, for example "bookkeeper (title not confirmed)".
2. **Who they are.** Two or three sentences on what the business does, for whom and where, from the business's own pages.
   Concrete beats general: services, client types, number of offices, network or franchise, how new the business is.
3. **What they told us.** One to three sentences from their own emails in `conversation` (paraphrased, never pasted):
   what they want from the meeting, anything they said about their role ("not the owner"), the place or time they
   suggested. Small personal details they shared with the owner themselves may stay if they help the conversation.
4. **Fit.** Start with "Fit: referrals first." (or "Fit: referrals both ways." when it is clearly two-way): who the owner
   could send them and who they could send the owner's business. If their business overlaps the owner's (for example
   both offer admin or IT services), frame the owner's business as complementary. Mark every inference "(a guess)".
5. **Practical** or **Note.** One line that helps the meeting: "they have never used Google Meet, so send joining steps",
   "ask how the two business names fit together; don't assume", "new to the group, so a short agenda will help".

When the job has `prep_notes`, a "Your notes:" paragraph goes just before Practical (see The owner's prep notes) and the
brief may run to 260 words.

Do not put sources, doubts or links in the brief text: they go in `sources` and `not_confirmed`, and the door adds them
underneath.

## The owner's prep notes
`prep_notes` is the sheet's Prep Notes: what the owner wants from this meeting, typed before it by the owner or by the
operator for them. Things to find out, things to show or tell them, reminders. They are the owner's, so the brief
carries every point:
- **"Your notes:"** paragraph, just before Practical: each point in plain words, typing fixed, meaning kept, nothing
  added. For example the note "would love to know how she prices her packages. show her our onboarding checklist"
  becomes "Your notes: find out how she prices her packages; show her the onboarding checklist you give new clients."
- **Questions:** each thing the owner wants to find out also becomes question 3 or 4 (see The 5 questions). Things to
  show or tell stay in "Your notes:"; the Practical line may say what to have ready (slides to share on a video call, a
  printout for a coffee).
- They are the owner's plans, not facts about the person, and restating them is not a pitch. Never write a plan as if it
  had already happened. List them in `sources` as "the owner's prep notes (sheet)".

`meeting_notes` on a booked meeting are notes from an earlier meeting with them: use them in a follow-up brief (see
Follow-up meetings).

## The 5 questions
The owner asks them in a relaxed conversation. Each is one open sentence (not yes or no), 15 to 300 characters, written
for this person: their business, their clients, their area, their group, what they told us. The shapes below show the
kind of question, not the wording; a sharper, more personal question always beats a stock one.
- **Questions 1 to 3: know them and help them.** What they do best and for whom, what a great referral looks like for
  them and what someone would say that tells the owner to introduce them, who they already work with or refer to, how
  the group is going for them. In a follow-up, go deeper instead (see Follow-up meetings).
- **Question 4: where their time goes** in their work (the angle of the owner's business), asked out of interest.
- **The owner's own questions come first:** each thing their prep notes say they want to find out takes the place of
  question 3 or 4, in their meaning, worded for the conversation.
- **Question 5, always: the introduction ask.** Ask who in their network would need what the owner's business does or
  would simply enjoy meeting the owner, and whether they would be happy to make the introduction. Name the people in
  their world (their clients, the partners they refer work to, people in their group) and keep it warm and easy to say
  yes to. It must use the word "introduce": the door refuses a brief whose question 5 is not an introduction ask.
- Never a pitch, never "would you like help with".
- Good shapes: "Who is your ideal client in <area>, and what is usually going on in their business when they need
  you?", "What might a business owner say to me that tells me I should introduce them to you?", "Which people do you
  already refer work to, and who are you still looking for?", "When <their core task>, where does most of your time
  go?", and for question 5 "Who in your network, perhaps <their clients or partners>, is buried in admin or would
  simply enjoy meeting me, and would you be happy to introduce us?"

## Example (made up, for the format only)
The job's `prep_notes`: "ask how she onboards new clients. tell her about our cafe owners breakfast in nov"

Brief:
```
Priya Nair, director (from her email signature), Northgate Bookkeeping, Fremantle. Port City group.
Northgate is a two-person bookkeeping practice for trades and hospitality businesses: BAS, payroll and Xero setup. Its website says it opened in 2024.
She told us she joined the group in July, prefers a morning coffee near Fremantle station, and is keen to meet people who work with cafes.
Fit: referrals both ways. Her cafe clients may struggle with rosters and supplier invoices (a guess), and your clients often need a bookkeeper. You sort out the systems, she keeps the books.
Your notes: find out how she brings a new client on board; tell her about the cafe owners' breakfast in November.
Practical: she said she is new to 1-2-1s, so a short agenda will help.
```
sources: `["northgate.example.com (home, about)", "Port City group member page", "her emails of 3 and 6 Oct", "the owner's prep notes (sheet)"]`
not_confirmed: `["her title (email signature only)"]`
Questions:
1. What made you choose trades and hospitality as Northgate's focus?
2. What does a great referral look like for you, and what would an owner say that tells me to introduce them?
3. How are you finding the Port City group since July, and which connections have helped most so far?
4. When a new client comes on board, how do you get them from a box of receipts to clean books, and where does that time go?
5. Which of your cafe or trades clients are drowning in rosters and invoices, or who else in your network would enjoy meeting me, and would you be happy to introduce us?

## Calendar lines
Lines in `conversation` that read `<date>, Calendar: ...` come from the owner's calendar (added by the operator): they
give the meeting's time, place or video link. Put them in the Practical line (for example "Practical: Thu 12 Mar,
10:30am at Bluegum Lane Cafe, Fremantle"). They are facts, not guesses.

## Follow-up meetings
When `conversation` shows they have already met the owner (for example "It was great meeting you today", a Calendar line
saying "follow-up", or an accepted meeting whose date has passed), write a follow-up brief instead of a first-meeting one:
1. **Identity line** as usual, then "Follow-up to your first meeting on <date>." (or "...your first meeting" when the
   date is not known).
2. **What we know from the first meeting:** only what is written down: their own words since, anything the owner
   summarised or promised in their emails, and `meeting_notes` if the row has them. Never invent what was said; if
   nothing is written, say "No notes from the first meeting on the sheet."
3. **What is open now:** promises, introductions, and the reason for this meeting (for example "a video call to learn
   more about his three service areas").
4. **Fit**, as usual (referrals first, guesses labelled).
5. **Your notes:** when there are prep notes, then **Practical:** the time, place or link from the Calendar line.
The questions go deeper than a first meeting: the specific referrals they want, introductions the owner could make, how
their services work in practice, what has changed since the first meeting. Do not repeat the getting-to-know-you
questions. Question 5 is still the introduction ask, now as specific as what the owner has learned allows.

## Checklist before you deliver
- The person is tied to this business by the domain, a page or their own words, or the brief says the identity is not
  confirmed.
- Every fact is on a page you opened or in their own words; every inference says "(a guess)".
- Nothing about private life you found yourself; nothing about health, family, money, legal matters or reviews.
- 120 to 220 words (260 with "Your notes:"), short paragraphs, the identity line first.
- Every point of `prep_notes` is in "Your notes:", and each thing the owner wants to find out is question 3 or 4.
- 5 questions: 1 to 3 know them and help them, 4 where their time goes, 5 the introduction ask with the word
  "introduce"; specific to this person, no stock wording, no pitch.
- No em or en dashes, no emojis, no email addresses, phone numbers or links in the brief text.
