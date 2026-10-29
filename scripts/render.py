#!/usr/bin/env python3
"""Render the animated SVG assets used by the profile README.

Everything is generated from the config below, so edit text here, not in the SVGs.
Static assets are deterministic. The telemetry dashboard and project cards pull live
numbers from the GitHub GraphQL API when a token is available (GITHUB_TOKEN / GH_TOKEN,
or `gh auth token` locally). If the API is unreachable the existing dashboard is kept,
so a failed refresh never publishes empty stats.

Usage:  python scripts/render.py [--offline]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import random
import subprocess
import sys
import textwrap
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

# --------------------------------------------------------------------------- config
LOGIN = "PrashantAHD"
NAME = "PRASHANT KUMAR"
TAGLINE = "// SECURING THE CLOUD, ONE PIPELINE AT A TIME"
ROLES = [
    "Microsoft Certified: Cybersecurity Architect Expert",
    "AWS Certified DevOps Engineer – Professional",
    "Cloud Security Engineer",
    "DevSecOps Engineer",
    "CNAPP · Wiz · CSPM Specialist",
    "Policy-as-Code & Automation Nerd",
]
YEARS = "5+"
ORGS_FALLBACK = 14  # GITHUB_TOKEN only sees public org memberships
MOTTO = "Shift left. Secure everything. Automate the rest."
EMAIL = "Prashant271227@gmail.com"

ARSENAL = [
    ("CLOUD & OPS", "cyan", ["AWS", "Azure", "GCP", "CloudWatch", "Prometheus", "Grafana", "Datadog",
                                       "CloudZero · FinOps"]),
    ("CLOUD SECURITY", "pink", ["Wiz CSPM", "Wiz MCP", "Qualys", "Trivy", "IAM · RBAC", "Entra ID", "GuardDuty",
                                "CloudTrail", "AWS Config", "HIPAA · HITRUST"]),
    ("DEVSECOPS", "green", ["Jenkins", "GitHub Actions", "Azure DevOps", "ArgoCD · GitOps", "Harness", "Terraform",
                            "Ansible", "Docker", "Kubernetes · EKS", "OpenShift", "Helm", "SonarQube", "Artifactory"]),
    ("AUTOMATION & AI", "violet", ["Python", "PowerShell", "Bash", "Groovy", "GitHub Copilot", "Claude", "MCP Agents",
                                   "Glean", "Atlassian Rovo", "ServiceNow"]),
]

# (issuer, level, name, verify url) — mirrors the resume's certification list
CERTS = [
    ("aws", "PROFESSIONAL", "DevOps Engineer – Professional",
     "https://www.credly.com/badges/72e67681-2adc-4eff-8f31-e565b7596838/public_url"),
    ("microsoft", "EXPERT", "Cybersecurity Architect Expert",
     "https://learn.microsoft.com/api/credentials/share/en-us/iPrashantkr/2574F2DCC705B905?sharingId=AB54B2AF1407CBA8"),
    ("aws", "PROFESSIONAL", "Solutions Architect – Professional",
     "https://www.credly.com/badges/410997f9-2d5d-43bb-9660-4bd38fc928b7/public_url"),
    ("microsoft", "EXPERT", "DevOps Engineer Expert",
     "https://learn.microsoft.com/api/credentials/share/en-us/iPrashantkr/2B555C9A9A693129?sharingId=AB54B2AF1407CBA8"),
    ("microsoft", "ASSOCIATE", "Azure Security Engineer Associate",
     "https://learn.microsoft.com/api/credentials/share/en-us/iPrashantkr/FFB769A37AB7B461?sharingId=AB54B2AF1407CBA8"),
    ("microsoft", "ASSOCIATE", "Azure Administrator Associate",
     "https://learn.microsoft.com/api/credentials/share/en-us/iPrashantkr/1B89518218F2550A?sharingId=AB54B2AF1407CBA8"),
    ("wiz", "CERTIFIED", "Managing Cloud Security Posture", "https://lnkd.in/drbpjnuC"),
]

# (value, label, client, color) — outcomes from the resume
IMPACT = [
    ("100%", "Critical/High cloud findings remediated to zero", "CareFirst", "green"),
    ("80%", "less monthly security governance reporting effort", "CareFirst", "cyan"),
    ("43%", "cloud cost reduction via FinOps automation", "Stellantis", "amber"),
    ("67%", "faster VEW image creation pipelines", "Stellantis", "violet"),
    ("700h→30h", "MTTT/MTTR, leading to contract extensions", "Stellantis", "pink"),
    ("700+", "incidents & service requests resolved", "Stellantis", "cyan"),
]
# (score, unit, framework, note, color) — final Oct 2026 governance report (Wiz tenant-wide ratings)
POSTURE_SCOPE = "CAREFIRST · WIZ · OCT 2026"
POSTURE = [
    (100, "", "Wiz Security Score", "tenant-wide · sustained", "green"),
    (93, "%", "HIPAA Security Rule", "▲ up from 92% (Sep)", "cyan"),
    (88, "%", "HITRUST CSF v11.2", "■ maintained", "violet"),
]
CAREER = [
    ("JAN 2024 — PRESENT", "AHEAD", "DevOps & Cloud Security Engineer",
     ["CareFirst BlueCross BlueShield", "CSX", "Stellantis", "Intermex"]),
    ("AUG 2021 — JAN 2024", "STU Biz Solutions", "DevOps Engineer", ["HSBC"]),
]

PROJECTS = [
    dict(repo="WizExpert", public=True, file="project-wizexpert", client="CareFirst", wide=True,
         tagline="Analyze. Report. Validate. Coordinate. Remediate.",
         desc="Independent Wiz MCP assistant for AWS & Azure: evidence-led investigation, monthly governance workbooks and "
              "executive dashboards, and approval-gated, ServiceNow-governed remediation verified with fresh Wiz evidence.",
         tags=["Wiz MCP", "AWS", "Azure", "Governance", "ServiceNow", "-80% reporting effort", "600+ tests"]),
    dict(repo="Azure-Storage-Analysis", public=True, file="project-azure-finops", client="CSX",
         tagline="Azure storage cost intelligence (FinOps).",
         desc="Single-command analysis across subscriptions: savings opportunities, 8-sheet "
              "executive Excel reports and a live web dashboard.",
         tags=["Azure", "FinOps", "Dashboards"]),
    dict(repo="github_access_tool", public=True, file="project-github-access", client="CSX",
         tagline="GitHub org access ops, zero dependencies.",
         desc="Bulk team membership, repo permissions, Actions secret access and Copilot cloud-agent "
              "enablement, significantly cutting manual access-request effort.",
         tags=["GitHub API", "IAM", "Automation"]),
    dict(repo="Agent-Doorbell", public=True, file="project-agent-doorbell", label="OPEN SOURCE",
         tagline="Human-in-the-loop for AI agents, from your phone.",
         desc="VS Code Copilot, Claude and Codex agents ring your phone when they need you: approve commands, "
              "answer questions and send prompts from Telegram.",
         tags=["Copilot", "Telegram", "106 tests"]),
    dict(repo="spend-guard", public=True, file="project-spend-guard", label="OPEN SOURCE",
         tagline="Stop paying top-model prices for routine AI work.",
         desc="A GitHub Copilot skill that keeps routine work on cheap models, hands code and security review "
              "to stronger ones, and caps chats at ~100k tokens with a handoff.",
         tags=["GitHub Copilot", "Model routing", "38 tests"]),
]

SECTIONS = [
    ("01", "WHOAMI", "// identity verified"),
    ("02", "CREDENTIALS", "// 7 certifications · click to verify"),
    ("03", "IMPACT", "// field record"),
    ("04", "THE INFINITE LOOP", "// security at every stage"),
    ("05", "ARSENAL", "// tools of the trade"),
    ("06", "OPERATIONS", "// featured projects"),
    ("07", "TELEMETRY", "// live from the GitHub API"),
    ("08", "ESTABLISH CONNECTION", "// let's build something secure"),
]

# --------------------------------------------------------------------------- theme
C = dict(bg="#05070f", bg2="#0b1226", cyan="#00e5ff", green="#00ff9d", violet="#8b5cf6",
         pink="#ff2e88", amber="#ffb020", aws="#ff9900", ms="#00a4ef", wiz="#5b8cff", text="#e6edf3", muted="#7d8aa5",
         dim="#3a4660", line="#14304a")
MONO = "'JetBrains Mono','Fira Code','Cascadia Code','SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "'Segoe UI','Inter',system-ui,-apple-system,'Helvetica Neue',Arial,sans-serif"
CW = 0.62  # monospace advance width per font-size unit (slightly generous across fallbacks)

BASE_CSS = """
.mono{font-family:%MONO%}.sans{font-family:%SANS%}
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
"""


def esc(s: str) -> str:
    return escape(str(s), {'"': "&quot;"})


def css(s: str) -> str:
    return s.replace("%MONO%", MONO).replace("%SANS%", SANS)


def svg(w: int, h: int, body: str, title: str, style: str = "") -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'fill="none" role="img" aria-label="{esc(title)}">\n<title>{esc(title)}</title>\n'
            f'<style>{css(BASE_CSS + style)}</style>\n{body}\n</svg>\n')


def frame(w: int, h: int, r: int = 16, accent: str = "cyan") -> str:
    """Dark card background with a gradient hairline border."""
    a = C[accent]
    return f'''<defs>
  <linearGradient id="fbg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#070b16"/><stop offset="1" stop-color="{C["bg2"]}"/>
  </linearGradient>
  <linearGradient id="fbd" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{a}" stop-opacity=".75"/>
    <stop offset=".5" stop-color="{C["violet"]}" stop-opacity=".35"/>
    <stop offset="1" stop-color="{C["pink"]}" stop-opacity=".55"/>
  </linearGradient>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{r}" fill="url(#fbg)" stroke="url(#fbd)"/>'''


def chip(x: float, y: float, label: str, color: str, fs: float = 11.5, h: float = 24) -> tuple[str, float]:
    w = len(label) * fs * CW + 20
    return (f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{color}" '
            f'fill-opacity=".08" stroke="{color}" stroke-opacity=".55"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + fs * .36:.1f}" text-anchor="middle" class="mono" '
            f'font-size="{fs}" fill="{C["text"]}">{esc(label)}</text></g>'), w


def discrete(events: list[tuple[float, float]], cycle: float) -> tuple[str, str]:
    """(time, value) events -> SMIL values/keyTimes strings for calcMode=discrete."""
    vals, keys, last = [], [], -1.0
    for t, v in events:
        k = round(t / cycle, 5)
        if k <= last:
            k = last + 0.00001
        vals.append(f"{v:.1f}")
        keys.append(f"{k:.5f}")
        last = k
    return ";".join(vals), ";".join(keys)


# --------------------------------------------------------------------------- header
def render_header() -> str:
    W, H, HZ = 1000, 350, 290  # HZ = horizon of the grid floor
    rnd = random.Random(42)
    rx, ry, R = 862, 150, 88   # radar centre / radius
    style = """
.hud{font:600 10.5px %MONO%;letter-spacing:2.4px;fill:#7d8aa5}
.rise{animation:rise linear infinite}
@keyframes rise{0%{transform:translateY(0);opacity:0}15%{opacity:.45}80%{opacity:.25}100%{transform:translateY(-150px);opacity:0}}
.scan{animation:scan 7s linear infinite}
@keyframes scan{from{transform:translateY(-90px)}to{transform:translateY(370px)}}
.gl{opacity:0;animation:gl 5.5s steps(1) infinite}
.gl2{animation-delay:.07s}
@keyframes gl{0%,86%,100%{opacity:0;transform:translate(0,0)}87%{opacity:.9;transform:translate(-6px,1px)}
89%{opacity:.9;transform:translate(5px,-2px)}91%{opacity:0}94%{opacity:.75;transform:translate(-3px,0)}95%{opacity:0}}
.float{animation:float 6s ease-in-out infinite}
@keyframes float{50%{transform:translateY(-7px)}}
.fade-in{animation:fin 1.4s ease-out both}
@keyframes fin{from{opacity:0;transform:translateX(-14px)}to{opacity:1;transform:none}}
"""
    p = [frame(W, H, 18)]
    p.append(f'''<defs>
  <radialGradient id="hglow" cx=".3" cy=".35" r=".8">
    <stop offset="0" stop-color="{C["violet"]}" stop-opacity=".22"/><stop offset=".55" stop-color="{C["cyan"]}" stop-opacity=".05"/>
    <stop offset="1" stop-color="#000" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="ng" gradientUnits="userSpaceOnUse" x1="40" y1="0" x2="700" y2="0" spreadMethod="reflect">
    <stop offset="0" stop-color="{C["cyan"]}"/><stop offset=".45" stop-color="#ffffff"/>
    <stop offset=".7" stop-color="{C["violet"]}"/><stop offset="1" stop-color="{C["pink"]}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="0 0;520 0;0 0" dur="9s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="floor" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/>
  </linearGradient>
  <mask id="fm"><rect x="0" y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#floor)"/></mask>
  <linearGradient id="hz" x1="0" x2="1"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{C["cyan"]}"/><stop offset="1" stop-color="{C["cyan"]}" stop-opacity="0"/></linearGradient>
  <linearGradient id="scan" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity="0"/>
    <stop offset=".9" stop-color="{C["cyan"]}" stop-opacity=".07"/><stop offset="1" stop-color="{C["cyan"]}" stop-opacity=".35"/></linearGradient>
  <linearGradient id="shg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C["cyan"]}"/>
    <stop offset="1" stop-color="{C["violet"]}"/></linearGradient>
  <clipPath id="clipall"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17"/></clipPath>
  <clipPath id="b1"><rect x="0" y="92" width="720" height="14"/><rect x="0" y="122" width="720" height="9"/></clipPath>
  <clipPath id="b2"><rect x="0" y="106" width="720" height="16"/><rect x="0" y="131" width="720" height="12"/></clipPath>
</defs>
<g clip-path="url(#clipall)">
<rect width="{W}" height="{H}" fill="url(#hglow)"/>''')

    # synthwave grid floor
    g = [f'<g mask="url(#fm)" stroke="{C["cyan"]}" stroke-opacity=".55" stroke-width="1">']
    for xb in range(-1500, 2600, 110):
        xt = 500 + (xb - 500) * 0.08
        g.append(f'<line x1="{xt:.1f}" y1="{HZ}" x2="{xb}" y2="{H}"/>')
    n = 9
    ys = [HZ + (H - HZ) * (k / n) ** 2 for k in range(n + 2)]
    for k in range(n + 1):
        g.append(f'<line x1="0" x2="{W}" y1="{ys[k]:.1f}" y2="{ys[k]:.1f}">'
                 f'<animate attributeName="y1" values="{ys[k]:.1f};{ys[k + 1]:.1f}" dur="1.6s" repeatCount="indefinite"/>'
                 f'<animate attributeName="y2" values="{ys[k]:.1f};{ys[k + 1]:.1f}" dur="1.6s" repeatCount="indefinite"/></line>')
    g.append('</g>')
    p.append("".join(g))
    p.append(f'<rect x="0" y="{HZ - 1}" width="{W}" height="2" fill="url(#hz)" filter="url(#glow)"/>')

    # drifting glyph particles
    glyphs = "01{}<>/#$λ∑⌘⊕"
    for _ in range(34):
        x, y = rnd.uniform(20, W - 20), rnd.uniform(60, H + 20)
        d, delay = rnd.uniform(7, 15), rnd.uniform(0, 15)
        col = rnd.choice([C["cyan"], C["violet"], C["green"]])
        p.append(f'<text class="mono rise" x="{x:.0f}" y="{y:.0f}" font-size="{rnd.choice([10, 11, 12, 13])}" fill="{col}" '
                 f'style="animation-duration:{d:.1f}s;animation-delay:-{delay:.1f}s">{esc(rnd.choice(glyphs))}</text>')

    # HUD
    p.append(f'''<g class="hud">
  <circle cx="34" cy="31" r="4" fill="{C["green"]}" class="blink"/>
  <text x="46" y="35">SECURE SESSION // ZERO-TRUST VERIFIED</text>
  <text x="{W - 32}" y="35" text-anchor="end">SYS://{LOGIN.upper()}  ▸  <tspan fill="{C["green"]}">ONLINE</tspan></text>
</g>
<g stroke="{C["cyan"]}" stroke-opacity=".6" stroke-width="1.5">
  <path d="M14 58 V14 H58"/><path d="M{W - 58} 14 H{W - 14} V58"/>
  <path d="M14 {H - 58} V{H - 14} H58"/><path d="M{W - 58} {H - 14} H{W - 14} V{H - 58}"/>
</g>''')

    # name block
    p.append(f'<text class="mono fade-in" x="58" y="84" font-size="13" letter-spacing="3.5" fill="{C["cyan"]}">{esc(TAGLINE)}</text>')
    name = 'x="56" y="142" font-size="60" font-weight="800" letter-spacing="2"'
    p.append(f'<text {name} class="sans" fill="{C["cyan"]}" opacity=".18" filter="url(#glow)">{NAME}</text>')
    p.append(f'<text {name} class="sans" fill="url(#ng)">{NAME}</text>')
    p.append(f'<text {name} fill="{C["cyan"]}" class="sans gl" clip-path="url(#b1)">{NAME}</text>')
    p.append(f'<text {name} fill="{C["pink"]}" class="sans gl gl2" clip-path="url(#b2)">{NAME}</text>')

    # typing roles
    fs, x0, y0 = 20, 86, 190
    step = fs * CW
    t, per_role = 0.4, []
    for role in ROLES:
        ev = []
        for i in range(len(role)):
            ev.append((t, (i + 1) * step)); t += 0.055
        t += 1.9
        for j in range(len(role)):
            ev.append((t, (len(role) - 1 - j) * step)); t += 0.018
        t += 0.35
        per_role.append(ev)
    cycle = t
    p.append(f'<text class="mono" x="58" y="{y0}" font-size="{fs}" font-weight="700" fill="{C["green"]}">❯</text>')
    cursor_ev = [(0.0, 0.0)]
    for i, (role, ev) in enumerate(zip(ROLES, per_role)):
        vals, keys = discrete([(0.0, 0.0)] + ev, cycle)
        cursor_ev += ev
        p.append(f'<clipPath id="rc{i}"><rect x="{x0 - 2}" y="{y0 - fs}" height="{fs + 10}" width="0">'
                 f'<animate attributeName="width" calcMode="discrete" dur="{cycle:.3f}s" repeatCount="indefinite" '
                 f'values="{vals}" keyTimes="{keys}"/></rect></clipPath>'
                 f'<text class="mono" x="{x0}" y="{y0}" font-size="{fs}" font-weight="600" fill="{C["text"]}" '
                 f'clip-path="url(#rc{i})">{esc(role)}</text>')
    vals, keys = discrete([(tt, x0 + v + 2) for tt, v in cursor_ev], cycle)
    p.append(f'<rect y="{y0 - fs + 3}" width="11" height="{fs + 2}" fill="{C["cyan"]}" class="blink" x="{x0}">'
             f'<animate attributeName="x" calcMode="discrete" dur="{cycle:.3f}s" repeatCount="indefinite" '
             f'values="{vals}" keyTimes="{keys}"/></rect>')

    clients = "  ·  ".join(c for _, org, _, cl in CAREER for c in cl if c != "Intermex")
    clients = clients.replace("CareFirst BlueCross BlueShield", "CareFirst")
    p.append(f'''<text class="mono fade-in" x="58" y="232" font-size="12.5" fill="{C["muted"]}" xml:space="preserve" style="white-space:pre;animation-delay:.4s"><tspan fill="{C["green"]}">▸ Securing Fortune 500 clouds for</tspan>  <tspan fill="{C["text"]}">{esc(clients)}</tspan></text>
<text class="mono fade-in" x="58" y="258" font-size="12.5" fill="{C["muted"]}" xml:space="preserve" style="white-space:pre;animation-delay:.6s">{YEARS} YOE   ·   <tspan fill="{C["amber"]}">{len(CERTS)}× Certified</tspan>   ·   <tspan fill="{C["violet"]}">@AHEAD</tspan>   ·   Gurgaon, IN</text>''')

    # radar + shield
    sweep = [f'<g><animateTransform attributeName="transform" type="rotate" from="0 {rx} {ry}" to="360 {rx} {ry}" dur="4s" repeatCount="indefinite"/>']
    for k in range(14):
        a0, a1 = math.radians(-(k + 1) * 4.5), math.radians(-k * 4.5)
        sweep.append(f'<path d="M{rx} {ry} L{rx + R * math.cos(a0):.1f} {ry + R * math.sin(a0):.1f} '
                     f'A{R} {R} 0 0 1 {rx + R * math.cos(a1):.1f} {ry + R * math.sin(a1):.1f} Z" '
                     f'fill="{C["cyan"]}" fill-opacity="{.32 * (1 - k / 14):.3f}"/>')
    sweep.append(f'<line x1="{rx}" y1="{ry}" x2="{rx + R}" y2="{ry}" stroke="{C["cyan"]}" stroke-width="1.5" filter="url(#glow)"/></g>')
    blips = []
    for ang, rr, lab in [(35, .72, "IAM"), (128, .55, "S3"), (205, .8, "AKS"), (300, .62, "KMS"), (250, .35, "VPC")]:
        bx, by = rx + R * rr * math.cos(math.radians(ang)), ry + R * rr * math.sin(math.radians(ang))
        begin = ang / 360 * 4
        anim = (f'<animate attributeName="opacity" values="1;0;0" keyTimes="0;.45;1" dur="4s" '
                f'begin="{begin:.2f}s" repeatCount="indefinite"/>')
        blips.append(f'<g opacity="0">{anim}<circle cx="{bx:.1f}" cy="{by:.1f}" r="3.2" fill="{C["green"]}" filter="url(#glow)"/>'
                     f'<text class="mono" x="{bx + 6:.1f}" y="{by - 5:.1f}" font-size="8.5" fill="{C["green"]}">{lab} ✓</text></g>')
    ticks = "".join(
        f'<text class="mono" x="{rx + (R + 32) * math.cos(math.radians(a - 90)):.1f}" '
        f'y="{ry + (R + 32) * math.sin(math.radians(a - 90)) + 3:.1f}" font-size="8" fill="{C["dim"]}" '
        f'text-anchor="middle">{a:03d}</text>' for a in (0, 90, 180, 270))
    p.append(f'''<g class="float"><g>
  <circle cx="{rx}" cy="{ry}" r="{R}" fill="#061021" fill-opacity=".7" stroke="{C["cyan"]}" stroke-opacity=".35"/>
  <circle cx="{rx}" cy="{ry}" r="{R * .66:.0f}" stroke="{C["cyan"]}" stroke-opacity=".18"/>
  <circle cx="{rx}" cy="{ry}" r="{R * .33:.0f}" stroke="{C["cyan"]}" stroke-opacity=".18"/>
  <path d="M{rx - R} {ry} H{rx + R} M{rx} {ry - R} V{ry + R}" stroke="{C["cyan"]}" stroke-opacity=".15"/>
  {"".join(sweep)}{"".join(blips)}
  <circle cx="{rx}" cy="{ry}" r="{R + 12}" stroke="{C["cyan"]}" stroke-opacity=".45" stroke-dasharray="2 6">
    <animateTransform attributeName="transform" type="rotate" from="0 {rx} {ry}" to="360 {rx} {ry}" dur="30s" repeatCount="indefinite"/></circle>
  <circle cx="{rx}" cy="{ry}" r="{R + 22}" stroke="{C["violet"]}" stroke-opacity=".55" stroke-width="2" stroke-dasharray="46 22 6 22">
    <animateTransform attributeName="transform" type="rotate" from="360 {rx} {ry}" to="0 {rx} {ry}" dur="18s" repeatCount="indefinite"/></circle>
  {ticks}
  <circle cx="{rx}" cy="{ry}" r="40" stroke="{C["cyan"]}" fill="none">
    <animate attributeName="r" values="40;105" dur="2.6s" repeatCount="indefinite"/>
    <animate attributeName="stroke-opacity" values=".7;0" dur="2.6s" repeatCount="indefinite"/></circle>
  <g transform="translate({rx} {ry + 2}) scale(.92)">
    <path d="M0 -52 L44 -37 V-2 C44 28 22 45 0 54 C-22 45 -44 28 -44 -2 V-37 Z" fill="#071226" stroke="url(#shg)" stroke-width="3" filter="url(#glow)"/>
    <path d="M0 -40 L33 -29 V-2 C33 21 17 34 0 41 C-17 34 -33 21 -33 -2 V-29 Z" fill="none" stroke="{C["cyan"]}" stroke-opacity=".3"/>
    <path d="M-10 -4 V-13 A10 10 0 0 1 10 -13 V-4" stroke="{C["cyan"]}" stroke-width="3.2" stroke-linecap="round"/>
    <rect x="-16" y="-5" width="32" height="25" rx="5" fill="{C["cyan"]}" filter="url(#glow)"/>
    <circle cx="0" cy="5" r="3.6" fill="#071226"/><rect x="-1.6" y="6" width="3.2" height="8" rx="1.5" fill="#071226"/>
  </g>
</g></g>''')

    p.append(f'<rect class="scan" x="0" y="0" width="{W}" height="90" fill="url(#scan)"/>')
    p.append('</g>')
    return svg(W, H, "\n".join(p), f"{NAME.title()}: Cloud Security & DevSecOps Engineer", style)


# --------------------------------------------------------------------------- terminal
def render_terminal() -> str:
    c = C
    K, S, V, A = c["violet"], c["green"], c["text"], c["amber"]
    lines = [
        ("cmd", [("whoami", V)]),
        ("out", [("prashant.kumar", c["cyan"]), ("  —  Cloud Security & DevSecOps Engineer @ ", V), ("AHEAD", K)]),
        ("cmd", [("cat ", V), ("~/.config/profile.yaml", c["cyan"])]),
        ("out", [("role:       ", K), ('"Cloud Security · DevSecOps · Platform Engineering"', S)]),
        ("out", [("location:   ", K), ('"Gurgaon, Haryana, India"', S)]),
        ("out", [("experience: ", K), (f'"{YEARS} years securing & scaling Fortune 500 cloud platforms"', S)]),
        ("out", [("clients:    ", K), ("[carefirst, csx, stellantis, intermex, hsbc]", c["cyan"])]),
        ("out", [("certified:", K)]),
        ("out", [("  - ", c["muted"]), ('"Microsoft Certified: Cybersecurity Architect Expert"', c["ms"])]),
        ("out", [("  - ", c["muted"]), ('"AWS Certified DevOps Engineer – Professional"', A)]),
        ("out", [("  - ", c["muted"]), ('"+5 more: AWS SA Pro · Azure DevOps Expert · Azure Security · Azure Admin · Wiz"',
                                         c["muted"])]),
        ("out", [("clouds:     ", K), ("[aws, azure, gcp]", c["cyan"])]),
        ("out", [("focus:      ", K), ("[cnapp, cspm, iam, shift-left, policy-as-code, finops]", c["cyan"])]),
        ("out", [("now:        ", K), ('"Wiz findings → evidence → approval-gated remediation"', S)]),
        ("out", [("motto:      ", K), (f'"{MOTTO}"', c["pink"])]),
        ("out", [("contact:    ", K), (f'"{EMAIL}"', c["cyan"])]),
        ("cmd", [("./posture-check ", V), ("--env prod --strict", c["muted"])]),
        ("out", [("[ PASS ]", S), (" least-privilege IAM         ", V), ("[ PASS ]", S), (" secrets vaulted & rotated", V)]),
        ("out", [("[ PASS ]", S), (" IaC policy gates            ", V), ("[ PASS ]", S), (" supply chain pinned & signed", V)]),
        ("out", [("✔ posture: HARDENED", S), ("   ·   drift: none   ·   ready to ship", c["muted"])]),
    ]
    fs, lh, x0, y0 = 14, 22.5, 30, 80
    step = fs * CW
    W, H = 1000, int(y0 + lh * (len(lines) + 1) + 6)

    t, timeline, prev = 0.6, [], "cmd"
    for kind, segs in lines:
        if kind == "cmd":
            t += 0.5 if prev == "out" else 0
            timeline.append(t)
            t += 0.3 + len("".join(s for s, _ in segs)) * 0.05 + 0.35
        else:
            timeline.append(t)
            t += 0.1
        prev = kind
    end = t + 0.4
    cycle = end + 9

    def pct(x: float) -> str:
        return f"{x / cycle * 100:.2f}%"

    style = []
    body = [frame(W, H, 14, "green")]
    body.append(f'''<rect x="1" y="1" width="{W - 2}" height="38" rx="13" fill="#0e1528"/>
<rect x="1" y="26" width="{W - 2}" height="13" fill="#0e1528"/>
<line x1="1" y1="39" x2="{W - 1}" y2="39" stroke="{c["line"]}"/>
<circle cx="24" cy="20" r="6" fill="#ff5f57"/><circle cx="44" cy="20" r="6" fill="#febc2e"/><circle cx="64" cy="20" r="6" fill="#28c840"/>
<text class="mono" x="{W / 2}" y="24.5" text-anchor="middle" font-size="12" fill="{c["muted"]}">prashant@ahead: ~/sec-ops — zsh</text>
<text class="mono" x="{W - 24}" y="24.5" text-anchor="end" font-size="11" fill="{c["green"]}">● encrypted</text>''')

    for i, ((kind, segs), ts) in enumerate(zip(lines, timeline)):
        y = y0 + i * lh
        style.append(f".l{i}{{animation:l{i} {cycle:.2f}s linear infinite}}"
                     f"@keyframes l{i}{{0%,{pct(ts)}{{opacity:0}}{pct(ts + .2)}{{opacity:1}}96%{{opacity:1}}100%{{opacity:0}}}}")
        spans = "".join(f'<tspan fill="{col}">{esc(s)}</tspan>' for s, col in segs)
        if kind == "cmd":
            n = len("".join(s for s, _ in segs))
            ev = [(0.0, 0.0), (ts, 2 * step)]
            ev += [(ts + 0.3 + k * 0.05, (k + 3) * step) for k in range(n)]
            ev.append((cycle * 0.96, 0.0))
            vals, keys = discrete(ev, cycle)
            body.append(f'<clipPath id="tc{i}"><rect x="{x0 - 4}" y="{y - fs - 2}" height="{lh}" width="0">'
                        f'<animate attributeName="width" calcMode="discrete" dur="{cycle:.2f}s" repeatCount="indefinite" '
                        f'values="{vals}" keyTimes="{keys}"/></rect></clipPath>')
            body.append(f'<text class="mono tl l{i}" x="{x0}" y="{y}" font-size="{fs}" xml:space="preserve" '
                        f'style="white-space:pre" clip-path="url(#tc{i})"><tspan fill="{c["green"]}" font-weight="700">❯ </tspan>{spans}</text>')
        else:
            body.append(f'<text class="mono tl l{i}" x="{x0 + 2 * step}" y="{y}" font-size="{fs}" xml:space="preserve" '
                        f'style="white-space:pre">{spans}</text>')

    i = len(lines)
    y = y0 + i * lh
    style.append(f".l{i}{{animation:l{i} {cycle:.2f}s linear infinite}}"
                 f"@keyframes l{i}{{0%,{pct(end)}{{opacity:0}}{pct(end + .1)}{{opacity:1}}96%{{opacity:1}}100%{{opacity:0}}}}")
    body.append(f'<g class="tl l{i}"><text class="mono" x="{x0}" y="{y}" font-size="{fs}" font-weight="700" fill="{c["green"]}">❯</text>'
                f'<rect class="blink" x="{x0 + 2 * step}" y="{y - fs + 1}" width="{step}" height="{fs + 3}" fill="{c["cyan"]}"/></g>')
    return svg(W, H, "\n".join(body), "Terminal: whoami — Prashant Kumar, Cloud Security & DevSecOps Engineer at AHEAD",
               "\n".join(style))


# --------------------------------------------------------------------------- infinity loop
def render_loop() -> str:
    W, H = 1000, 384
    cx, cy, a = 500, 196, 330

    def pt(t: float) -> tuple[float, float]:
        d = 1 + math.sin(t) ** 2
        return cx + a * math.cos(t) / d, cy + a * math.sin(t) * math.cos(t) / d

    ts = [math.pi / 2 + 2 * math.pi * k / 300 for k in range(301)]
    path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in map(pt, ts)) + " Z"

    stages = [
        (math.pi / 2 + .55, "PLAN", "Threat Modeling", "green"),
        (math.pi - .32, "CODE", "SAST · Secrets", "green"),
        (math.pi + .32, "BUILD", "SCA · SBOM", "cyan"),
        (3 * math.pi / 2 - .55, "TEST", "DAST · IaC Scan", "cyan"),
        (3 * math.pi / 2 + .55, "RELEASE", "Sign · Attest", "violet"),
        (2 * math.pi - .32, "DEPLOY", "Policy-as-Code", "violet"),
        (2 * math.pi + .32, "OPERATE", "CSPM · CNAPP", "pink"),
        (5 * math.pi / 2 - .55, "MONITOR", "SIEM · Detect", "pink"),
    ]
    style = """
.flow{stroke-dasharray:2 16;animation:flow 1.2s linear infinite}
@keyframes flow{to{stroke-dashoffset:-18}}
.pulse{animation:pulse 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes pulse{50%{transform:scale(1.6);opacity:.35}}
.lbl{animation:lbl 9s ease-in-out infinite}
@keyframes lbl{0%,100%{opacity:.85}50%{opacity:1}}
"""
    b = [frame(W, H, 16, "violet")]
    b.append(f'''<defs>
  <linearGradient id="ig" gradientUnits="userSpaceOnUse" x1="170" y1="0" x2="830" y2="0">
    <stop offset="0" stop-color="{C["green"]}"/><stop offset=".35" stop-color="{C["cyan"]}"/>
    <stop offset=".65" stop-color="{C["violet"]}"/><stop offset="1" stop-color="{C["pink"]}"/>
  </linearGradient>
  <linearGradient id="tg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>
    <stop offset="1" stop-color="#fff" stop-opacity=".03"/></linearGradient>
  <filter id="soft" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
  <path id="inf" d="{path}"/>
</defs>
<text class="sans" x="{cx - a * .58:.0f}" y="{cy + 14}" text-anchor="middle" font-size="44" font-weight="800" letter-spacing="10" fill="url(#tg)">DEV</text>
<text class="sans" x="{cx + a * .58:.0f}" y="{cy + 14}" text-anchor="middle" font-size="44" font-weight="800" letter-spacing="10" fill="url(#tg)">OPS</text>
<text class="mono" x="{cx - a * .58:.0f}" y="{cy + 38}" text-anchor="middle" font-size="10.5" letter-spacing="2" fill="{C["green"]}" opacity=".7">◂ SHIFT LEFT</text>
<text class="mono" x="{cx + a * .58:.0f}" y="{cy + 38}" text-anchor="middle" font-size="10.5" letter-spacing="2" fill="{C["pink"]}" opacity=".7">SHIELD RIGHT ▸</text>
<use href="#inf" stroke="url(#ig)" stroke-width="14" opacity=".35" filter="url(#soft)"/>
<use href="#inf" stroke="url(#ig)" stroke-width="3.2"/>
<use href="#inf" class="flow" stroke="#fff" stroke-opacity=".7" stroke-width="2" stroke-linecap="round"/>''')

    for k in range(8):
        col = [C["cyan"], C["green"], C["violet"], C["pink"]][k % 4]
        b.append(f'<circle r="4.5" fill="{col}" filter="url(#glow)"><animateMotion dur="10s" begin="-{k * 1.25:.2f}s" '
                 f'repeatCount="indefinite" rotate="auto"><mpath href="#inf"/></animateMotion></circle>')

    for t, name, ctrl, col in stages:
        x, y = pt(t)
        colr = C[col]
        outer = abs(x - cx) > a * .6
        if outer:  # outer nodes sit on the steep part of the curve, so label them sideways
            side = -1 if x < cx else 1
            lx, anchor, ny, cyy = x + side * 18, "end" if side < 0 else "start", y - 1, y + 15
        else:
            up = y < cy
            lx, anchor = x, "middle"
            ny, cyy = (y - 38, y - 21) if up else (y + 33, y + 50)
        b.append(f'''<g><circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{colr}" fill-opacity=".25" class="pulse"/>
<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{C["bg"]}" stroke="{colr}" stroke-width="2.5"/>
<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{colr}"/>
<text class="sans lbl" x="{lx:.1f}" y="{ny:.1f}" text-anchor="{anchor}" font-size="15" font-weight="800" letter-spacing="2.5" fill="{C["text"]}">{name}</text>
<text class="mono" x="{lx:.1f}" y="{cyy:.1f}" text-anchor="{anchor}" font-size="11.5" fill="{colr}">{esc(ctrl)}</text></g>''')

    b.append(f'''<g transform="translate({cx} {cy})">
  <circle r="30" fill="{C["bg"]}" stroke="url(#ig)" stroke-width="1.5"/>
  <circle r="38" stroke="{C["cyan"]}" stroke-opacity=".5" stroke-dasharray="3 5">
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="14s" repeatCount="indefinite"/></circle>
  <g transform="scale(.42)">
    <path d="M0 -52 L44 -37 V-2 C44 28 22 45 0 54 C-22 45 -44 28 -44 -2 V-37 Z" fill="#071226" stroke="{C["cyan"]}" stroke-width="5" filter="url(#glow)"/>
    <path d="M-16 0 L-4 12 L18 -14" stroke="{C["green"]}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
  </g>
</g>
<text class="mono" x="{cx}" y="{H - 14}" text-anchor="middle" font-size="11.5" letter-spacing="1.5" fill="{C["muted"]}">every stage gated  ·  every artifact verified  ·  every finding owned</text>''')
    return svg(W, H, "\n".join(b), "DevSecOps infinity loop with a security control at every stage", style)


# --------------------------------------------------------------------------- arsenal
def render_arsenal() -> str:
    W, m, gap = 1000, 20, 14
    pw = (W - 2 * m - 3 * gap) / 4
    fs, ch, top = 11, 24, 78
    layouts, max_y = [], 0
    for title, col, items in ARSENAL:
        x, y, rows = 14, top, []
        for it in items:
            w = len(it) * fs * CW + 20
            if x + w > pw - 14:
                x, y = 14, y + ch + 8
            rows.append((x, y, it))
            x += w + 7
        layouts.append(rows)
        max_y = max(max_y, y + ch)
    H = int(max_y + 46)
    style = """
.sweep{animation:sweep 5s ease-in-out infinite}
@keyframes sweep{0%{transform:translateX(-60px);opacity:0}20%{opacity:1}60%,100%{transform:translateX(240px);opacity:0}}
.cin{animation:cin .6s ease-out both}
@keyframes cin{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
"""
    b = [frame(W, H, 16)]
    for i, ((title, col, items), rows) in enumerate(zip(ARSENAL, layouts)):
        px, colr = m + i * (pw + gap), C[col]
        b.append(f'''<g transform="translate({px:.1f} 18)">
<clipPath id="pc{i}"><rect width="{pw:.1f}" height="{H - 36}" rx="12"/></clipPath>
<rect width="{pw:.1f}" height="{H - 36}" rx="12" fill="{colr}" fill-opacity=".035" stroke="{colr}" stroke-opacity=".3"/>
<g clip-path="url(#pc{i})"><rect y="0" width="{pw:.1f}" height="3" fill="{colr}" opacity=".35"/>
<rect class="sweep" y="0" width="70" height="3" fill="{colr}" filter="url(#glow)" style="animation-delay:{i * .6:.1f}s"/></g>
<text class="mono" x="14" y="34" font-size="12" font-weight="700" fill="{colr}">[0{i + 1}]</text>
<text class="sans" x="50" y="34" font-size="13.5" font-weight="800" letter-spacing="2" fill="{C["text"]}">{esc(title)}</text>
<line x1="14" x2="{pw - 14:.1f}" y1="50" y2="50" stroke="{colr}" stroke-opacity=".25" stroke-dasharray="3 4"/>''')
        for j, (x, y, it) in enumerate(rows):
            el, _ = chip(x, y - 18, it, colr, fs, ch)
            b.append(f'<g class="cin" style="animation-delay:{.15 + i * .12 + j * .06:.2f}s">{el}</g>')
        b.append('</g>')
    return svg(W, H, "\n".join(b), "Arsenal: cloud platforms, cloud security, DevSecOps and automation tooling", style)


# --------------------------------------------------------------------------- project cards
LANG_COLORS = {"Python": "#3572A5", "PowerShell": "#012456", "Shell": "#89e051", "HCL": "#844FBA"}


def render_project(p: dict, live: dict) -> str:
    wide = p.get("wide", False)
    W, H = (1000, 206) if wide else (490, 236)
    info = live.get(p["repo"], {})
    lang = info.get("lang") or "Python"
    lcol = info.get("color") or LANG_COLORS.get(lang, C["cyan"])
    accent = "cyan" if p["public"] else "amber"
    ac = C[accent]
    style = """
.comet{animation:comet 7s linear infinite}
@keyframes comet{to{stroke-dashoffset:-100}}
"""
    b = [frame(W, H, 16, accent)]
    b.append(f'<rect class="comet" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="15" pathLength="100" '
             f'stroke="{ac}" stroke-width="2" stroke-dasharray="10 90" filter="url(#glow)"/>')
    badge = "● PUBLIC REPO" if p["public"] else "● PRIVATE · INTERNAL"
    bw = len(badge) * 10 * CW + 20
    b.append(f'<rect x="22" y="20" width="{bw:.0f}" height="22" rx="11" fill="{ac}" fill-opacity=".1" stroke="{ac}" stroke-opacity=".5"/>'
             f'<text class="mono" x="{22 + bw / 2:.0f}" y="35" text-anchor="middle" font-size="10" font-weight="700" '
             f'letter-spacing="1" fill="{ac}">{badge}</text>')
    pill = f"CLIENT · {p['client'].upper()}" if p.get("client") else p.get("label")
    if pill:
        pc = C["violet"] if p.get("client") else C["green"]
        cw = len(pill) * 10 * CW + 20
        b.append(f'<rect x="{30 + bw:.0f}" y="20" width="{cw:.0f}" height="22" rx="11" fill="{pc}" fill-opacity=".12" '
                 f'stroke="{pc}" stroke-opacity=".6"/><text class="mono" x="{30 + bw + cw / 2:.0f}" y="35" '
                 f'text-anchor="middle" font-size="10" font-weight="700" letter-spacing="1" fill="{pc}">{esc(pill)}</text>')
    meta = f'<tspan fill="{lcol}">●</tspan> {esc(lang)}'
    if p["public"] and info.get("stars"):
        meta += f'   <tspan fill="{C["amber"]}">★</tspan> {info.get("stars", 0)}'
    b.append(f'<text class="mono" x="{W - 22}" y="35" text-anchor="end" font-size="11.5" fill="{C["muted"]}" '
             f'xml:space="preserve" style="white-space:pre">{meta}</text>')
    title = p["repo"]
    b.append(f'<text class="sans" x="22" y="82" font-size="23" font-weight="800" fill="{C["text"]}">{esc(title)}</text>')
    b.append(f'<text class="mono" x="22" y="106" font-size="12" fill="{ac}">› {esc(p["tagline"])}</text>')
    wrap = textwrap.wrap(p["desc"], 132 if wide else 64)
    if len(wrap) > (2 if wide else 3):
        raise ValueError(f"{p['repo']}: description too long for the card ({len(wrap)} lines)")
    for k, ln in enumerate(wrap):
        b.append(f'<text class="sans" x="22" y="{134 + k * 19}" font-size="13.5" fill="#b4bfd3">{esc(ln)}</text>')
    cta = "OPEN REPO ↗" if p["public"] else "◆ INTERNAL TOOLING"
    x = 22
    for tg in p["tags"]:
        el, w = chip(x, H - 40, tg, ac, 10.5, 22)
        b.append(el)
        x += w + 7
    if x > W - 22 - len(cta) * (11 * CW + 1.5) - 8:
        raise ValueError(f"{p['repo']}: tags overlap the '{cta}' label")
    b.append(f'<text class="mono" x="{W - 22}" y="{H - 24}" text-anchor="end" font-size="11" font-weight="700" '
             f'letter-spacing="1.5" fill="{ac}">{cta}</text>')
    return svg(W, H, "\n".join(b), f"{title}: {p['tagline']}", style)


# --------------------------------------------------------------------------- section headers
def render_section(num: str, title: str, sub: str) -> str:
    W, H = 1000, 58
    style = """
.glint{animation:glint 4.5s ease-in-out infinite}
@keyframes glint{0%{transform:translateX(-160px)}70%,100%{transform:translateX(1060px)}}
"""
    b = [frame(W, H, 12), f'''<defs><linearGradient id="sl" x1="0" x2="1"><stop offset="0" stop-color="{C["cyan"]}"/>
<stop offset=".5" stop-color="{C["violet"]}"/><stop offset="1" stop-color="{C["pink"]}" stop-opacity=".2"/></linearGradient>
<linearGradient id="gl" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".18"/>
<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="sc"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="11"/></clipPath></defs>
<g clip-path="url(#sc)"><rect class="glint" x="0" y="0" width="140" height="{H}" fill="url(#gl)" transform="skewX(-20)"/>
<rect x="0" y="{H - 3}" width="{W}" height="3" fill="url(#sl)"/></g>
<text class="sans" x="22" y="41" font-size="30" font-weight="800" fill="none" stroke="{C["cyan"]}" stroke-width="1.2">{num}</text>
<text class="sans" x="74" y="38" font-size="19" font-weight="800" letter-spacing="4" fill="{C["text"]}">{esc(title)}</text>
<rect class="blink" x="{W - 30}" y="24" width="9" height="15" fill="{C["green"]}"/>
<text class="mono" x="{W - 40}" y="37" text-anchor="end" font-size="12" fill="{C["muted"]}">{esc(sub)}</text>''']
    return svg(W, H, "\n".join(b), f"{num} {title}", style)


# --------------------------------------------------------------------------- buttons
def render_button(kind: str) -> str:
    style = """
.shine{animation:shine 4s ease-in-out infinite}
@keyframes shine{0%{transform:translateX(-80px)}55%,100%{transform:translateX(420px)}}
"""
    if kind == "linkedin":
        W, accent = 250, "cyan"
        icon = (f'<rect x="14" y="11" width="24" height="24" rx="5" fill="#0a66c2"/>'
                f'<text class="sans" x="26" y="29" text-anchor="middle" font-size="15" font-weight="800" fill="#fff">in</text>')
        label = f'<text class="mono" x="50" y="28" font-size="12.5" font-weight="700" letter-spacing="1.6" fill="{C["text"]}">CONNECT ON LINKEDIN</text>'
        title = "Connect on LinkedIn"
    elif kind == "github":
        W, accent = 220, "violet"
        icon = (f'<rect x="14" y="11" width="24" height="24" rx="5" fill="{C["violet"]}" fill-opacity=".2" stroke="{C["violet"]}"/>'
                f'<text class="mono" x="26" y="27.5" text-anchor="middle" font-size="10.5" font-weight="800" fill="{C["text"]}">&lt;/&gt;</text>')
        label = f'<text class="mono" x="50" y="28" font-size="12.5" font-weight="700" letter-spacing="1.6" fill="{C["text"]}">EXPLORE REPOS</text>'
        title = "Explore repositories"
    elif kind == "email":
        W, accent = 330, "green"
        icon = (f'<rect x="14" y="12" width="24" height="18" rx="3" fill="{C["green"]}" fill-opacity=".15" stroke="{C["green"]}" stroke-width="1.5"/>'
                f'<path d="M15 13 L26 23 L37 13" stroke="{C["green"]}" stroke-width="1.5" fill="none"/>')
        label = f'<text class="mono" x="50" y="28" font-size="12.5" font-weight="700" letter-spacing=".6" fill="{C["text"]}">{esc(EMAIL)}</text>'
        title = f"Email {EMAIL}"
    else:
        raise ValueError(kind)
    H = 46
    b = [frame(W, H, 23, accent), f'''<defs><linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>
<stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="bc"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="22"/></clipPath></defs>
<g clip-path="url(#bc)"><rect class="shine" x="0" y="0" width="60" height="{H}" fill="url(#sh)" transform="skewX(-20)"/></g>
{icon}{label}''']
    return svg(W, H, "\n".join(b), title, style)


# --------------------------------------------------------------------------- certifications
ISSUERS = {
    "aws": ("AWS CERTIFIED", "amber", C["aws"]),
    "microsoft": ("MICROSOFT CERTIFIED", "ms", C["ms"]),
    "wiz": ("WIZ CERTIFIED", "violet", C["wiz"]),
}


def issuer_logo(issuer: str, cx: float, cy: float) -> str:
    if issuer == "aws":
        pts = " ".join(f"{cx + 22 * math.cos(math.radians(a)):.1f},{cy + 22 * math.sin(math.radians(a)):.1f}"
                       for a in range(30, 390, 60))
        return (f'<polygon points="{pts}" fill="{C["aws"]}" fill-opacity=".14" stroke="{C["aws"]}" stroke-width="2"/>'
                f'<text class="sans" x="{cx}" y="{cy + 4.5}" text-anchor="middle" font-size="12.5" font-weight="800" fill="{C["aws"]}">AWS</text>')
    if issuer == "microsoft":
        sq = [("#f25022", -1, -1), ("#7fba00", 1, -1), ("#00a4ef", -1, 1), ("#ffb900", 1, 1)]
        return "".join(f'<rect x="{cx + (dx - 1) * 10.5 + (1 if dx > 0 else 0):.1f}" y="{cy + (dy - 1) * 10.5 + (1 if dy > 0 else 0):.1f}" '
                       f'width="19.5" height="19.5" fill="{col}"/>' for col, dx, dy in sq)
    return (f'<circle cx="{cx}" cy="{cy}" r="21" fill="{C["wiz"]}" fill-opacity=".16" stroke="{C["wiz"]}" stroke-width="2"/>'
            f'<text class="sans" x="{cx}" y="{cy + 5.5}" text-anchor="middle" font-size="15" font-weight="800" fill="{C["wiz"]}">wiz</text>')


def render_cert(issuer: str, level: str, name: str) -> str:
    W, H = 490, 104
    head, accent, col = ISSUERS[issuer]
    style = """
.comet{animation:comet 6s linear infinite}
@keyframes comet{to{stroke-dashoffset:-100}}
.seal{animation:seal 12s linear infinite;transform-box:fill-box;transform-origin:center}
@keyframes seal{to{transform:rotate(360deg)}}
"""
    lw = len(level) * 9.5 * CW + 18
    sx, sy = W - 52, 42
    b = [frame(W, H, 14, accent), f'''<rect class="comet" x="1" y="1" width="{W - 2}" height="{H - 2}" rx="13" pathLength="100"
 stroke="{col}" stroke-width="2" stroke-dasharray="8 92" filter="url(#glow)"/>
{issuer_logo(issuer, 46, 50)}
<text class="mono" x="86" y="34" font-size="10" font-weight="700" letter-spacing="2" fill="{col}">{head}</text>
<text class="sans" x="86" y="60" font-size="17" font-weight="800" fill="{C["text"]}">{esc(name)}</text>
<rect x="86" y="70" width="{lw:.0f}" height="20" rx="10" fill="{col}" fill-opacity=".12" stroke="{col}" stroke-opacity=".55"/>
<text class="mono" x="{86 + lw / 2:.0f}" y="84" text-anchor="middle" font-size="9.5" font-weight="700" letter-spacing="1.2" fill="{col}">{level}</text>
<circle class="seal" cx="{sx}" cy="{sy}" r="22" stroke="{col}" stroke-opacity=".7" stroke-width="1.5" stroke-dasharray="3 3"/>
<circle cx="{sx}" cy="{sy}" r="15" fill="{col}" fill-opacity=".15" stroke="{col}"/>
<path d="M{sx - 7} {sy} l5 5 l9 -10" stroke="{C["green"]}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
<text class="mono" x="{sx}" y="{H - 16}" text-anchor="middle" font-size="10.5" font-weight="700" letter-spacing="1.2" fill="{col}">VERIFY ↗</text>''']
    return svg(W, H, "\n".join(b), f"{head.title()}: {name}", style)


# --------------------------------------------------------------------------- impact
def render_impact() -> str:
    W, TOP = 1000, 396  # TOP = height of the timeline + outcomes area; the posture strip sits below it
    H = TOP + 138
    style = """
.tile{animation:tup .7s ease-out both}
@keyframes tup{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.pulse{animation:pulse 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}
@keyframes pulse{50%{transform:scale(1.7);opacity:.3}}
.flow{stroke-dasharray:3 9;animation:flow 1.4s linear infinite}
@keyframes flow{to{stroke-dashoffset:-12}}
"""
    b = [frame(W, H, 16), f'''<defs><linearGradient id="vg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/>
<stop offset="1" stop-color="{C["cyan"]}"/></linearGradient>
<linearGradient id="tl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["cyan"]}"/><stop offset=".6" stop-color="{C["violet"]}"/>
<stop offset="1" stop-color="{C["pink"]}" stop-opacity=".3"/></linearGradient></defs>''']

    # mission log (career timeline)
    lx, lw = 20, 360
    b.append(f'''<rect x="{lx}" y="18" width="{lw}" height="{TOP - 36}" rx="12" fill="#ffffff" fill-opacity=".02" stroke="{C["line"]}"/>
<text class="mono" x="{lx + 18}" y="44" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{C["muted"]}">MISSION LOG // CAREER</text>
<line x1="{lx + 28}" y1="72" x2="{lx + 28}" y2="{TOP - 46}" stroke="url(#tl)" stroke-width="2"/>
<line x1="{lx + 28}" y1="72" x2="{lx + 28}" y2="{TOP - 46}" stroke="#fff" stroke-opacity=".6" stroke-width="2" class="flow"/>''')
    y = 82
    for k, (when, org, role, clients) in enumerate(CAREER):
        col = C["cyan"] if k == 0 else C["violet"]
        b.append(f'''<circle cx="{lx + 28}" cy="{y - 4}" r="9" fill="{col}" fill-opacity=".3" class="pulse"/>
<circle cx="{lx + 28}" cy="{y - 4}" r="6" fill="{C["bg"]}" stroke="{col}" stroke-width="2.5"/>
<text class="mono" x="{lx + 50}" y="{y}" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{col}">{when}</text>
<text class="sans" x="{lx + 50}" y="{y + 27}" font-size="21" font-weight="800" fill="{C["text"]}">{esc(org)}</text>
<text class="mono" x="{lx + 50}" y="{y + 47}" font-size="11.5" fill="{C["muted"]}">{esc(role)}</text>''')
        cx, cy = lx + 50, y + 58
        for cl in clients:
            w = len(cl) * 10 * CW + 20
            if cx + w > lx + lw - 14:
                cx, cy = lx + 50, cy + 28
            el, w = chip(cx, cy, cl, col, 10, 22)
            b.append(el)
            cx += w + 6
        y = cy + 56
    b.append(f'''<circle cx="{lx + 28}" cy="{y - 4}" r="6" fill="{C["bg"]}" stroke="{C["pink"]}" stroke-width="2.5"/>
<text class="mono" x="{lx + 50}" y="{y}" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{C["pink"]}">2021</text>
<text class="sans" x="{lx + 50}" y="{y + 22}" font-size="14" font-weight="700" fill="{C["text"]}">B.Sc. · ITM University, Gwalior</text>''')

    # outcomes grid
    gx, gw, gap = 396, W - 396 - 20, 12
    tw, th = (gw - 2 * gap) / 3, (TOP - 36 - 30 - gap) / 2
    b.append(f'<text class="mono" x="{gx + 4}" y="44" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{C["muted"]}">'
             f'OUTCOMES // MEASURED IMPACT</text>')
    for i, (val, label, client, col) in enumerate(IMPACT):
        x, y = gx + (i % 3) * (tw + gap), 58 + (i // 3) * (th + gap)
        colr = C[col]
        fs = min(40, (tw - 32) / (len(val) * .6))
        lines = textwrap.wrap(label, 26)
        b.append(f'''<g class="tile" style="animation-delay:{i * .12:.2f}s">
<rect x="{x:.1f}" y="{y:.1f}" width="{tw:.1f}" height="{th:.1f}" rx="12" fill="{colr}" fill-opacity=".05" stroke="{colr}" stroke-opacity=".32"/>
<rect x="{x + 16:.1f}" y="{y:.1f}" width="{tw - 32:.1f}" height="2.5" fill="{colr}" filter="url(#glow)"/>
<text class="mono" x="{x + 16:.1f}" y="{y + 28:.1f}" font-size="9.5" font-weight="700" letter-spacing="1.5" fill="{colr}">◆ {esc(client.upper())}</text>
<text class="sans" x="{x + 14:.1f}" y="{y + 28 + fs + 10:.1f}" font-size="{fs:.1f}" font-weight="800" fill="url(#vg)">{esc(val)}</text>
{"".join(f'<text class="mono" x="{x + 16:.1f}" y="{y + 28 + fs + 34 + j * 15:.1f}" font-size="10.5" fill="{C["muted"]}">{esc(t)}</text>' for j, t in enumerate(lines))}
</g>''')

    # security posture strip with animated gauges
    sy, sh = TOP + 2, H - TOP - 20
    b.append(f'''<rect x="20" y="{sy}" width="{W - 40}" height="{sh}" rx="12" fill="#ffffff" fill-opacity=".02" stroke="{C["line"]}"/>
<text class="mono" x="38" y="{sy + 26}" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{C["muted"]}">SECURITY POSTURE // {esc(POSTURE_SCOPE)}</text>''')
    iw = (W - 40) / len(POSTURE)
    for i, (score, unit, name, note, col) in enumerate(POSTURE):
        colr = C[col]
        x0 = 20 + i * iw
        gx0, gy0, r = x0 + 58, sy + 74, 30
        b.append(f'''<g class="tile" style="animation-delay:{.3 + i * .15:.2f}s">
<circle cx="{gx0:.1f}" cy="{gy0}" r="{r}" stroke="{C["line"]}" stroke-width="6"/>
<circle cx="{gx0:.1f}" cy="{gy0}" r="{r}" stroke="{colr}" stroke-width="6" stroke-linecap="round" pathLength="100"
 stroke-dasharray="100" stroke-dashoffset="{100 - score}" transform="rotate(-90 {gx0:.1f} {gy0})" filter="url(#glow)">
<animate attributeName="stroke-dashoffset" from="100" to="{100 - score}" dur="2.2s" begin="{.4 + i * .2:.1f}s" fill="freeze"/></circle>
<text class="sans" x="{gx0:.1f}" y="{gy0 + 6}" text-anchor="middle" font-size="18" font-weight="800" fill="{C["text"]}">{score}{esc(unit)}</text>
<text class="sans" x="{gx0 + 50:.1f}" y="{gy0 - 4}" font-size="16" font-weight="800" fill="{C["text"]}">{esc(name)}</text>
<text class="mono" x="{gx0 + 50:.1f}" y="{gy0 + 16}" font-size="10.5" fill="{colr}">{esc(note)}</text></g>''')
        if i:
            b.append(f'<line x1="{x0:.1f}" y1="{sy + 44}" x2="{x0:.1f}" y2="{sy + sh - 14}" stroke="{C["line"]}" stroke-dasharray="2 4"/>')
    return svg(W, H, "\n".join(b), "Impact: career timeline and measured outcomes", style)


# --------------------------------------------------------------------------- footer
def render_footer() -> str:
    W, H = 1000, 214
    cmd = "establish --secure-connection --to prashant.kumar"
    fs, x0, y0 = 15, 34, 48
    step = fs * CW
    cycle = 12.0
    ev = [(0.0, 2 * step)] + [(0.5 + k * 0.045, (k + 3) * step) for k in range(len(cmd))] + [(11.4, 2 * step)]
    vals, keys = discrete(ev, cycle)
    done = 0.5 + len(cmd) * 0.045
    style = f"""
.ok{{animation:ok {cycle}s linear infinite}}
@keyframes ok{{0%,{(done + 1.6) / cycle * 100:.1f}%{{opacity:0}}{(done + 2) / cycle * 100:.1f}%,94%{{opacity:1}}100%{{opacity:0}}}}
.dash{{stroke-dasharray:6 8;animation:dash 1s linear infinite}}
@keyframes dash{{to{{stroke-dashoffset:-14}}}}
"""
    L, Rx, y = 205, 795, 112
    b = [frame(W, H, 16, "green"), f'''<defs><linearGradient id="mg" x1="0" x2="1"><stop offset="0" stop-color="{C["cyan"]}"/>
<stop offset=".5" stop-color="{C["violet"]}"/><stop offset="1" stop-color="{C["pink"]}"/></linearGradient></defs>
<clipPath id="fc"><rect x="{x0 - 4}" y="{y0 - fs - 2}" height="{fs + 10}" width="0">
<animate attributeName="width" calcMode="discrete" dur="{cycle}s" repeatCount="indefinite" values="{vals}" keyTimes="{keys}"/></rect></clipPath>
<text class="mono" x="{x0}" y="{y0}" font-size="{fs}" clip-path="url(#fc)" xml:space="preserve" style="white-space:pre"><tspan fill="{C["green"]}" font-weight="700">❯ </tspan><tspan fill="{C["text"]}">{esc(cmd)}</tspan></text>
<line x1="{L}" y1="{y}" x2="{Rx}" y2="{y}" stroke="{C["cyan"]}" stroke-opacity=".5" stroke-width="2" class="dash"/>
<circle r="4.5" cy="{y}" fill="{C["green"]}" filter="url(#glow)"><animate attributeName="cx" values="{L};{Rx}" dur="2.2s" repeatCount="indefinite"/></circle>
<circle r="4.5" cy="{y}" fill="{C["violet"]}" filter="url(#glow)"><animate attributeName="cx" values="{Rx};{L}" dur="2.2s" begin="1.1s" repeatCount="indefinite"/></circle>
<rect x="{W / 2 - 128}" y="{y - 15}" width="256" height="30" rx="15" fill="{C["bg"]}" stroke="url(#mg)"/>
<text class="mono" x="{W / 2}" y="{y + 4.5}" text-anchor="middle" font-size="11.5" letter-spacing="1" fill="{C["text"]}">🔒 TLS 1.3 · mTLS · ZERO TRUST</text>
<rect x="55" y="{y - 23}" width="150" height="46" rx="10" fill="{C["green"]}" fill-opacity=".07" stroke="{C["green"]}" stroke-opacity=".6"/>
<text class="mono" x="130" y="{y + 5}" text-anchor="middle" font-size="14" font-weight="700" letter-spacing="3" fill="{C["green"]}">YOU</text>
<rect x="{Rx}" y="{y - 23}" width="150" height="46" rx="10" fill="{C["violet"]}" fill-opacity=".08" stroke="{C["violet"]}" stroke-opacity=".7"/>
<text class="mono" x="{Rx + 75}" y="{y + 5}" text-anchor="middle" font-size="14" font-weight="700" letter-spacing="3" fill="{C["violet"]}">PRASHANT</text>
<text class="mono ok" x="{W / 2}" y="{y + 40}" text-anchor="middle" font-size="12" fill="{C["green"]}">✔ handshake complete · channel secured · {esc(EMAIL)}</text>
<text class="sans" x="{W / 2}" y="{H - 26}" text-anchor="middle" font-size="19" font-weight="700" font-style="italic" fill="url(#mg)">{esc(MOTTO)}</text>''']
    return svg(W, H, "\n".join(b), "Establish a secure connection with Prashant", style)


# --------------------------------------------------------------------------- telemetry dashboard
def render_dashboard(s: dict | None) -> str:
    W, H = 1000, 342
    s = s or {}
    fmt = lambda k: f"{s[k]:,}" if isinstance(s.get(k), int) else "—"  # noqa: E731
    tiles = [
        ("CONTRIBUTIONS", fmt("contributions"), "last 12 months", "cyan"),
        ("COMMITS", fmt("commits"), "last 12 months", "green"),
        ("ACTIVE DAYS", fmt("active_days"), "last 12 months", "violet"),
        ("ORGANIZATIONS", fmt("orgs"), "collaborating across", "pink"),
        ("YEARS IN CLOUD", YEARS, "building & securing", "amber"),
    ]
    style = """
.tile{animation:tup .7s ease-out both}
@keyframes tup{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2.6s ease-out .4s forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.area{animation:afade 1.6s ease-out 1.6s both}
@keyframes afade{from{opacity:0}to{opacity:1}}
.scanx{animation:scanx 5s linear infinite}
@keyframes scanx{from{transform:translateX(0)}to{transform:translateX(560px)}}
.grow{transform-box:fill-box;transform-origin:left;animation:grow 1.4s ease-out both}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
"""
    b = [frame(W, H, 16), f'''<defs>
  <linearGradient id="num" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="{C["cyan"]}"/></linearGradient>
  <linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity=".4"/>
    <stop offset="1" stop-color="{C["cyan"]}" stop-opacity="0"/></linearGradient>
  <linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="{C["green"]}"/><stop offset=".5" stop-color="{C["cyan"]}"/>
    <stop offset="1" stop-color="{C["violet"]}"/></linearGradient>
  <linearGradient id="sx" x1="0" x2="1"><stop offset="0" stop-color="{C["cyan"]}" stop-opacity="0"/>
    <stop offset="1" stop-color="{C["cyan"]}" stop-opacity=".25"/></linearGradient>
</defs>
<circle cx="30" cy="31" r="4.5" fill="{C["cyan"]}" class="blink"/>
<text class="mono" x="44" y="36" font-size="13" font-weight="700" letter-spacing="3" fill="{C["text"]}">SOC // GITHUB TELEMETRY</text>
<rect x="{W - 266}" y="19" width="58" height="22" rx="11" fill="{C["green"]}" fill-opacity=".12" stroke="{C["green"]}" stroke-opacity=".6"/>
<circle cx="{W - 252}" cy="30" r="3.5" fill="{C["green"]}" class="blink"/>
<text class="mono" x="{W - 243}" y="34" font-size="10.5" font-weight="700" fill="{C["green"]}">LIVE</text>
<text class="mono" x="{W - 22}" y="34" text-anchor="end" font-size="11" fill="{C["muted"]}">sync {esc(s.get("synced", "pending"))}</text>''']

    tw = (W - 40 - 4 * 12) / 5
    for i, (lab, val, cap, col) in enumerate(tiles):
        x, y = 20 + i * (tw + 12), 56
        colr = C[col]
        b.append(f'''<g class="tile" style="animation-delay:{i * .12:.2f}s">
<rect x="{x:.1f}" y="{y}" width="{tw:.1f}" height="94" rx="12" fill="{colr}" fill-opacity=".05" stroke="{colr}" stroke-opacity=".3"/>
<rect x="{x:.1f}" y="{y + 18}" width="3" height="58" rx="1.5" fill="{colr}" filter="url(#glow)"/>
<text class="mono" x="{x + 18:.1f}" y="{y + 24}" font-size="10" font-weight="700" letter-spacing="1.6" fill="{colr}">{lab}</text>
<text class="sans" x="{x + 16:.1f}" y="{y + 64}" font-size="34" font-weight="800" fill="url(#num)">{esc(val)}</text>
<text class="mono" x="{x + 18:.1f}" y="{y + 82}" font-size="9.5" fill="{C["muted"]}">{esc(cap)}</text></g>''')

    # weekly activity chart
    px, py, pw, ph = 20, 164, 600, 150
    weeks = s.get("weeks") or [0] * 52
    peak = max(weeks) or 1
    cx0, cx1, cy0, cy1 = px + 18, px + pw - 18, py + 42, py + ph - 16
    pts = [(cx0 + (cx1 - cx0) * k / max(1, len(weeks) - 1), cy1 - (cy1 - cy0) * v / peak) for k, v in enumerate(weeks)]
    line = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    area = line + f" L{cx1} {cy1} L{cx0} {cy1} Z"
    pk = max(range(len(weeks)), key=lambda k: weeks[k])
    b.append(f'''<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="12" fill="#ffffff" fill-opacity=".02" stroke="{C["line"]}"/>
<text class="mono" x="{px + 18}" y="{py + 24}" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{C["muted"]}">WEEKLY ACTIVITY // LAST 52 WEEKS</text>
<text class="mono" x="{px + pw - 18}" y="{py + 24}" text-anchor="end" font-size="10.5" fill="{C["cyan"]}">peak {max(weeks)} / week</text>
{"".join(f'<line x1="{cx0}" x2="{cx1}" y1="{cy0 + (cy1 - cy0) * f:.1f}" y2="{cy0 + (cy1 - cy0) * f:.1f}" stroke="{C["line"]}" stroke-dasharray="2 4"/>' for f in (0, .5, 1))}
<path class="area" d="{area}" fill="url(#ar)"/>
<path class="draw" d="{line}" pathLength="1" stroke="url(#ln)" stroke-width="2.4" stroke-linejoin="round" filter="url(#glow)"/>
<circle class="area" cx="{pts[pk][0]:.1f}" cy="{pts[pk][1]:.1f}" r="4" fill="{C["bg"]}" stroke="{C["cyan"]}" stroke-width="2"/>
<rect class="scanx" x="{cx0 - 40}" y="{cy0}" width="40" height="{cy1 - cy0}" fill="url(#sx)"/>''')

    # language mix
    lx, lw = 632, 348
    langs = s.get("langs") or []
    b.append(f'''<rect x="{lx}" y="{py}" width="{lw}" height="{ph}" rx="12" fill="#ffffff" fill-opacity=".02" stroke="{C["line"]}"/>
<text class="mono" x="{lx + 18}" y="{py + 24}" font-size="10.5" font-weight="700" letter-spacing="1.5" fill="{C["muted"]}">LANGUAGE MIX // PUBLIC REPOS</text>
<clipPath id="lb"><rect x="{lx + 18}" y="{py + 40}" width="{lw - 36}" height="10" rx="5"/></clipPath>
<rect x="{lx + 18}" y="{py + 40}" width="{lw - 36}" height="10" rx="5" fill="{C["line"]}"/>''')
    x, segs = lx + 18, []
    for k, (nm, pc, col) in enumerate(langs):
        w = (lw - 36) * pc / 100
        segs.append(f'<rect class="grow" style="animation-delay:{.3 + k * .15:.2f}s" x="{x:.1f}" y="{py + 40}" width="{w:.1f}" height="10" fill="{col}"/>')
        x += w
    b.append(f'<g clip-path="url(#lb)">{"".join(segs)}</g>')
    for k, (nm, pc, col) in enumerate(langs[:4]):
        yy = py + 76 + k * 19
        b.append(f'<circle cx="{lx + 24}" cy="{yy - 4}" r="4.5" fill="{col}"/>'
                 f'<text class="mono" x="{lx + 36}" y="{yy}" font-size="11.5" fill="{C["text"]}">{esc(nm)}</text>'
                 f'<text class="mono" x="{lx + lw - 18}" y="{yy}" text-anchor="end" font-size="11.5" fill="{C["muted"]}">{pc:.1f}%</text>')
    if not langs:
        b.append(f'<text class="mono" x="{lx + 18}" y="{py + 80}" font-size="11.5" fill="{C["muted"]}">awaiting telemetry…</text>')

    since = s.get("since", "")
    b.append(f'<text class="mono" x="20" y="{H - 12}" font-size="10" fill="{C["dim"]}">public repos: {fmt("public_repos")}  ·  '
             f'stars: {fmt("stars")}  ·  on GitHub since {esc(since)}  ·  auto-rendered daily by scripts/render.py via GitHub Actions</text>')
    return svg(W, H, "\n".join(b), "Live GitHub telemetry dashboard", style)


# --------------------------------------------------------------------------- GitHub API
QUERY = """query($login:String!){user(login:$login){createdAt organizations{totalCount}
contributionsCollection{totalCommitContributions restrictedContributionsCount
 contributionCalendar{totalContributions weeks{contributionDays{contributionCount}}}}
repositories(first:100,ownerAffiliations:OWNER,privacy:PUBLIC,isFork:false){totalCount
 nodes{name stargazerCount primaryLanguage{name color}
  languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}}}"""


def get_token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def fetch_stats() -> dict | None:
    token = get_token()
    if not token:
        print("! no GitHub token found; skipping live data", file=sys.stderr)
        return None
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": f"{LOGIN}-profile-renderer"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except Exception as e:  # network/HTTP errors must not break the render
        print(f"! GitHub API error: {e}", file=sys.stderr)
        return None
    if data.get("errors") or not (data.get("data") or {}).get("user"):
        print(f"! GitHub API returned errors: {data.get('errors')}", file=sys.stderr)
        return None

    u = data["data"]["user"]
    cc = u["contributionsCollection"]
    days = [d["contributionCount"] for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cc["contributionCalendar"]["weeks"]][-52:]
    repos = u["repositories"]["nodes"]
    sizes: dict[str, list] = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            sizes.setdefault(n, [0, e["node"]["color"] or C["cyan"]])[0] += e["size"]
    total = sum(v[0] for v in sizes.values()) or 1
    langs = sorted(((n, v[0] * 100 / total, v[1]) for n, v in sizes.items()), key=lambda x: -x[1])
    if len(langs) > 4:
        langs = langs[:3] + [("Other", sum(x[1] for x in langs[3:]), C["dim"])]
    return dict(
        contributions=cc["contributionCalendar"]["totalContributions"],
        commits=cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        active_days=sum(1 for d in days[-365:] if d > 0),
        orgs=max(u["organizations"]["totalCount"], ORGS_FALLBACK),
        public_repos=u["repositories"]["totalCount"],
        stars=sum(r["stargazerCount"] for r in repos),
        weeks=weeks, langs=langs, since=u["createdAt"][:4],
        synced=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        repos={r["name"]: dict(stars=r["stargazerCount"], lang=(r["primaryLanguage"] or {}).get("name"),
                               color=(r["primaryLanguage"] or {}).get("color")) for r in repos},
    )


# --------------------------------------------------------------------------- main
def write(name: str, content: str) -> None:
    (ASSETS / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"  + assets/{name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true", help="skip the GitHub API; keep existing live assets")
    args = ap.parse_args()
    ASSETS.mkdir(exist_ok=True)

    stats = None if args.offline else fetch_stats()
    print("rendering assets" + (" (live data)" if stats else " (offline)"))
    write("header.svg", render_header())
    write("terminal.svg", render_terminal())
    write("devsecops-loop.svg", render_loop())
    write("arsenal.svg", render_arsenal())
    write("footer.svg", render_footer())
    write("impact.svg", render_impact())
    for kind in ("linkedin", "github", "email"):
        write(f"btn-{kind}.svg", render_button(kind))
    for i, (issuer, level, name, _url) in enumerate(CERTS, 1):
        write(f"cert-{i:02d}.svg", render_cert(issuer, level, name))
    for i, (num, title, sub) in enumerate(SECTIONS, 1):
        write(f"section-{i:02d}.svg", render_section(num, title, sub))

    live = (stats or {}).get("repos", {})
    for p in PROJECTS:
        target = ASSETS / f"{p['file']}.svg"
        if stats or not target.exists():
            write(target.name, render_project(p, live))
    if stats or not (ASSETS / "telemetry.svg").exists():
        write("telemetry.svg", render_dashboard(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
