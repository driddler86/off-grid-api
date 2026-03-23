# Off-Grid Scout — Launch Marketing Copy

*Last updated: 23 March 2026*

---

## Table of Contents
1. [Reddit Post — Off-Grid Communities](#1-reddit-post--off-grid-communities)
2. [Reddit Post — Indie Dev / Side Project](#2-reddit-post--indie-dev--side-project)
3. [Facebook Group Post — UK Off-Grid Living](#3-facebook-group-post--uk-off-grid-living)
4. [Product Hunt — Tagline & Description](#4-product-hunt--tagline--description)
5. [Twitter/X Launch Thread](#5-twitterx-launch-thread)
6. [Waitlist Email — Launch Announcement](#6-waitlist-email--launch-announcement)

---

## 1. Reddit Post — Off-Grid Communities

**Subreddits:** r/OffGrid, r/OffGridUK, r/homestead

**Title:** I got tired of manually checking flood maps, soil data, and planning records for every land listing — so I built a tool that does it automatically

---

Hey everyone,

Like a lot of you, I've spent the last couple of years seriously looking at land in the UK with the goal of going off-grid. And if you've been through that process, you know the drill:

You find a plot on Rightmove that looks promising. Lovely photos. Reasonable price. Then you spend the next two hours cross-referencing flood risk maps, checking the Environment Agency data, looking up BGS borehole records for water table depth, pulling solar irradiance data, reading through the local planning authority's stance on agricultural dwellings, and trying to work out if that access track actually has rights of way.

Then you do it again. And again. For dozens of listings.

I'm a developer by trade, and after the 50th time doing this exact same research loop, I thought — why am I not automating this?

So I built **Off-Grid Scout**. It's a Chrome extension that sits on top of the property sites you're already browsing — Rightmove, Zoopla, OnTheMarket, Savills, PrimeLocation, and PlotFinder. When you're looking at a land listing, you click the extension and it pulls data from 7+ real UK data sources to generate what I'm calling a **Sovereignty Score** (0-100).

Here's what it actually checks:

- **Water access** — aquifer depth, borehole proximity, and watercourse data from the British Geological Survey
- **Energy potential** — solar irradiance and wind speed data from NASA POWER, factored for your specific coordinates and UK climate patterns
- **Planning restrictions** — scans nearby planning applications and flags conservation areas, AONBs, Green Belt, and council planning attitudes to off-grid development
- **Flood risk** — pulls live Environment Agency flood zone data (not just the postcode-level stuff)
- **Soil quality** — BGS soil and geology data relevant to growing, drainage, and foundation viability
- **Connectivity** — road access, nearest services, and terrain analysis via OpenStreetMap

The score isn't meant to replace proper due diligence — you should still get surveys done before buying anything. But it's meant to help you quickly filter out the duds and focus your time on plots that actually have off-grid potential.

It's free to use — you get 3 scans a day without paying anything. If you're seriously land-hunting and need more, there are paid tiers (Scout at £9.99/mo for 25 scans, Pioneer at £19.99/mo for 100 scans).

I'm also doing a **founding member lifetime deal — £99 for unlimited access, forever**. That's only for the first 100 people, and then it's gone.

I'd genuinely love feedback from this community. You lot are the people I built this for, and if there's data sources I'm missing or scoring weights that feel off, I want to know.

**Website:** www.offgridscout.co.uk

Happy to answer any questions about how the scoring works, what data sources are used, or anything else.

---

## 2. Reddit Post — Indie Dev / Side Project

**Subreddits:** r/SideProject, r/indiehackers

**Title:** I built a Chrome extension that scores UK land plots for off-grid living potential — here's the tech stack and what I learned

---

Hey folks — wanted to share a side project I've been working on that's now live.

### The problem

I've been looking at buying land in the UK for off-grid living. The research process is brutal — for every listing, you need to check flood risk, water table depth, solar potential, planning restrictions, soil quality, and access. Each of those requires a different government website or dataset. It takes 1-2 hours per listing, and most plots turn out to be unsuitable.

### What I built

**Off-Grid Scout** — a Chrome extension that works on the 6 major UK property listing sites (Rightmove, Zoopla, OnTheMarket, Savills, PrimeLocation, PlotFinder). You click the extension on any land listing, and it generates a "Sovereignty Score" (0-100) by pulling and analysing data from 7+ external APIs.

### Tech stack

- **Backend:** FastAPI (Python) deployed on Render with Docker
- **Database:** SQLite with WAL mode (moved from JSON file storage — don't start with JSON files, learn from my mistakes)
- **Chrome Extension:** Manifest V3, vanilla JS, no framework. Content scripts extract listing data using site-specific DOM selectors
- **External APIs:** UK Environment Agency (flood risk), OpenStreetMap Overpass + Nominatim (terrain, access, geocoding), NASA POWER (solar/wind), BGS (geology, aquifers, soil), PlanIt API (planning applications), OpenTopoData (elevation)
- **Payments:** Stripe with checkout sessions, webhooks, and customer portal
- **Auth:** Custom API key system (ogs_ prefix, SHA-256 hashed storage, tier-based rate limiting)
- **Landing page:** Static HTML + Tailwind CSS served from FastAPI, dark theme
- **Tests:** 25 pytest tests covering the evaluation engine

### Architecture decisions

The interesting bit is the two-phase evaluation:

1. **Discovery phase** — the AutonomousScout analyses listing keywords, checks flood risk zones, estimates grid proximity, and scans for ghost planning applications nearby
2. **Evaluation phase** — four specialist modules run in parallel:
   - OSLandRover (terrain/access via Overpass API)
   - EnergyHunter (solar/wind via NASA POWER)
   - ResourceHunter (aquifer/soil via BGS)
   - PolicyHunter (UK planning document scoring)

Results get weighted and combined into the final Sovereignty Score.

### Lessons learned

1. **Don't use JSON files as a database.** I started with JSON for users and waitlist. Migrated to SQLite with WAL mode after about a week. The migration was painless but I should have started there.

2. **Content scripts for 6 different websites are a nightmare.** Every property site structures their DOM differently. Rightmove puts coordinates in a script tag. Zoopla uses data attributes. Savills uses a completely different page structure. Budget 3x the time you think you'll need for content script development.

3. **Free tier is essential for trust.** Nobody wants to pay for a Chrome extension before trying it. 3 free scans/day has been the right number — enough to try it properly, not enough if you're seriously land-hunting.

4. **External API reliability varies wildly.** The BGS API occasionally times out. NASA POWER has rate limits. I built an in-memory TTL cache that's saved me from a lot of pain.

5. **UK-specific data is surprisingly accessible.** The Environment Agency, BGS, and planning APIs are all free and reasonably well-documented. If you're building anything UK geo-data related, there's more available than you'd think.

6. **Manifest V3 is fine, actually.** There was a lot of doom and gloom about MV3 but for this use case it works well. Service workers instead of background pages took some adjustment but it's not the disaster people predicted.

### Pricing

- Free: 3 scans/day
- Scout: £9.99/mo (25 scans/day)
- Pioneer: £19.99/mo (100 scans/day)
- Lifetime founding member: £99 (first 100 only)

### Numbers so far

Just launched, so being transparent — early days. Building in public and sharing as it grows.

**Website:** www.offgridscout.co.uk

Happy to go deeper on any part of the tech stack or answer questions about working with UK government APIs.

---

## 3. Facebook Group Post — UK Off-Grid Living

**Groups:** UK Off-Grid Living, Off-Grid UK, Self-Sufficient UK, etc.

---

Hi everyone 👋

Hope this is OK to share — I've built something I think a lot of people in this group will find genuinely useful.

If you've ever spent hours researching a land listing only to discover it's in a flood zone, has terrible solar exposure, or sits in a conservation area with zero chance of planning permission — you'll know the pain.

I've built a free Chrome extension called **Off-Grid Scout** that does all that research for you automatically.

It works on Rightmove, Zoopla, OnTheMarket, Savills, PrimeLocation, and PlotFinder. When you're on a land listing, you click the extension and it checks:

🌊 Flood risk (Environment Agency data)
☀️ Solar & wind potential (NASA climate data)
💧 Water access (BGS aquifer & borehole data)
🌱 Soil quality (geological survey data)
📋 Planning restrictions (nearby applications & designations)
🛤️ Access & connectivity (OpenStreetMap terrain data)

It gives you a **Sovereignty Score out of 100** — basically a quick read on how viable that plot is for off-grid living.

It's **free to use** — you get 3 scans a day without paying anything. If you're actively land-hunting and need more, there are affordable monthly plans starting at £9.99.

I'm also offering a **lifetime deal for £99** to the first 100 members — that gets you full access forever, no monthly fees.

I built this because I'm going through the land search process myself and got fed up doing the same manual checks over and over. It's not a replacement for proper surveys, but it saves you hours of initial research and helps you spot the red flags before you get emotionally attached to a listing! 😄

🔗 **www.offgridscout.co.uk**

Would love to hear what you think. If there's anything you wish it checked that it doesn't, let me know — I'm actively developing it and this community's input matters.

---

## 4. Product Hunt — Tagline & Description

### Tagline

**Your AI land scout for off-grid living in the UK — instantly score any plot's sovereignty potential.**

### Description (300 words)

Searching for off-grid land in the UK is a time sink. Every promising listing on Rightmove or Zoopla sends you down a rabbit hole of flood maps, planning portals, geological surveys, and solar calculators. Two hours later, you discover the plot sits in Flood Zone 3 with a conservation area designation. Back to scrolling.

Off-Grid Scout fixes this.

It's a Chrome extension that works directly on the UK property sites you already use — Rightmove, Zoopla, OnTheMarket, Savills, PrimeLocation, and PlotFinder. Click the extension on any land listing and get an instant **Sovereignty Score** (0-100) that tells you how viable that plot is for off-grid living.

Behind the score, we're pulling real data from 7+ authoritative UK sources:

- **Environment Agency** flood risk zones
- **British Geological Survey** aquifer depth and soil data
- **NASA POWER** solar irradiance and wind speed
- **OpenStreetMap** terrain, access routes, and proximity analysis
- **PlanIt API** nearby planning applications and restrictions
- **OpenTopoData** elevation and topography

No guesswork. No generic postcode-level data. Actual coordinate-specific analysis for the exact plot you're looking at.

The score breaks down into six clear categories — water access, energy potential, planning restrictions, flood risk, soil quality, and connectivity — so you can see exactly where a plot shines and where it falls short.

Built by a developer going through the UK land search process firsthand. Every feature exists because of a real frustration encountered during months of manual research.

Off-Grid Scout won't replace a proper survey, but it will save you hours per listing and help you focus your time and money on plots that actually have potential.

**Free tier** gives you 3 scans/day. Paid plans start at £9.99/month. And for early adopters — a one-time **£99 lifetime deal** for the first 100 members.

Stop researching. Start scouting.

---

## 5. Twitter/X Launch Thread

### Tweet 1 — Hook

I spent months manually checking flood maps, soil data, and planning records for every land listing in the UK.

Then I automated the entire process.

Introducing Off-Grid Scout 🏕️

A Chrome extension that scores any UK land plot for off-grid living potential.

Here's how it works 🧵

---

### Tweet 2 — The Problem

The problem with buying off-grid land in the UK:

Every listing requires checking:
→ Flood risk (Environment Agency)
→ Water table depth (BGS)
→ Solar/wind potential (NASA data)
→ Planning restrictions (local authority)
→ Soil quality (geological surveys)
→ Access routes (OS maps)

That's 1-2 hours per listing. Most plots are unsuitable.

---

### Tweet 3 — The Solution

Off-Grid Scout does all of this in seconds.

Browse Rightmove, Zoopla, or any of the 6 supported UK property sites → click the extension → get a Sovereignty Score (0-100).

7+ real UK data sources. Coordinate-specific analysis. Six category breakdown.

No guesswork. Just data.

---

### Tweet 4 — The Stack / Credibility

Built with:
• FastAPI + Python backend
• 7+ UK government & scientific APIs
• Manifest V3 Chrome extension
• Stripe payments
• SQLite with WAL mode

Every data point comes from official UK sources — Environment Agency, BGS, NASA POWER, OpenStreetMap.

This isn't AI hallucination. It's real data, intelligently scored.

---

### Tweet 5 — CTA

Off-Grid Scout is live now 🟢

✅ Free — 3 scans/day, no card needed
✅ Scout — £9.99/mo for 25 scans/day
✅ Pioneer — £19.99/mo for 100 scans/day
✅ Lifetime — £99 one-time (first 100 members only)

If you're searching for land in the UK and dreaming of going off-grid, this will save you hundreds of hours.

🔗 www.offgridscout.co.uk

---

### Suggested Hashtags (use 2-3 per tweet, rotate)

#OffGrid #OffGridUK #OffGridLiving #Homestead #SelfSufficient #LandForSale #UKProperty #IndieHacker #SideProject #ChromeExtension #BuildInPublic #SovereigntyScore #OffGridScout

---

## 6. Waitlist Email — Launch Announcement

**Subject line options (pick one):**
- Off-Grid Scout is live — your founding member access is inside
- It's here. Score any UK land plot for off-grid potential in seconds.
- You signed up for this — Off-Grid Scout just launched

**Preview text:** Your Sovereignty Score awaits. Founding member lifetime deal for the first 100 only.

---

**Email body:**

Hey {{first_name|there}},

You signed up for Off-Grid Scout because you're serious about finding the right piece of land.

Today, it's live.

**Off-Grid Scout is a Chrome extension that instantly evaluates any UK land listing for off-grid living potential.** Browse Rightmove, Zoopla, or any of the 6 major property sites — click the extension — and get a Sovereignty Score (0-100) backed by real UK data.

No more manually cross-referencing flood maps, soil surveys, planning portals, and solar calculators. Off-Grid Scout checks all of it in seconds:

- Flood risk (Environment Agency)
- Water access (BGS aquifer & borehole data)
- Solar & wind potential (NASA POWER)
- Soil quality (geological survey data)
- Planning restrictions (nearby applications & designations)
- Access & connectivity (OpenStreetMap terrain data)

You're on this list because you got here early. That means something.

---

**Your Founding Member Deal**

As a waitlist member, you have first access to the **Lifetime Founding Member** tier:

**£99 — one time — full access forever.**

No monthly fees. No annual renewals. Every feature. Every update. For life.

This is only available to the **first 100 members**, and once they're claimed, this tier is gone permanently. It won't come back at this price.

For context, the monthly Pioneer plan is £19.99/mo — so the lifetime deal pays for itself in 5 months.

➡️ **Claim your lifetime access:** [Get Lifetime Access](https://www.offgridscout.co.uk)

---

**Not ready to commit? Completely fine.**

The **free tier gives you 3 scans per day** — no card required. Install the extension, try it on a few listings, and see if the Sovereignty Score matches your gut instinct. I think it will.

---

**What's next?**

I'm building this in public and your feedback directly shapes what comes next. Here's what's on the roadmap:

- Saved plots & comparison dashboard
- Email alerts when new high-scoring land is listed
- Downloadable PDF dossiers for shortlisted plots
- Mobile-friendly web app version

Hit reply and tell me what would make Off-Grid Scout more useful for your search. I read every email.

Happy scouting,

[Your name]
Builder, Off-Grid Scout

P.S. — That £99 lifetime deal is genuinely limited to 100 spots. I'm not going to send you a "we extended it!" email in two weeks. When they're gone, they're gone.

---

**Footer:**

You're receiving this because you joined the Off-Grid Scout waitlist at www.offgridscout.co.uk

[Unsubscribe]({{unsubscribe_url}}) | [Privacy Policy](https://www.offgridscout.co.uk/static/privacy.html)

Off-Grid Scout | United Kingdom

---

## Appendix: Platform-Specific Notes

### Reddit Posting Tips
- Post during UK evening hours (6-9 PM GMT) for maximum UK audience visibility
- Engage authentically in comments for at least 2 hours after posting
- Don't cross-post the same content — tailor the tone for each subreddit
- If moderators remove the post, message them first and ask if a revised version would be acceptable
- Build karma in the subreddits before posting by commenting helpfully on other threads for a week

### Facebook Group Tips
- Check group rules about self-promotion before posting
- Some groups have dedicated "share your project" days — use those
- Respond to every comment, especially critical ones
- Consider offering a group-specific discount code for tracking

### Product Hunt Tips
- Launch on a Tuesday or Wednesday for best visibility
- Have 5-10 supporters ready to upvote and leave genuine comments in the first hour
- Prepare a "maker comment" expanding on the story with personal motivation
- Respond to every comment on launch day
- Have screenshots/GIF demo ready showing the extension in action

### Twitter/X Tips
- Space tweets 15-20 minutes apart, not all at once
- Pin Tweet 1 (the hook) to your profile
- Quote-tweet your own thread throughout the day with additional context
- Engage with everyone who replies or retweets
- Consider a short screen recording demo as a video tweet to complement the thread

### Email Tips
- Send during Tuesday-Thursday morning (9-11 AM GMT) for best open rates
- A/B test subject lines if your email tool supports it
- Set up a follow-up email 3 days later for non-openers with a different subject line
- Track the lifetime deal redemption link separately from the general site link
