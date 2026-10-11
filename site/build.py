#!/usr/bin/env python3
"""Builds the SpendSentry marketing site (static HTML) into this folder. Stdlib only.
Run: python3 site/build.py   (output is committed; GitHub Pages serves site/)."""
import html
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
BASE = "https://nirbanravi.github.io/ppc-agent/"
REPO = "https://github.com/nirbanravi/ppc-agent"
NAME = "SpendSentry"
DEF = ("SpendSentry is an open-source AI PPC agent for Claude Code that audits ad accounts, checks budget pacing, "
       "plans budgets and writes client reports across 12 ad platforms, and cannot change an account unless you approve the exact change.")
PLATFORMS = ["Google Ads", "YouTube", "Meta Ads", "LinkedIn Ads", "TikTok Ads", "Microsoft Advertising", "Amazon Ads",
             "Reddit Ads", "Pinterest Ads", "Snapchat Ads", "Apple Ads", "X Ads"]
UPDATED = "2026-10-11"
INSTALL = """claude plugin marketplace add nirbanravi/ppc-agent
claude plugin install spendsentry@spendsentry"""

CSS = """
:root{--bg:#fbfaf7;--fg:#17191d;--muted:#5f6670;--line:#e3e0d8;--card:#fff;--accent:#2f5fd0;--accent-soft:#e8eefc;--ok:#067647;--bad:#b42318;--code:#f3f1ec}
@media (prefers-color-scheme:dark){:root{--bg:#11161f;--fg:#eef1f5;--muted:#a3adbb;--line:#273142;--card:#161d29;--accent:#7fb2ff;--accent-soft:#1b2740;--ok:#47cd89;--bad:#f97066;--code:#1b2331}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}header.top{border-bottom:1px solid var(--line)}nav{max-width:1040px;margin:0 auto;padding:14px 16px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
nav .brand{font-weight:750;color:var(--fg);text-decoration:none;margin-right:auto;font-size:18px}nav a{text-decoration:none;font-size:15px}
main{max-width:860px;margin:0 auto;padding:40px 16px 72px}h1{font-size:clamp(32px,5vw,48px);line-height:1.1;letter-spacing:-.02em;margin:0 0 16px}
h2{font-size:26px;margin:48px 0 12px;letter-spacing:-.01em}h3{font-size:19px;margin:28px 0 6px}.lede{font-size:20px;color:var(--muted);margin:0 0 24px}
pre{background:var(--code);border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow-x:auto;font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
code{font:0.88em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--code);padding:1px 5px;border-radius:5px}pre code{background:none;padding:0}
.btn{display:inline-block;background:var(--accent);color:#fff;padding:11px 18px;border-radius:10px;text-decoration:none;font-weight:600;margin:4px 8px 4px 0}
.btn.ghost{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:16px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card h3{margin-top:0}.chips{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.chip{border:1px solid var(--line);border-radius:999px;padding:3px 12px;font-size:14px;background:var(--card)}
table{width:100%;border-collapse:collapse;font-size:15px;display:block;overflow-x:auto}th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted)}
.ok{color:var(--ok);font-weight:650}.bad{color:var(--bad);font-weight:650}.note{background:var(--accent-soft);border-radius:10px;padding:12px 16px;font-size:15px}
img{max-width:100%;height:auto;border:1px solid var(--line);border-radius:12px}details{border-bottom:1px solid var(--line);padding:12px 0}summary{font-weight:650;cursor:pointer}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:14px}footer div{max-width:1040px;margin:0 auto;padding:22px 16px}.muted{color:var(--muted)}
"""

PAGES = [
    ("index.html", "Home"),
    ("google-ads-audit.html", "Google Ads audit"),
    ("meta-ads-audit.html", "Meta Ads audit"),
    ("ai-agent-ad-account-safety.html", "AI agent safety"),
    ("compare.html", "Compare"),
]


def e(s):
    return html.escape(s, quote=True)


def page(fname, title, description, body, jsonld):
    nav = "".join(f'<a href="{f}">{e(t)}</a>' for f, t in PAGES[1:])
    ld = "".join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in jsonld)
    url = BASE + ("" if fname == "index.html" else fname)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<meta name="description" content="{e(description)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}assets/og.png"><meta name="twitter:card" content="summary_large_image">
<meta name="author" content="Ravi Nirban"><style>{CSS}</style>{ld}</head><body>
<header class="top"><nav><a class="brand" href="./">🛡 {NAME}</a>{nav}<a href="{REPO}">GitHub</a></nav></header>
<main>{body}</main>
<footer><div>{NAME} is open source (MIT), created by <a href="https://github.com/nirbanravi">Ravi Nirban</a>. Not affiliated with Google, Meta, Anthropic or any ad platform. Page updated {UPDATED}.</div></footer>
</body></html>
"""


def faq_ld(qas):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qas]}


def faq_html(qas):
    return "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in qas)


def crumbs(name, fname):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": NAME, "item": BASE},
        {"@type": "ListItem", "position": 2, "name": name, "item": BASE + fname}]}


SOFTWARE_LD = {
    "@context": "https://schema.org", "@type": "SoftwareApplication", "name": NAME,
    "alternateName": "SpendSentry PPC agent", "description": DEF, "applicationCategory": "BusinessApplication",
    "applicationSubCategory": "PPC audit and paid media management", "operatingSystem": "macOS, Linux, Windows (Claude Code)",
    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "license": "https://opensource.org/licenses/MIT",
    "codeRepository": REPO, "url": BASE, "image": BASE + "assets/og.png", "softwareVersion": "1.0.0",
    "author": {"@type": "Person", "name": "Ravi Nirban", "url": "https://github.com/nirbanravi"},
    "keywords": "AI PPC agent, Google Ads audit, Meta Ads audit, PPC audit, paid media, Claude Code plugin, ad account audit",
}

INSTALL_HTML = f"""<pre><code>{e(INSTALL)}</code></pre>
<p class="muted">Run these in a terminal with <a href="https://code.claude.com/docs/en/overview">Claude Code</a> installed. Then open a project folder, start <code>claude</code>, and type <code>/ads audit google ./exports</code>. Python 3.9+ is the only other requirement.</p>"""

# ---------------------------------------------------------------- pages
home_faq = [
    ("What is SpendSentry?", DEF),
    ("Which ad platforms does it support?", "Google Ads, YouTube, Meta Ads (Facebook and Instagram), LinkedIn Ads, TikTok Ads, Microsoft Advertising, Amazon Ads, Reddit Ads, Pinterest Ads, Snapchat Ads, Apple Ads and X Ads, from CSV/XLSX exports or read-only API/MCP access."),
    ("Can SpendSentry change my ad account?", "Only after you approve. It proposes exact changes with before and after values, a gate checks them against limits such as a 30% budget-change cap, and you approve by typing a one-time code. A hook blocks every other write, including replays and edited requests."),
    ("Is SpendSentry free?", "Yes. It is open source under the MIT license and runs locally in Claude Code. The engine does not send your exports anywhere."),
    ("What does an audit include?", "Scored findings with evidence: conversion tracking breaks, campaigns spending without conversions, CPA and ROAS against target, budget- and rank-limited campaigns, wasted search terms, frequency and creative fatigue signals, spend concentration and pacing. Each finding cites the source file and rows and carries a confidence score."),
    ("Do I need to be a developer?", "No coding is needed, but you do need Claude Code, which runs in a terminal or code editor. If you can export a report from Google Ads and paste two commands, you can run an audit."),
]

home = f"""
<h1>The open-source AI PPC agent that can't quietly change your ad accounts</h1>
<p class="lede">{e(DEF)}</p>
<a class="btn" href="{REPO}">Get it on GitHub</a><a class="btn ghost" href="google-ads-audit.html">See a Google Ads audit</a>
<div class="chips">{''.join(f'<span class="chip">{e(p)}</span>' for p in PLATFORMS)}</div>
<img src="assets/sample-report.png" alt="SpendSentry audit report showing a critical conversion tracking break, CPA above target and evidence rows" width="1100" loading="lazy">
<p class="muted">Example report generated from the synthetic sample exports in the repository, not a real client.</p>

<h2>What it does</h2>
<div class="grid">
<div class="card"><h3>/ads audit</h3>Scored findings with the rows behind them, impact ranges and a confidence score for each.</div>
<div class="card"><h3>/ads monitor</h3>Budget pacing against monthly targets, tracking breaks and anomalies.</div>
<div class="card"><h3>/ads plan</h3>Budget allocation and campaign structure, with the reasoning written down.</div>
<div class="card"><h3>/ads experiment</h3>A test backlog with minimum detectable effect, duration and decision rules.</div>
<div class="card"><h3>/ads report</h3>Client-ready Markdown and HTML reports built from finalized runs.</div>
<div class="card"><h3>/ads optimize · create</h3>Exact changes packaged for review. Nothing runs until you approve it.</div>
</div>

<h2>Why paid media teams trust it</h2>
<table><tr><th></th><th>Typical AI ads tool</th><th>{NAME}</th></tr>
<tr><td>Account changes</td><td>The model decides</td><td class="ok">Blocked unless you approved that exact call</td></tr>
<tr><td>Numbers in reports</td><td>Generated text</td><td class="ok">Computed from your exports, with file and row cited</td></tr>
<tr><td>Missing or stale data</td><td>Rarely mentioned</td><td class="ok">Listed in every report; run marked partial</td></tr>
<tr><td>Confidence</td><td>Implied</td><td class="ok">Scored 0–1 with reasons</td></tr>
<tr><td>History</td><td>Chat scrollback</td><td class="ok">Versioned, hashed JSON for every run</td></tr></table>
<p><a href="ai-agent-ad-account-safety.html">How the approval gate works →</a></p>

<h2>Install</h2>{INSTALL_HTML}

<h2>FAQ</h2>{faq_html(home_faq)}
"""

g_faq = [
    ("How do I audit a Google Ads account with AI?", "Export a campaign report segmented by day and a search terms report from Google Ads, then run /ads audit google ./exports in Claude Code with SpendSentry installed. You get scored findings with the rows that support each one."),
    ("Which Google Ads reports does the audit need?", "A campaign report by day with Cost, Impressions, Clicks, Conversions, Conversion value, Budget and Campaign status, plus a search terms report. Adding Search impression share and Search lost IS (budget/rank) unlocks the budget- and rank-limit checks."),
    ("Does the AI audit replace a PPC specialist?", "No. The automated checks catch measurable problems fast, and Claude adds judgement on top, but every finding comes with evidence so a specialist can confirm or reject it quickly."),
    ("Is it safe to connect my Google Ads account?", "Use exports or read-only access. Google's official Google Ads MCP server is read-only, and SpendSentry blocks write tools unless you approve each exact change."),
]
google = f"""
<h1>AI Google Ads audit with Claude Code</h1>
<p class="lede">Run an evidence-backed Google Ads audit in minutes: tracking breaks, wasted spend, search-term waste, budget limits and CPA/ROAS against target, with the exact rows behind every finding.</p>

<h2>1. Export two reports</h2>
<table><tr><th>Report</th><th>Columns</th><th>Segment</th></tr>
<tr><td>Campaigns</td><td>Campaign, Campaign status, Budget, Cost, Impr., Clicks, Conversions, Conv. value, Search impr. share, Search lost IS (budget), Search lost IS (rank)</td><td>Day, last 30–90 days</td></tr>
<tr><td>Search terms</td><td>Search term, Match type, Campaign, Ad group, Cost, Clicks, Impr., Conversions</td><td>None</td></tr></table>
<p class="muted">The default Google Ads download (UTF-16, with report title rows and a Total row) works as-is.</p>

<h2>2. Run the audit</h2>
<pre><code>/ads audit google ./exports</code></pre>
<p>On first run you set CPA/ROAS targets and monthly budgets. The audit is read-only.</p>

<h2>3. What it checks automatically</h2>
<table><tr><th>Check</th><th>What it catches</th></tr>
<tr><td>Tracking break</td><td>Conversions drop to zero for consecutive days while spend continues</td></tr>
<tr><td>Zero-conversion spend</td><td>Campaigns spending above a waste threshold with no conversions; awareness campaigns are flagged separately</td></tr>
<tr><td>CPA / ROAS vs target</td><td>Blended and campaign-level performance against your targets</td></tr>
<tr><td>Budget-limited</td><td>Campaigns losing 20%+ impression share to budget while converting at or below account CPA</td></tr>
<tr><td>Rank-limited</td><td>Campaigns losing 40%+ impression share to ad rank</td></tr>
<tr><td>Search-term waste</td><td>Terms that spent at least one CPA with no conversions, ranked by spend</td></tr>
<tr><td>CTR outliers, concentration, pacing</td><td>Campaigns far below sibling CTR, one campaign dominating spend, month-to-date pacing</td></tr></table>
<p>Claude then works through a Google-specific checklist: primary vs secondary conversion actions, duplicate conversions, bidding vs data volume, brand cannibalisation in Performance Max, location and network settings. Every judgement finding still has to cite data.</p>

<h2>4. Read the report</h2>
<p>Each finding shows its severity, the evidence rows, an impact range with the method used, and a confidence score with reasons. Missing columns and stale exports are listed at the top, not hidden.</p>
<img src="assets/sample-report.png" alt="Google Ads audit report with a critical tracking break finding" loading="lazy" width="1100">

<h2>Install</h2>{INSTALL_HTML}
<h2>FAQ</h2>{faq_html(g_faq)}
"""

m_faq = [
    ("How do I audit Meta Ads with AI?", "Export a campaign and ad set report from Ads Manager with spend, impressions, reach, frequency, link clicks, a named conversion event and its value (ideally broken down by day), then run /ads audit meta ./exports in Claude Code with SpendSentry."),
    ("Why should I avoid the 'Results' column?", "In Meta Ads Manager, 'Results' counts whatever event each ad set optimises for, so it can mix purchases, leads and other events. SpendSentry warns when it sees it. Export a named event such as Purchases or Leads instead."),
    ("Can SpendSentry change my Meta campaigns?", "Not without your approval. Meta's official Ads MCP server can create and edit campaigns, so SpendSentry treats every write tool as gated: it runs only when it matches a change you approved with a one-time code."),
]
meta = f"""
<h1>AI Meta Ads audit (Facebook &amp; Instagram) with Claude Code</h1>
<p class="lede">Audit Meta Ads from an export: CPA and ROAS against target, frequency and creative fatigue, zero-conversion ad sets and tracking gaps, each with the evidence behind it.</p>

<h2>What to export from Ads Manager</h2>
<ul>
<li>Campaign and ad set level: Amount spent, Impressions, Reach, Frequency, Link clicks, a <strong>named</strong> conversion event (Purchases, Leads) and its conversion value.</li>
<li>Break it down by <strong>Day</strong>. Without daily rows, the tracking-break and trend checks cannot run, and the report will say so.</li>
<li>Optional: an ad-level export for creative fatigue.</li></ul>

<h2>What the audit checks</h2>
<table><tr><th>Area</th><th>Checks</th></tr>
<tr><td>Performance</td><td>Blended and campaign CPA/ROAS against target; campaigns at 2× the account CPA with a meaningful spend share</td></tr>
<tr><td>Saturation</td><td>Average frequency at 5+, alongside CPA trend</td></tr>
<tr><td>Waste</td><td>Spend with no conversions; awareness and video-view campaigns are judged on their own goal</td></tr>
<tr><td>Measurement</td><td>Conversions without value, 'Results' column warnings, Pixel/CAPI deduplication and attribution-setting questions for the analyst pass</td></tr></table>

<div class="note">Meta's Marketing API changes often: v26.0 shipped in July 2026, and several deprecations reach all versions on 27 October 2026. SpendSentry keeps a dated registry of platform rules and re-checks official docs when an entry is stale.</div>

<h2>Run it</h2>
<pre><code>/ads audit meta ./exports</code></pre>
<h2>Install</h2>{INSTALL_HTML}
<h2>FAQ</h2>{faq_html(m_faq)}
"""

s_faq = [
    ("Can AI agents change my Google or Meta ad account?", "Yes, if they are connected to a write-capable tool. Meta's hosted Ads MCP server and the Amazon Ads MCP Server both support creating, updating and deleting. Google's official Google Ads MCP server is read-only."),
    ("How does SpendSentry stop unapproved changes?", "A Claude Code PreToolUse hook checks every ad-platform tool call. Write-capable calls are blocked unless the exact tool and input match an action in a changeset that passed safety checks and that you approved by typing a one-time code."),
    ("Can the AI approve its own changes?", "No. Approvals are recorded only from your own message, by a separate hook. Attempts to write an approval file, type the approval phrase in a command, or send raw HTTP writes to ad APIs are blocked."),
    ("What are the limits of this protection?", "Shell-level detection is pattern-based, so keep ad API credentials out of your shell environment. Skill hooks start when the skill is loaded; installing it as a plugin keeps them active whenever the plugin is enabled."),
]
safety = f"""
<h1>How to stop AI agents from changing your ad account</h1>
<p class="lede">AI agents can now act on ad accounts through MCP servers, and several official servers can create, edit and delete. Here's how SpendSentry makes every change go through you.</p>

<h2>The risk</h2>
<p>A model that is confidently wrong about a budget, a bid strategy or a pause can cost a month's spend in an afternoon. Asking the model to be careful isn't enough; the protection needs to be enforced in code, outside the model.</p>

<h2>The approval gate</h2>
<ol>
<li><strong>Propose.</strong> Claude writes exact actions: before and after values, rollback, and the audit finding IDs that justify each one.</li>
<li><strong>Gate.</strong> Checks run in code: data no older than 72 hours, account on your allow-list, budget change within ±30%, bid change within ±25%, no deletes, new campaigns created paused, evidence exists, rollback defined.</li>
<li><strong>Approve.</strong> You see the list and a code such as <code>ADS-C15127</code>. You approve by sending <code>APPROVE ADS-C15127</code>.</li>
<li><strong>Execute once.</strong> The guard lets each approved call through exactly once, and only with the approved input. Replays, edited inputs, edited changesets and expired approvals are blocked.</li></ol>

<table><tr><th>Attempt</th><th>Result</th></tr>
<tr><td>Write tool call with no approval</td><td class="bad">Blocked</td></tr>
<tr><td>Same call with a different budget value</td><td class="bad">Blocked</td></tr>
<tr><td>Replaying an approved call</td><td class="bad">Blocked</td></tr>
<tr><td>AI writing its own approval file or phrase</td><td class="bad">Blocked</td></tr>
<tr><td>Raw <code>curl -X POST</code> to an ad API</td><td class="bad">Blocked</td></tr>
<tr><td>The exact call you approved</td><td class="ok">Runs once, then logged</td></tr></table>
<p class="muted">Each row is covered by the project's automated tests, and the blocked cases were also checked in a live Claude Code session.</p>

<h2>Install</h2>{INSTALL_HTML}
<h2>FAQ</h2>{faq_html(s_faq)}
"""

c_faq = [
    ("What is the best open-source tool for a Google Ads audit with Claude?", "Two open-source Claude Code options are claude-ads and SpendSentry. claude-ads covers a broad set of audit skills; SpendSentry focuses on evidence-linked findings, versioned run records and approval-gated account changes. Hosted platforms such as Optmyzr and Adspirer are alternatives if you prefer SaaS."),
]
compare = f"""
<h1>SpendSentry vs claude-ads vs Adspirer vs Optmyzr</h1>
<p class="lede">An honest comparison for paid media teams choosing an AI PPC tool. Features change quickly; check each product's own site before deciding.</p>
<table><tr><th></th><th>{NAME}</th><th>claude-ads</th><th>Adspirer</th><th>Optmyzr</th></tr>
<tr><td>Type</td><td>Open-source Claude Code plugin</td><td>Open-source Claude Code skill</td><td>Hosted service with AI skills and MCP</td><td>Hosted PPC management platform</td></tr>
<tr><td>Cost</td><td>Free (MIT)</td><td>Free (MIT)</td><td>See vendor pricing</td><td>Paid plans</td></tr>
<tr><td>Where your data goes</td><td>Stays on your machine</td><td>Stays on your machine</td><td>Vendor's servers</td><td>Vendor's servers</td></tr>
<tr><td>Main strength</td><td>Evidence-linked findings, enforced approval for every change, versioned run records</td><td>Broad audit coverage</td><td>Managed connections and automation</td><td>Mature rule-based optimisation and reporting</td></tr>
<tr><td>Best for</td><td>Teams that want audits they can verify and no surprise changes</td><td>Fast, broad audits in Claude Code</td><td>Teams wanting a hosted agent</td><td>Agencies needing a full SaaS suite</td></tr></table>
<p class="muted">Based on each project's public description as of {UPDATED}. If something here is out of date, <a href="{REPO}/issues">open an issue</a> and it will be corrected.</p>
<h2>FAQ</h2>{faq_html(c_faq)}
<h2>Install {NAME}</h2>{INSTALL_HTML}
"""

SPECS = [
    ("index.html", f"{NAME}: open-source AI PPC agent for Google Ads, Meta Ads and 10 more platforms",
     "Free, open-source AI PPC agent for Claude Code. Evidence-backed Google Ads and Meta Ads audits, pacing and client reports across 12 ad platforms, with approval-gated account changes.",
     home, [SOFTWARE_LD, faq_ld(home_faq)]),
    ("google-ads-audit.html", "AI Google Ads audit with Claude Code: free, evidence-backed | SpendSentry",
     "How to audit a Google Ads account with AI in minutes: which reports to export, what gets checked (tracking breaks, wasted search terms, budget limits) and how to read the findings.",
     google, [faq_ld(g_faq), crumbs("Google Ads audit", "google-ads-audit.html")]),
    ("meta-ads-audit.html", "AI Meta Ads audit (Facebook & Instagram) with Claude Code | SpendSentry",
     "Audit Meta Ads with AI: what to export from Ads Manager, the checks for CPA, ROAS, frequency and tracking, and why to avoid the Results column.",
     meta, [faq_ld(m_faq), crumbs("Meta Ads audit", "meta-ads-audit.html")]),
    ("ai-agent-ad-account-safety.html", "How to stop AI agents from changing your ad account | SpendSentry",
     "AI agents can edit Google, Meta and Amazon ad accounts through MCP. See how an enforced approval gate blocks every change you didn't approve.",
     safety, [faq_ld(s_faq), crumbs("AI agent safety", "ai-agent-ad-account-safety.html")]),
    ("compare.html", "SpendSentry vs claude-ads vs Adspirer vs Optmyzr: AI PPC tools compared",
     "An honest comparison of AI PPC tools for paid media teams: open-source Claude Code plugins vs hosted platforms, and where your data goes.",
     compare, [faq_ld(c_faq), crumbs("Compare", "compare.html")]),
]


def main():
    for fname, title, desc, body, ld in SPECS:
        (OUT / fname).write_text(page(fname, title, desc, body, ld), encoding="utf-8")
    urls = "".join(f"<url><loc>{BASE}{'' if f == 'index.html' else f}</loc><lastmod>{UPDATED}</lastmod></url>" for f, *_ in SPECS)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {BASE}sitemap.xml\n")
    llms = [f"# {NAME}", "", f"> {DEF}", "", "## Pages"]
    llms += [f"- [{t.split(' | ')[0]}]({BASE}{'' if f == 'index.html' else f}): {d}" for f, t, d, *_ in SPECS]
    llms += ["", "## Install", "```", INSTALL, "```", "", f"Source: {REPO} (MIT). Author: Ravi Nirban."]
    (OUT / "llms.txt").write_text("\n".join(llms) + "\n")
    (OUT / ".nojekyll").write_text("")
    print("built", len(SPECS), "pages")


if __name__ == "__main__":
    main()
