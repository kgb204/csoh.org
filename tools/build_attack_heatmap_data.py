#!/usr/bin/env python3
"""Regenerate data/chains/*.json + data/chains-index.json from breaches/*.html.

Run this whenever a breach kill chain page is added or its MITRE ATT&CK tags
change - the attack-heatmap.html page has no other source of truth. It is not
wired into any CI workflow (unlike sync_chrome.py / sync_counts.py); run it by
hand as part of adding a kill chain, alongside the other CONTRIBUTING_KILL_CHAINS.md
registration steps.

Extraction is intentionally conservative: it only reads the `<a class="mt ...">`
technique tags a breach page already carries (added by whoever wrote that page,
per CONTRIBUTING_KILL_CHAINS.md's "How to find the MITRE ATT&CK technique"
section) and the technique-to-tactic mapping in TECH_MAP below. It never invents
a technique for a step that has none - those are logged to
ATTACK_HEATMAP_REVIEW.md instead, since on inspection they are narrative /
discovery / response steps (how a breach was found, what the vendor did
afterward), not attacker actions, and forcing an ATT&CK label onto them would
be a guess dressed up as data. See that file for the current list.

A technique valid under more than one ATT&CK tactic (e.g. T1078 Valid Accounts)
is disambiguated using the breach page's own phase-lbl for that step (PHASE_TACTIC
below) when the phase names one of the technique's real tactics; otherwise it
falls back to the technique's primary tactic and is marked "inferred": true so
the heatmap UI can flag it for review rather than presenting it as certain.
"""
import re
import os
import json
import glob
import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BREACH_DIR = REPO / "breaches"
OUT_DIR = REPO / "data" / "chains"
INDEX_OUT = REPO / "data" / "chains-index.json"
REVIEW_OUT = REPO / "ATTACK_HEATMAP_REVIEW.md"

PHASE_RE = re.compile(r'<div class="phase-lbl (ph-[\w]+)">(.*?)</div>', re.S)
STEP_NUM_RE = re.compile(r'<div class="step-num">(.*?)</div>', re.S)
STEP_TITLE_RE = re.compile(r'<div class="step-title">(.*?)</div>', re.S)
MT_RE = re.compile(
    r'<a class="mt (mt-\w+)" href="(https://attack\.mitre\.org/techniques/([^"/]+(?:/\d+)?)/?)"[^>]*>(.*?)</a>',
    re.S,
)
INC_TITLE_RE = re.compile(r'<h2 class="inc-title">(.*?)</h2>', re.S)
INC_YEAR_RE = re.compile(r'<span class="inc-year">(.*?)</span>', re.S)
SEV_RE = re.compile(r'<span class="sev-badge sev-(\w+)">', re.S)
PROV_RE = re.compile(r'<span class="prov-tag prov-(\w+)">(.*?)</span>', re.S)

# phase-lbl class (the page's own kill-chain narrative stage) -> candidate ATT&CK
# tactic. This is a disambiguation aid for techniques valid under more than one
# tactic, not a substitute for the technique's real MITRE tactic set.
PHASE_TACTIC = {
    "ph-recon": "Reconnaissance",
    "ph-init": "Initial Access",
    "ph-exec": "Execution",
    "ph-cred": "Credential Access",
    "ph-priv": "Privilege Escalation",
    "ph-persist": "Persistence",
    "ph-exfil": "Exfiltration",
    "ph-impact": "Impact",
    "ph-disco": "Discovery",  # only for steps that DO carry a technique tag
    "ph-de": "Defense Evasion",
}

# Technique ID (sub-technique where the page tags one specifically) -> (display
# name, [valid ATT&CK tactics, primary first]). Compiled from MITRE ATT&CK
# Enterprise; the techniques added or revised in ATT&CK v19 (Apr 2026) were
# cross-checked against current sources rather than assumed from memory:
# T1656, T1657, T1651, T1677, T1684.001, T1685, T1580, T1621, T1611, T1598,
# T1588.007.
TECH_MAP = {
    "T1001.002": ("Data Obfuscation: Steganography", ["Command and Control"]),
    "T1021": ("Remote Services", ["Lateral Movement"]),
    "T1021.001": ("Remote Services: Remote Desktop Protocol", ["Lateral Movement"]),
    "T1027": ("Obfuscated Files or Information", ["Defense Evasion"]),
    "T1030": ("Data Transfer Size Limits", ["Exfiltration"]),
    "T1036": ("Masquerading", ["Defense Evasion"]),
    "T1036.005": ("Masquerading: Match Legitimate Name or Location", ["Defense Evasion"]),
    "T1041": ("Exfiltration Over C2 Channel", ["Exfiltration"]),
    "T1046": ("Network Service Discovery", ["Discovery"]),
    "T1053": ("Scheduled Task/Job", ["Execution", "Persistence", "Privilege Escalation"]),
    "T1056.001": ("Input Capture: Keylogging", ["Collection"]),
    "T1059": ("Command and Scripting Interpreter", ["Execution"]),
    "T1059.004": ("Command and Scripting Interpreter: Unix Shell", ["Execution"]),
    "T1059.007": ("Command and Scripting Interpreter: JavaScript", ["Execution"]),
    "T1070": ("Indicator Removal", ["Defense Evasion"]),
    "T1071.001": ("Application Layer Protocol: Web Protocols", ["Command and Control"]),
    "T1071.004": ("Application Layer Protocol: DNS", ["Command and Control"]),
    "T1072": ("Software Deployment Tools", ["Execution"]),
    "T1078": ("Valid Accounts", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"]),
    "T1078.002": ("Valid Accounts: Domain Accounts", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"]),
    "T1078.004": ("Valid Accounts: Cloud Accounts", ["Initial Access", "Persistence", "Privilege Escalation", "Defense Evasion"]),
    "T1082": ("System Information Discovery", ["Discovery"]),
    "T1087.004": ("Account Discovery: Cloud Account", ["Discovery"]),
    "T1090.002": ("Proxy: External Proxy", ["Command and Control"]),
    "T1098": ("Account Manipulation", ["Persistence", "Privilege Escalation"]),
    "T1098.002": ("Account Manipulation: Additional Email Delegate Permissions", ["Persistence"]),
    "T1098.005": ("Account Manipulation: Device Registration", ["Persistence"]),
    "T1102": ("Web Service", ["Command and Control"]),
    "T1105": ("Ingress Tool Transfer", ["Command and Control"]),
    "T1110.003": ("Brute Force: Password Spraying", ["Credential Access"]),
    "T1111": ("Multi-Factor Authentication Interception", ["Credential Access"]),
    "T1114.002": ("Email Collection: Remote Email Collection", ["Collection"]),
    "T1125": ("Video Capture", ["Collection"]),
    "T1133": ("External Remote Services", ["Initial Access", "Persistence"]),
    "T1190": ("Exploit Public-Facing Application", ["Initial Access"]),
    "T1195": ("Supply Chain Compromise", ["Initial Access"]),
    "T1195.001": ("Supply Chain Compromise: Compromise Software Dependencies and Development Tools", ["Initial Access"]),
    "T1195.002": ("Supply Chain Compromise: Compromise Software Supply Chain", ["Initial Access"]),
    "T1199": ("Trusted Relationship", ["Initial Access"]),
    "T1203": ("Exploitation for Client Execution", ["Execution"]),
    "T1204.001": ("User Execution: Malicious Link", ["Execution"]),
    "T1204.002": ("User Execution: Malicious File", ["Execution"]),
    "T1211": ("Exploitation for Defense Evasion", ["Defense Evasion"]),
    "T1212": ("Exploitation for Credential Access", ["Credential Access"]),
    "T1213": ("Data from Information Repositories", ["Collection"]),
    "T1213.002": ("Data from Information Repositories: Sharepoint", ["Collection"]),
    "T1485": ("Data Destruction", ["Impact"]),
    "T1486": ("Data Encrypted for Impact", ["Impact"]),
    "T1490": ("Inhibit System Recovery", ["Impact"]),
    "T1496": ("Resource Hijacking", ["Impact"]),
    "T1497": ("Virtualization/Sandbox Evasion", ["Defense Evasion", "Discovery"]),
    "T1505.003": ("Server Software Component: Web Shell", ["Persistence"]),
    "T1528": ("Steal Application Access Token", ["Credential Access"]),
    "T1530": ("Data from Cloud Storage", ["Collection"]),
    "T1534": ("Internal Spearphishing", ["Lateral Movement"]),
    "T1539": ("Steal Web Session Cookie", ["Credential Access"]),
    "T1543": ("Create or Modify System Process", ["Persistence", "Privilege Escalation"]),
    "T1543.001": ("Create or Modify System Process: Launch Agent", ["Persistence", "Privilege Escalation"]),
    "T1543.002": ("Create or Modify System Process: Systemd Service", ["Persistence", "Privilege Escalation"]),
    "T1546": ("Event Triggered Execution", ["Persistence", "Privilege Escalation"]),
    "T1548": ("Abuse Elevation Control Mechanism", ["Privilege Escalation", "Defense Evasion"]),
    "T1550": ("Use Alternate Authentication Material", ["Defense Evasion", "Lateral Movement"]),
    "T1550.001": ("Use Alternate Authentication Material: Application Access Token", ["Defense Evasion", "Lateral Movement"]),
    "T1550.004": ("Use Alternate Authentication Material: Web Session Cookie", ["Defense Evasion", "Lateral Movement"]),
    "T1552": ("Unsecured Credentials", ["Credential Access"]),
    "T1552.001": ("Unsecured Credentials: Credentials In Files", ["Credential Access"]),
    "T1552.004": ("Unsecured Credentials: Private Keys", ["Credential Access"]),
    "T1552.005": ("Unsecured Credentials: Cloud Instance Metadata API", ["Credential Access"]),
    "T1552.007": ("Unsecured Credentials: Container API", ["Credential Access"]),
    "T1553.002": ("Subvert Trust Controls: Code Signing", ["Defense Evasion"]),
    "T1554": ("Compromise Host Software Binary", ["Persistence"]),
    "T1555": ("Credentials from Password Stores", ["Credential Access"]),
    "T1555.003": ("Credentials from Password Stores: Credentials from Web Browsers", ["Credential Access"]),
    "T1556.006": ("Modify Authentication Process: Multi-Factor Authentication", ["Credential Access", "Defense Evasion", "Persistence", "Privilege Escalation"]),
    "T1560.001": ("Archive Collected Data: Archive via Utility", ["Collection"]),
    "T1562.001": ("Impair Defenses: Disable or Modify Tools", ["Defense Evasion"]),
    "T1562.007": ("Impair Defenses: Disable or Modify Cloud Firewall", ["Defense Evasion"]),
    "T1562.008": ("Impair Defenses: Disable or Modify Cloud Logs", ["Defense Evasion"]),
    "T1566": ("Phishing", ["Initial Access"]),
    "T1566.002": ("Phishing: Spearphishing Link", ["Initial Access"]),
    "T1566.003": ("Phishing: Spearphishing via Service", ["Initial Access"]),
    "T1566.004": ("Phishing: Spearphishing Voice", ["Initial Access"]),
    "T1567.001": ("Exfiltration Over Web Service: Exfiltration to Code Repository", ["Exfiltration"]),
    "T1574": ("Hijack Execution Flow", ["Persistence", "Privilege Escalation", "Defense Evasion"]),
    "T1578": ("Modify Cloud Compute Infrastructure", ["Defense Evasion"]),
    "T1578.002": ("Modify Cloud Compute Infrastructure: Create Cloud Instance", ["Defense Evasion"]),
    "T1580": ("Cloud Infrastructure Discovery", ["Discovery"]),
    "T1583.001": ("Acquire Infrastructure: Domains", ["Resource Development"]),
    "T1585": ("Establish Accounts", ["Resource Development"]),
    "T1586": ("Compromise Accounts", ["Resource Development"]),
    "T1587.001": ("Develop Capabilities: Malware", ["Resource Development"]),
    "T1588.005": ("Obtain Capabilities: Exploits", ["Resource Development"]),
    "T1588.006": ("Obtain Capabilities: Vulnerabilities", ["Resource Development"]),
    "T1588.007": ("Obtain Capabilities: Artificial Intelligence", ["Resource Development"]),
    "T1589": ("Gather Victim Identity Information", ["Reconnaissance"]),
    "T1589.001": ("Gather Victim Identity Information: Credentials", ["Reconnaissance"]),
    "T1589.002": ("Gather Victim Identity Information: Email Addresses", ["Reconnaissance"]),
    "T1590": ("Gather Victim Network Information", ["Reconnaissance"]),
    "T1591": ("Gather Victim Org Information", ["Reconnaissance"]),
    "T1593": ("Search Open Websites/Domains", ["Reconnaissance"]),
    "T1594": ("Search Victim-Owned Websites", ["Reconnaissance"]),
    "T1595": ("Active Scanning", ["Reconnaissance"]),
    "T1595.002": ("Active Scanning: Vulnerability Scanning", ["Reconnaissance"]),
    "T1598": ("Phishing for Information", ["Reconnaissance"]),
    "T1606": ("Forge Web Credentials", ["Credential Access"]),
    "T1606.001": ("Forge Web Credentials: Web Cookies", ["Credential Access"]),
    "T1606.002": ("Forge Web Credentials: SAML Tokens", ["Credential Access"]),
    "T1611": ("Escape to Host", ["Privilege Escalation"]),
    "T1613": ("Container and Resource Discovery", ["Discovery"]),
    "T1619": ("Cloud Storage Object Discovery", ["Discovery"]),
    "T1621": ("Multi-Factor Authentication Request Generation", ["Credential Access"]),
    "T1651": ("Cloud Administration Command", ["Execution"]),
    "T1656": ("Impersonation", ["Defense Evasion"]),
    "T1657": ("Financial Theft", ["Impact"]),
    "T1677": ("Poisoned Pipeline Execution", ["Execution"]),
    "T1684.001": ("Social Engineering: Impersonation", ["Defense Evasion"]),
    "T1685": ("Disable or Modify Tools", ["Defense Evasion"]),
}


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&rarr;", "->").replace("&#39;", "'").replace("&quot;", '"')
    return re.sub(r"\s+", " ", s).strip()


def base_id(href: str):
    m = re.search(r"techniques/(T\d+)(?:/(\d+))?/?$", href)
    if not m:
        return None
    base, sub = m.groups()
    return base + ("." + sub if sub else "")


def short_chain_name(inc_title: str, slug: str) -> str:
    if not inc_title:
        return slug
    for sep in (" - ", " – ", " — "):
        if sep in inc_title:
            return inc_title.split(sep, 1)[0].strip()
    return inc_title


def parse_breach_page(html: str):
    kc_match = re.search(r'<div class="kill-chain">(.*?)<div class="def-box">', html, re.S)
    if not kc_match:
        return None
    kc_html = kc_match.group(1)

    step_starts = [m.start() for m in re.finditer(r'<div class="kc-step step-\w">', kc_html)]
    phase_starts = [(m.start(), m.group(1)) for m in re.finditer(PHASE_RE, kc_html)]

    def phase_for_pos(pos):
        cur = None
        for ps, cls in phase_starts:
            if ps <= pos:
                cur = cls
            else:
                break
        return cur

    boundaries = sorted(step_starts + [p[0] for p in phase_starts] + [len(kc_html)])

    steps = []
    for s in step_starts:
        end = next((b for b in boundaries if b > s), len(kc_html))
        block = kc_html[s:end]
        num_m = STEP_NUM_RE.search(block)
        title_m = STEP_TITLE_RE.search(block)
        techs = [
            {"mt_class": mt_class, "href": href, "label": strip_tags(label)}
            for mt_class, href, _tid_raw, label in MT_RE.findall(block)
        ]
        steps.append({
            "step_num": strip_tags(num_m.group(1)) if num_m else None,
            "phase_class": phase_for_pos(s),
            "step_title": strip_tags(title_m.group(1)) if title_m else None,
            "techniques": techs,
        })

    inc_title_m = INC_TITLE_RE.search(html)
    inc_year_m = INC_YEAR_RE.search(html)
    sev_m = SEV_RE.search(html)
    prov_m = PROV_RE.search(html)
    return {
        "inc_title": strip_tags(inc_title_m.group(1)) if inc_title_m else None,
        "inc_year": strip_tags(inc_year_m.group(1)) if inc_year_m else None,
        "severity": sev_m.group(1) if sev_m else None,
        "provider": strip_tags(prov_m.group(2)) if prov_m else None,
        "steps": steps,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    review_lines = []
    unmapped_ids = set()
    index_entries = []
    total_tags = 0
    total_inferred = 0

    for path in sorted(glob.glob(str(BREACH_DIR / "*.html"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        html = Path(path).read_text(encoding="utf-8")
        parsed = parse_breach_page(html)
        if parsed is None:
            print(f"WARNING: {slug} has no kill-chain block, skipped")
            continue

        chain_name = short_chain_name(parsed["inc_title"], slug)
        seen = set()
        techniques = []
        excluded_steps = []

        for step in parsed["steps"]:
            if not step["techniques"]:
                excluded_steps.append(step)
                continue
            phase_tactic = PHASE_TACTIC.get(step["phase_class"])
            for t in step["techniques"]:
                tid = base_id(t["href"])
                if tid is None:
                    continue
                entry = TECH_MAP.get(tid)
                if entry is None:
                    unmapped_ids.add(tid)
                    continue
                display_name, valid_tactics = entry

                if phase_tactic in valid_tactics:
                    tactic, inferred = phase_tactic, False
                elif len(valid_tactics) == 1:
                    tactic, inferred = valid_tactics[0], False
                else:
                    tactic, inferred = valid_tactics[0], True

                total_tags += 1
                if inferred:
                    total_inferred += 1
                key = (tid, tactic)
                if key in seen:
                    continue
                seen.add(key)
                techniques.append({"id": tid, "name": display_name, "tactic": tactic, "inferred": inferred})

        if excluded_steps:
            review_lines.append(f"### {chain_name} (`{slug}`)")
            for s in excluded_steps:
                review_lines.append(
                    f"- Step {s['step_num']} [{s['phase_class']}]: \"{s['step_title']}\" "
                    f"- no ATT&CK technique tagged on the page; excluded as a narrative/"
                    f"discovery/response step, not an attacker action. Review if this should map to something."
                )
            review_lines.append("")

        chain_doc = {
            "id": slug,
            "name": chain_name,
            "title": parsed["inc_title"],
            "url": f"/breaches/{slug}.html",
            "year": parsed["inc_year"],
            "severity": parsed["severity"],
            "provider": parsed["provider"],
            "techniques": techniques,
        }
        (OUT_DIR / f"{slug}.json").write_text(json.dumps(chain_doc, indent=2) + "\n", encoding="utf-8")
        index_entries.append({"id": slug, "file": f"{slug}.json", "name": chain_name, "url": f"/breaches/{slug}.html"})

    index_entries.sort(key=lambda e: e["id"])
    index_doc = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(index_entries),
        "chains": index_entries,
    }
    INDEX_OUT.write_text(json.dumps(index_doc, indent=2) + "\n", encoding="utf-8")

    with open(REVIEW_OUT, "w", encoding="utf-8") as f:
        f.write("# ATT&CK heatmap data extraction - review notes\n\n")
        f.write("Generated by `tools/build_attack_heatmap_data.py`. Not published (see site-publish.filter).\n\n")
        f.write(f"Chains processed: {len(index_entries)}\n")
        f.write(f"Technique tag instances extracted: {total_tags}\n")
        f.write(
            f"Inferred tactic assignments (multi-tactic technique, phase context didn't "
            f"disambiguate - used MITRE's primary tactic, please review): {total_inferred}\n"
        )
        f.write(f"Unmapped technique IDs (not in TECH_MAP, excluded entirely - add them there): {sorted(unmapped_ids)}\n\n")
        f.write("## Steps with no ATT&CK technique tag on the page (excluded - not attacker actions)\n\n")
        f.write("\n".join(review_lines))

    print(f"Wrote {len(index_entries)} chain files + index to {OUT_DIR}")
    print(f"Technique tag instances: {total_tags}, inferred: {total_inferred}, unmapped: {sorted(unmapped_ids)}")
    if unmapped_ids:
        raise SystemExit(f"{len(unmapped_ids)} technique id(s) have no TECH_MAP entry - add them and re-run")


if __name__ == "__main__":
    main()
