from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.proz.models.proz import ProzProfile

META_EVIDENCE_ID = "_verification_meta"

WORK_EXPERIENCE_TYPES = {"previous_employer", "work_sample"}
IDENTITY_TYPES = {"github", "linkedin", "identity_document"}
SKILL_TYPES = {"portfolio", "recommendation", "certification", "github", "work_sample"}


def evidences(profile: ProzProfile) -> List[Dict[str, Any]]:
    raw = profile.verification_evidences
    if not isinstance(raw, list):
        return []
    return [e for e in raw if e.get("id") != META_EVIDENCE_ID and e.get("type") != "system"]


def get_meta(profile: ProzProfile) -> Dict[str, Any]:
    raw = profile.verification_evidences
    if not isinstance(raw, list):
        return {}
    for item in raw:
        if item.get("id") == META_EVIDENCE_ID:
            return item
    return {}


def set_meta(profile: ProzProfile, meta: Dict[str, Any]) -> None:
    save_evidences(profile, evidences(profile), meta)


def save_evidences(
    profile: ProzProfile,
    user_items: List[Dict[str, Any]],
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    items = list(user_items)
    if meta:
        items.append({"id": META_EVIDENCE_ID, "type": "system", **meta})
    profile.verification_evidences = items


def compute_score(evidences_list: List[Dict[str, Any]]) -> int:
    weights = {
        "github": 25,
        "portfolio": 15,
        "work_sample": 20,
        "recommendation": 20,
        "linkedin": 10,
        "certification": 15,
        "previous_employer": 15,
        "identity_document": 20,
    }
    score = 0
    seen_types: set[str] = set()
    for item in evidences_list:
        t = item.get("type")
        if t in weights and t not in seen_types:
            score += weights[t]
            seen_types.add(t)
    return min(score, 100)


def requirements_met(evidences_list: List[Dict[str, Any]]) -> Dict[str, bool]:
    types = {e.get("type") for e in evidences_list}
    has_work_exp = bool(types & WORK_EXPERIENCE_TYPES) or any(
        e.get("type") == "previous_employer" for e in evidences_list
    )
    return {
        "identity_link": bool(types & IDENTITY_TYPES),
        "work_proof": bool(types & {"portfolio", "work_sample", "github", "previous_employer"}),
        "work_experience": has_work_exp,
        "third_party": bool(types & {"recommendation", "previous_employer", "certification"}),
        "minimum_items": len(evidences_list) >= 2,
    }


def verification_flags(evidences_list: List[Dict[str, Any]]) -> Dict[str, bool]:
    types = {e.get("type") for e in evidences_list}
    approved = {e.get("type") for e in evidences_list if e.get("status") == "approved"}
    return {
        "identity_verified": bool(approved & IDENTITY_TYPES) or bool(types & IDENTITY_TYPES),
        "work_experience_verified": bool(approved & WORK_EXPERIENCE_TYPES),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
