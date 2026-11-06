"""Run all aspects against a repo and build the report dict; apply the capability list (profile) and an optional review."""

from __future__ import annotations

import platform
import sys
import time
from datetime import UTC, datetime

from . import __version__
from .acceptance import method_for
from .checklist import CRITICAL_CAP, PRIORITY_WEIGHT, priority_from_weight
from .dimensions import DIMENSIONS
from .model import band, grade
from .profiles import resolve as resolve_checklist
from .repo import Repo

REVIEW_SCORES = {"met": 1.0, "partial": 0.5, "unmet": 0.0, "na": None}


def status_of(score: float | None, pending: bool = False) -> str:
    if pending:
        return "review"
    if score is None:
        return "na"
    return "pass" if score >= 0.85 else "partial" if score >= 0.35 else "fail"


def scan(repo: Repo, only: list[str] | None = None, checklist: dict | None = None) -> dict:
    t0 = time.perf_counter()
    checklist = checklist or resolve_checklist(repo.root)
    repo.params = checklist.get("params") or {}
    dims = []
    for d in DIMENSIONS:
        if only and d.id not in only:
            continue
        t = time.perf_counter()
        try:
            res = d.run(repo).to_dict()
        except Exception as e:  # one broken heuristic must not sink the whole assessment
            res = {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "score": None,
                "grade": "N/A",
                "checks": [
                    {
                        "id": f"{d.id}.error",
                        "title": "Assessment error",
                        "weight": 0,
                        "score": None,
                        "status": "na",
                        "evidence": [f"{type(e).__name__}: {e}"],
                        "recommendation": "",
                    }
                ],
            }
        res["elapsed_s"] = round(time.perf_counter() - t, 3)
        res["auto_checks"] = res.pop("checks")
        dims.append(res)
    report = {
        "schema": "sdlc360/report@2",
        "tool": {"name": "sdlc360", "version": __version__, "python": sys.version.split()[0], "platform": platform.platform()},
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "repo": {
            "source": repo.source,
            "head": repo.head,
            "commits": repo.commit_count,
            "files": len(repo.files),
            "source_files": len(repo.source_files),
            "test_files": len(repo.test_files),
            "languages": dict(list(repo.languages.items())[:8]),
        },
        "checklist": checklist,
        "scan_params": repo.params,  # thresholds the scanner rules used; a profile change needs a re-scan to alter them
        "dimensions": dims,
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    return finalize(report)


def _weighted(checks: list[dict]) -> float | None:
    scored = [c for c in checks if c["score"] is not None and c["weight"] > 0]
    total = sum(c["weight"] for c in scored)
    return round(100 * sum(c["weight"] * c["score"] for c in scored) / total, 1) if total else None


def apply_checklist(dim: dict, items: list[dict] | None, verdicts: dict, params: dict | None = None) -> list[dict]:
    raw = {c["id"]: c for c in dim.get("auto_checks", [])}
    if not items:  # dimension not in checklist: keep the scanner's own checks, derive a priority from their weight
        out = []
        for c in raw.values():
            prio = priority_from_weight(c["weight"])
            out.append(dict(c, priority=prio, weight=PRIORITY_WEIGHT[prio], source="auto", method=method_for(c["id"], (params or {}).get(c["id"]))))
        return out
    out = []
    for it in items:
        if it["custom"]:
            v = verdicts.get(it["id"], {})
            st = str(v.get("status", "")).lower()
            score = REVIEW_SCORES.get(st) if st in REVIEW_SCORES else None
            out.append(
                {
                    "id": it["id"],
                    "title": it["text"],
                    "priority": it["priority"],
                    "weight": it["weight"],
                    "score": score,
                    "status": status_of(score, pending=st not in REVIEW_SCORES),
                    "evidence": [v["note"]] if v.get("note") else [],
                    "recommendation": v.get("recommendation", ""),
                    "source": "review",
                    "method": {
                        "looks_at": "Your own capability, judged by a reviewer (person or agent) who records the verdict in review.json.",
                        "met_when": it.get("met_when") or v.get("criteria") or "The reviewer records a verdict with evidence.",
                    },
                }
            )
        elif it["id"] in raw:
            c = raw[it["id"]]
            out.append(
                dict(
                    c,
                    title=it["text"],
                    priority=it["priority"],
                    weight=it["weight"],
                    status=status_of(c["score"]),
                    source="auto",
                    method=method_for(c["id"], (params or {}).get(c["id"])),
                )
            )
    return out


def critical_cap(checks: list[dict]) -> tuple[float | None, list[str]]:
    """The `critical` gate: lowest cap imposed by unmet / partially met critical capabilities."""
    caps = [(CRITICAL_CAP[c["status"]], c["id"]) for c in checks if c.get("priority") == "critical" and c["status"] in CRITICAL_CAP]
    if not caps:
        return None, []
    cap = min(v for v, _ in caps)
    return cap, [cid for v, cid in caps]


def finalize(report: dict, review: dict | None = None) -> dict:
    """(Re)compute checks and scores from raw scanner output + checklist + review. Idempotent."""
    review = review or report.get("review") or {}
    rdims = review.get("dimensions", {}) if isinstance(review, dict) else {}
    verdicts = (review.get("capabilities") or review.get("expectations") or {}) if isinstance(review, dict) else {}  # key before 0.4
    items = (report.get("checklist") or {}).get("items", {})
    wanted, used = (report.get("checklist") or {}).get("params") or {}, report.get("scan_params") or {}
    report["thresholds_changed"] = sorted(  # take effect at the next scan; keys of older versions are not compared
        cid for cid in wanted if any(k in used.get(cid, {}) and used[cid][k] != v for k, v in wanted[cid].items())
    )
    for d in report["dimensions"]:
        if "auto_checks" not in d:  # report@1 compatibility
            d["auto_checks"] = d.pop("checks")
        d["checks"] = apply_checklist(d, items.get(d["id"]), verdicts, report.get("scan_params"))
        auto = _weighted([c for c in d["checks"] if c["source"] == "auto"])
        base = _weighted(d["checks"])
        r = rdims.get(d["id"], {})
        adj = max(-20.0, min(20.0, float(r.get("adjust", 0) or 0)))
        d["auto_score"], d["adjust"], d["review_notes"] = auto, adj, list(r.get("notes", []))
        cap, gated_by = critical_cap(d["checks"])
        raw_score = None if base is None else max(0.0, min(100.0, base + adj))
        d["uncapped_score"] = None if raw_score is None else round(raw_score, 1)
        d["capped_by"] = gated_by if (cap is not None and raw_score is not None and raw_score > cap) else []
        d["score"] = None if raw_score is None else round(min(raw_score, cap) if cap is not None else raw_score, 1)
        d["grade"], d["band"] = grade(d["score"]), band(d["score"])
    scored = [d["score"] for d in report["dimensions"] if d["score"] is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else None
    report["overall"] = {"score": overall, "grade": grade(overall), "band": band(overall), "dimensions_scored": len(scored)}
    if review:
        report["review"] = review
    report["top_actions"] = top_actions(report)
    return report


def top_actions(report: dict, n: int = 10) -> list[dict]:
    """Rank unmet capabilities by recoverable points weighted by how weak their dimension is."""
    acts = []
    for d in report["dimensions"]:
        checks = [c for c in d["checks"] if c["score"] is not None]
        total_w = sum(c["weight"] for c in checks) or 1
        for c in checks:
            if c["status"] == "pass" or not c.get("recommendation"):
                continue
            gain = 100 * c["weight"] * (1 - c["score"]) / total_w
            weakness = 1 + (100 - (d["score"] or 0)) / 100
            acts.append(
                {
                    "dimension": d["name"],
                    "dimension_id": d["id"],
                    "check": c["title"],
                    "check_id": c["id"],
                    "gain": round(gain, 1),
                    "priority": round(gain * weakness, 1),
                    "recommendation": c["recommendation"],
                    "status": c["status"],
                }
            )
    acts.sort(key=lambda a: -a["priority"])
    acts.sort(key=lambda a: 0 if a["check_id"] in ("sec.no_secrets", "sec.no_sensitive_files") and a["status"] == "fail" else 1)
    return acts[:n]
