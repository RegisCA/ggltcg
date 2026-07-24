#!/usr/bin/env python3
"""Weekly dependency vulnerability digest for ggltcg.

Snyk's dashboard/REST API is unavailable on this org's plan ("not entitled
for api access"). `snyk test` still works for the frontend (npm resolves
locally from package-lock.json, no org API call needed) but not for the
backend (pip resolution needs the org API). So findings come from two
sources:

  - frontend: `snyk test --json` (npm/yarn ecosystem, local resolution)
  - backend:  OSV.dev batch query against the venv's installed versions
              (free, unauthenticated, PyPI-ecosystem coverage overlaps
              heavily with what Snyk would report)

Usage:
    python3 scripts/snyk/security_digest.py                # print + save digest
    python3 scripts/snyk/security_digest.py --apply         # also open a bot PR
                                                              # for safe findings
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
ENV_FILE = Path(__file__).resolve().parent / ".env"
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def load_env():
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip()
    return env


def snyk_frontend_findings(env):
    proc = subprocess.run(
        ["npx", "--yes", "snyk@latest", "test", f"--org={env['SNYK_ORG_SLUG']}", "--json"],
        cwd=FRONTEND_DIR,
        env={**__import__("os").environ, "SNYK_TOKEN": env["SNYK_TOKEN"]},
        capture_output=True,
        text=True,
    )
    if not proc.stdout.strip():
        raise RuntimeError(f"snyk test produced no output: {proc.stderr[-2000:]}")
    data = json.loads(proc.stdout)
    findings = []
    for v in data.get("vulnerabilities", []):
        findings.append(
            {
                "ecosystem": "npm",
                "package": v["packageName"],
                "installed": v["version"],
                "fixed_in": sorted(v.get("fixedIn", []), key=_version_key),
                "severity": v["severity"],
                "title": v["title"],
                "direct": v.get("from", [None])[0] == v["packageName"] or len(v.get("from", [])) <= 2,
                "ids": v.get("identifiers", {}).get("CVE", []) or [v.get("id", "")],
            }
        )
    return findings


def backend_installed_versions():
    proc = subprocess.run(
        ["uv", "pip", "list", "--python", str(VENV_PYTHON), "--format=freeze"],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    versions = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if "==" not in line:
            continue
        name, version = line.split("==")
        versions[name.lower()] = version
    return versions


def osv_query(versions):
    queries = [
        {"package": {"name": name, "ecosystem": "PyPI"}, "version": version}
        for name, version in versions.items()
    ]
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=json.dumps({"queries": queries}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    hits = {}
    for (name, version), r in zip(versions.items(), result["results"]):
        vuln_ids = [v["id"] for v in r.get("vulns", [])]
        if vuln_ids:
            hits[name] = (version, vuln_ids)
    return hits


def osv_details(vuln_ids):
    details = {}
    for vid in vuln_ids:
        with urllib.request.urlopen(f"https://api.osv.dev/v1/vulns/{vid}", timeout=20) as resp:
            details[vid] = json.load(resp)
    return details


def backend_findings():
    versions = backend_installed_versions()
    hits = osv_query(versions)
    all_ids = sorted({vid for _, ids in hits.values() for vid in ids})
    details = osv_details(all_ids)

    findings = []
    for name, (installed, vuln_ids) in hits.items():
        fixed = set()
        cves = set()
        summaries = []
        for vid in vuln_ids:
            d = details[vid]
            cves.update(a for a in d.get("aliases", []) if a.startswith("CVE-"))
            summaries.append(d.get("summary", "")[:100])
            for aff in d.get("affected", []):
                if aff.get("package", {}).get("name", "").lower() != name:
                    continue
                for rng in aff.get("ranges", []):
                    for ev in rng.get("events", []):
                        if "fixed" in ev:
                            fixed.add(ev["fixed"])
        findings.append(
            {
                "ecosystem": "pip",
                "package": name,
                "installed": installed,
                "fixed_in": sorted(fixed, key=_version_key),
                "severity": None,
                "title": "; ".join(dict.fromkeys(summaries)),
                "direct": True,
                "ids": sorted(cves),
            }
        )
    return findings


def _version_key(v):
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"[.\-]", v))


def requirements_pin(name):
    text = (BACKEND_DIR / "requirements.txt").read_text()
    for line in text.splitlines():
        m = re.match(rf"^{re.escape(name)}\s*(==|>=)\s*([\w.]+)", line, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
    return None, None


def classify(f):
    """'safe': single patch/minor bump, no major version jump. 'review': everything else."""
    if not f["fixed_in"]:
        return "review", "no fix published yet"
    target = f["fixed_in"][-1]
    try:
        installed_major = _version_key(f["installed"])[0]
        target_major = _version_key(target)[0]
    except (IndexError, TypeError):
        return "review", "could not compare versions"
    if installed_major != target_major:
        return "review", f"major version bump {f['installed']} -> {target} needs manual review"
    return "safe", f"upgrade {f['package']} to {target}"


def render_markdown(findings):
    lines = [f"# Security digest — {len(findings)} findings\n"]
    safe = [f for f in findings if f["_classification"] == "safe"]
    review = [f for f in findings if f["_classification"] == "review"]

    lines.append(f"**{len(safe)} safe to auto-fix**, **{len(review)} need manual review**.\n")

    for label, group in (("Safe auto-fixes", safe), ("Needs manual review", review)):
        if not group:
            continue
        lines.append(f"## {label}\n")
        for f in group:
            cve = ", ".join(f["ids"]) or "no CVE"
            fixed = f["fixed_in"][-1] if f["fixed_in"] else "none"
            lines.append(
                f"- **{f['package']}** ({f['ecosystem']}) {f['installed']} -> {fixed} "
                f"— {f['severity'] or ''} {cve}\n  {f['title']}"
            )
        lines.append("")
    return "\n".join(lines)


def apply_safe_fix(f):
    """Returns True if a file was edited for this finding."""
    if f["ecosystem"] == "pip":
        op, current = requirements_pin(f["package"])
        target = f["fixed_in"][-1]
        path = BACKEND_DIR / "requirements.txt"
        text = path.read_text()
        if op:
            new_line_prefix = f"{f['package']}{op}{target}"
            text = re.sub(
                rf"^{re.escape(f['package'])}\s*{op}\s*[\w.]+",
                new_line_prefix,
                text,
                count=1,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        else:
            cve_note = ", ".join(f["ids"]) or "advisory"
            text += f"{f['package']}>={target}  # not directly required, minimum safe version to avoid {cve_note}\n"
        path.write_text(text)
        return True
    if f["ecosystem"] == "npm":
        path = FRONTEND_DIR / "package.json"
        pkg = json.loads(path.read_text())
        target = f["fixed_in"][-1]
        if f["package"] in pkg.get("dependencies", {}):
            pkg["dependencies"][f["package"]] = f"^{target}"
        else:
            pkg.setdefault("overrides", {})[f["package"]] = f"^{target}"
        path.write_text(json.dumps(pkg, indent=2) + "\n")
        return True
    return False


def run(cmd, cwd, **kwargs):
    print(f"$ {' '.join(cmd)}  (in {cwd})")
    return subprocess.run(cmd, cwd=cwd, check=True, **kwargs)


def apply_and_open_pr(safe_findings, env):
    if not safe_findings:
        print("No safe findings to apply.")
        return

    branch = f"fix/snyk-weekly-{__import__('datetime').date.today().isoformat()}"
    run(["git", "checkout", "-b", branch], cwd=REPO_ROOT)

    for f in safe_findings:
        apply_safe_fix(f)

    if any(f["ecosystem"] == "pip" for f in safe_findings):
        run(["uv", "pip", "install", "-r", "backend/requirements.txt", "--python", str(VENV_PYTHON)], cwd=REPO_ROOT)
    if any(f["ecosystem"] == "npm" for f in safe_findings):
        run(["npm", "install"], cwd=FRONTEND_DIR)

    try:
        if any(f["ecosystem"] == "pip" for f in safe_findings):
            run(["python", "-m", "pytest", "-q"], cwd=BACKEND_DIR,
                env={**__import__("os").environ, "GOOGLE_API_KEY": "dummy-test-key",
                     "PATH": f"{REPO_ROOT}/.venv/bin:{__import__('os').environ['PATH']}"})
        if any(f["ecosystem"] == "npm" for f in safe_findings):
            run(["npm", "run", "build"], cwd=FRONTEND_DIR)
            run(["npm", "run", "test"], cwd=FRONTEND_DIR)
    except subprocess.CalledProcessError:
        print("Tests failed after applying fixes — aborting, not pushing.")
        run(["git", "checkout", "main"], cwd=REPO_ROOT)
        run(["git", "branch", "-D", branch], cwd=REPO_ROOT)
        return

    run(["git", "add", "-A"], cwd=REPO_ROOT)
    summary = "\n".join(f"- {f['package']} {f['installed']} -> {f['fixed_in'][-1]}" for f in safe_findings)
    run(["git", "commit", "-m", f"fix: weekly Snyk/OSV dependency bumps\n\n{summary}"], cwd=REPO_ROOT)
    run(["gh", "auth", "switch", "-u", "regisca-bot"], cwd=REPO_ROOT)
    run(["git", "push", "-u", "origin", branch], cwd=REPO_ROOT)
    run(
        [
            "gh", "pr", "create",
            "--title", "fix: weekly Snyk/OSV dependency bumps",
            "--base", "main", "--head", branch,
            "--body", f"Automated weekly digest found these safe single-version bumps:\n\n{summary}\n\nTests passed locally before push. Review before merging.",
        ],
        cwd=REPO_ROOT,
    )
    run(["gh", "auth", "switch", "-u", "RegisCA"], cwd=REPO_ROOT)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Open a bot PR for safe findings")
    args = parser.parse_args()

    env = load_env()
    findings = snyk_frontend_findings(env) + backend_findings()
    for f in findings:
        f["_classification"], f["_reason"] = classify(f)

    report = render_markdown(findings)
    print(report)

    REPORTS_DIR.mkdir(exist_ok=True)
    import datetime
    out_path = REPORTS_DIR / f"{datetime.date.today().isoformat()}.md"
    out_path.write_text(report)
    print(f"\nSaved to {out_path}")

    if args.apply:
        safe = [f for f in findings if f["_classification"] == "safe"]
        apply_and_open_pr(safe, env)


if __name__ == "__main__":
    sys.exit(main())
