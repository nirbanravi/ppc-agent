# Launch kit

## Naming system for SEO and AI search (use it identically everywhere)
| Layer | Value | Why |
|---|---|---|
| Brand (ownable) | **SpendSentry** | Unique, so AI assistants can tie every mention to one entity |
| Category phrase (always next to the brand) | **open-source AI PPC agent** | Matches how PPC experts search and how AI answers phrase recommendations |
| GitHub URL | `github.com/nirbanravi/ppc-agent` (repo name = keyword) | GitHub search weights the repo name most; both words show in the URL |
| Plugin / directory name | `spendsentry`, with description starting "Open-source AI PPC agent…" | Anthropic's directory and `/plugin` search read name and description |
| Command | `/ads` | Short to type and easy to say in demos |

Use the exact definition sentence from the top of the README on every profile, listing and post. AI search engines build their picture of an entity from repeated, consistent statements across independent sites.

Validate the keywords with real data before locking them in: run Google Keyword Planner on "ppc audit", "google ads audit", "ai ppc tool", "ppc ai agent", "paid media ai", "meta ads audit" and "google ads ai agent" (India + US + UK). If "google ads audit" clearly beats "ppc", swap the repo slug to `google-ads-audit-agent` and keep the brand.

### AI search (AIO/GEO) checklist
- [ ] Definition sentence first in README, plugin description, GitHub About, Product Hunt and LinkedIn.
- [ ] `llms.txt` at the repo root (done) and on the docs site.
- [ ] FAQ in the README (done). Answer the questions people actually ask an AI assistant.
- [ ] GitHub Pages site with SoftwareApplication JSON-LD, one page per platform audit ("Meta Ads audit with Claude Code") and an honest comparison page (vs claude-ads, Adspirer, Optmyzr).
- [ ] Listings that AI crawlers already index for this category: Anthropic plugin directory, claudemarketplaces.com, osrepos, landscape.jimmysong.io, awesome-claude-code lists and Product Hunt.
- [ ] Third-party mentions: guest posts and podcasts in PPC media, plus r/PPC threads. AI answers cite these far more than your own site.
- [ ] Check monthly: ask ChatGPT, Perplexity, Gemini and Google AI Overviews "best open-source AI tool for Google Ads audit" and note whether you're cited.

## Name and search
**SpendSentry.** "Spend" is what advertisers protect, and "Sentry" signals both watching (audits, pacing) and guarding (approval-gated writes). It's one unique token, so a search for the name finds only you.

Checked 2026-10-11 by web search: no ad-tech product or repo found under this name. Before launch, check the GitHub username/org, the spendsentry domains (.com/.dev/.io), X/LinkedIn handles, and a trademark search (IP India class 9/42, USPTO TESS). A web search is not a trademark clearance.

Rejected names: AdProof (existing ad-tech company), AdSentinel (collides with "AdBlocker Sentinel" adware and eyeo's ad-blocking AI), AdWarden (existing Chrome extension), SpendGuard (too close to the "Ad Spend Guardian" Shopify app), and anything with "Claude" or "Google Ads" in the name (trademarks, and Anthropic's directory may reject "Claude" names).

People don't search for your name until they've heard it. They search for what it does, so put those words everywhere GitHub and Google index:
- **GitHub "About":** `AI Google Ads & Meta Ads audit skill for Claude Code: PPC audits, pacing, reports across 12 ad platforms, with approval-gated changes`
- **Topics (max 20):** claude-code, claude-skills, claude-plugin, claude-code-plugin, ai-agents, mcp, ppc, paid-media, google-ads, meta-ads, facebook-ads, linkedin-ads, tiktok-ads, amazon-ads, microsoft-ads, ads-audit, marketing-automation, performance-marketing, digital-marketing, adops
- **Command stays `/ads`:** short and easy to say in a demo.
- **Long-tail pages (docs/ or a GitHub Pages site):** "Google Ads audit with Claude Code", "Meta Ads audit checklist (2026)", "How to stop AI agents changing your ad account". These pages catch searches for months; a launch post fades in days.

## Positioning (one line)
**The paid media skill for Claude Code that can't quietly change your ad accounts.** It produces evidence-backed audits across 12 platforms, and every account change needs your typed approval.

Why this angle: "AI ads audit" is crowded (claude-ads and other open-source skills, vendor MCP servers, Adspirer-style SaaS). What's rarer is enforced safety plus traceable numbers, and that is what agency owners and in-house leads worry about once agents can write to accounts.

Proof points you can show, not just claim:
1. A 60-second screen recording of Claude trying a write, being blocked, you approving, the exact call passing, and a replay being blocked.
2. The audit report with evidence lines and confidence reasons.
3. The eval table: "without the plugin, Claude failed the 'no silent account changes' case; with it, it passed."

## Before announcing
- [ ] Real-account testing done (docs/TESTING.md stage 4) on at least 3 accounts and 3 platforms.
- [x] Owner name and repo path filled in (Ravi Nirban, nirbanravi/ppc-agent).
- [ ] CI green; tag `v1.0.0` and create a GitHub Release with the changelog.
- [ ] Repo topics: `claude-code`, `claude-skills`, `claude-plugin`, `ppc`, `google-ads`, `meta-ads`, `paid-media`, `ai-agents`.
- [ ] Social preview image (Settings → General) made from the report screenshot.
- [ ] Demo GIF/video at the top of the README.

## Distribution, in order
1. **Anthropic plugin directory.** Go to claude.ai/directory/manage → Submit new → Plugin bundle → `nirbanravi/ppc-agent`. The repo must be public before publishing. Answer the data-handling questions accurately: exports are processed locally, and nothing is sent anywhere by the engine. Review time isn't published.
2. **Curated lists.** Open PRs to the main awesome-claude-code / awesome-claude-skills lists, with one line and the safety angle. Follow each list's contributing rules.
3. **Practitioner communities.** These are your users, and they're harder to fool than devs. Post a real teardown (anonymised) to r/PPC and PPC Chat, plus your LinkedIn network. Lead with the finding, not the tool.
4. **Dev communities.** Use Show HN or r/ClaudeAI for the hook-based approval design. That technical story is what devs upvote.
5. **India-first angle** (fits your AdOps OS plan; SpendSentry can be its flagship skill): INR examples, lakh formatting and Indian D2C/healthcare scenarios. Few tools serve this.

## Launch posts (drafts, edit to your voice)

**LinkedIn**
> AI agents can now edit ad accounts directly. Meta's and Amazon's official MCP servers support create/update/delete.
> After 13 years of managing up to ₹X Cr/month in ad spend, my first question was: what stops a confident wrong change?
> So I built SpendSentry, an open-source Claude Code plugin:
> • audits 12 ad platforms from exports or read-only access
> • every number traces to a file and row, with a confidence score
> • it cannot change an account unless I type the approval code for that exact change
> [Add one real, anonymised finding from your beta tests here. Don't use the synthetic sample: readers will ask.]
> Free, MIT: github.com/nirbanravi/ppc-agent. I'd love brutal feedback from PPC folks.

**Show HN**
> Show HN: Approval-gated ad account changes for Claude Code
> SpendSentry is a Claude Code plugin for paid media work. The interesting part is enforcement. A PreToolUse hook blocks any write-capable ad-platform tool call unless the exact (tool, input) hash matches a changeset that passed a gate. A UserPromptSubmit hook records approval only from the human's typed "APPROVE <code>", so the model cannot approve itself. Approvals are single-use, expire, and are void if the changeset is edited. Audits are stdlib Python with hashed, versioned JSON run records. Known limits are in the README.

**r/PPC** (lead with value, disclose that you're the author)
> I built an open-source tool that audits Google/Meta/etc. exports and flags things like tracking breaks, zero-conversion spend and search-term waste, with the rows behind each finding. Here's an anonymised teardown it produced [screenshot]. I'm the author, it's free, and I'm looking for people to break it on their exports.

## What to measure (first 30 days)
- Installs: GitHub stars are a weak proxy. Track clones and issues opened with real export headers.
- Activation: share of issue reporters who completed an audit.
- Quality: false-positive reports per audit, from feedback.
- Leads: inbound audit/consulting requests, if that's your goal.

Expectations: most open-source launches get modest traction. Sustained reach usually comes from repeated useful teardowns and contributions, not one launch post.
