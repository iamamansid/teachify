# Launch plan — Teachify v0.1

Goal: a **24–48h velocity burst**, not a slow drip. GitHub trending rewards stars + forks in a short window.

## Pre-launch (T-2 days)

- [ ] Record the 20-sec demo (see script below). Export as GIF + MP4 (for X/Reddit/HN).
- [ ] Write the "How I built Teachify" post (Dev.to / Hashnode / personal blog). Publish T-2 so Google indexes it before launch traffic.
- [ ] Prepare the repo: README with demo above the fold, `npm install && npm run build` verified on a clean machine, LICENSE, CONTRIBUTING note.
- [ ] Line up 5–10 friends to try it in the first 2 hours and star + comment honestly. No fake stars, no engagement pods — real tries only.
- [ ] Draft Show HN, Reddit, X, LinkedIn posts (below). Do not post early.

## Launch day (T0, morning)

Post in this order, all within the same morning where possible:

1. **Hacker News — Show HN** (8–9 AM ET is the classic window).
   Title: `Show HN: Teachify — Teach Mode for any LLM (same prompt, guided instead of done)`
   Body: problem (autopilot deskilling) → demo GIF → install (3 commands) → "The AI guides. You type. You learn." → ask for feedback + task ideas.
   Stay online for 2h and reply to every comment.
2. **Reddit** — r/programming, r/learnprogramming, r/ClaudeAI / r/cursor as relevant. Tailor the title per subreddit; lead with the problem, not marketing copy. Ask for task ideas.
3. **X** — thread: problem → 20-sec video → install → tools list → "you type, AI guides". Tag no one unless genuinely relevant.
4. **LinkedIn** — narrative version: junior devs + deskilling + what Teachify changes. Link to repo.
5. **Product Hunt** — Day 2–3, Developer Tools category (optional; don't split Day-1 attention).

## Demo video script (20 sec)

> 0–3s: "LLM agents write all your code. You learn nothing."
> 3–8s: Screen: `Teach Mode on. Implement rate limiting.` → AI breaks it into steps, shows Step 1/5.
> 8–14s: Learner types the line. AI: "✅ Verified. Step 2/5…"
> 14–18s: Learner finishes. AI quizzes: "What does rate limiting actually protect?" Learner answers.
> 18–20s: "Teachify. The AI guides. You type. You learn." + repo URL.

Lead with Teach Mode on a **fresh prompt** (rate limiting), not just a canned task — that is the product. Show the canned tasks only as "or try a demo task instantly".

Keep the video to **one task, one pass, no setup**. If setup takes >10s, pre-record the install.

## What to measure (first week)

- Stars, forks, clones (GitHub Insights), issues, PRs (especially new-task PRs).
- Honest user quotes: "I finally understood @RestController" — screenshot + save to `docs/GTV-EVIDENCE.md` tracker.
- Drop-off: where do learners stall? (Step with most hints / attempts.)

## What NOT to do

- Don't buy stars / fake engagement. Assessors, maintainers, and HN all spot it, and it poisons GTV evidence.
- Don't launch without the demo video. A wall of text doesn't spread.
- Don't promise the browser overlay / pixel cursor in v0.1. Ship what exists.
