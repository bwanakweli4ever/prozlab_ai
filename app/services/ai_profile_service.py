import base64
import json
import logging
import os
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar

import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-opus-5-5"
MARKETPLACE_CONTEXT = (
    "Prozlab is a US company that sends verified IT, web and software professionals to client businesses. "
    "Professionals build a profile so we can match them to client work."
)

T = TypeVar("T", bound=BaseModel)


# ---- Structured outputs Claude must return ----

class _Experience(BaseModel):
    role: str
    company: str
    period: str
    description: str


class _EducationItem(BaseModel):
    institution: str
    degree: str
    period: str


class _ResumeFields(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: str
    location: str
    years_experience: Optional[int]
    skills: List[str]
    bio: str
    education: str
    certifications: str
    website: str
    linkedin: str
    experiences: List[_Experience]
    education_items: List[_EducationItem]


class _ResumeAnalysis(BaseModel):
    extracted: _ResumeFields
    suggestions: List[str]
    rephrased_summaries: List[str]


class _SuggestedUpdates(BaseModel):
    bio: Optional[str]
    location: Optional[str]
    years_experience: Optional[int]
    hourly_rate: Optional[float]
    availability: Optional[Literal["full-time", "part-time", "contract", "freelance"]]
    education: Optional[str]
    certifications: Optional[str]
    website: Optional[str]
    linkedin: Optional[str]
    preferred_contact_method: Optional[Literal["email", "phone", "linkedin", "website"]]


class _ProfileReview(BaseModel):
    suggested_updates: _SuggestedUpdates
    suggestions: List[str]
    rephrased_bio: List[str]


class _RankedCandidate(BaseModel):
    index: int
    score: float
    reasons: List[str]


class _Ranking(BaseModel):
    ranking: List[_RankedCandidate]


RESUME_SYSTEM = (
    MARKETPLACE_CONTEXT + " Turn the attached resume into profile fields. "
    "Use only facts stated in the resume: when it does not say something, use an empty string, an empty list or null. "
    "location is the person's city and state or country only. years_experience is total years of professional work. "
    "bio is 2-4 sentences in the first person that a client would read. "
    "rephrased_summaries are two alternative bios, also first person and built only from the resume. "
    "suggestions are 3-5 specific, practical ways to strengthen this profile."
)

REVIEW_SYSTEM = (
    MARKETPLACE_CONTEXT + " Review the professional profile you are given and suggest targeted improvements. "
    "In suggested_updates, set only the fields that should change and leave every other field null. "
    "Never invent employers, numbers, certifications or other facts that are not in the profile. "
    "suggestions are concise, specific tips. rephrased_bio holds 2-3 improved first-person bios built only from the profile's facts."
)

RANK_SYSTEM = (
    MARKETPLACE_CONTEXT + " Rank candidate professionals for a client's service request. "
    "Return every candidate you would consider, sorted by score descending, with score 0-100 and short reasons. "
    "index is the candidate's position in the candidates array. Favor a matching specialty or category, enough experience, "
    "an hourly rate within budget, a local candidate when the work is on site, and a higher rating."
)


class AIProfileService:
    def __init__(self):
        # Best-effort load of .env like EmailService so server picks up keys without process-level export
        try:
            from dotenv import load_dotenv  # type: ignore
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            load_dotenv(os.path.join(project_root, '.env'), override=False)
            load_dotenv(os.path.join(project_root, '.env.production'), override=False)
            load_dotenv(os.path.join(os.getcwd(), '.env'), override=False)
        except Exception:
            pass

        try:
            from app.config.settings import settings  # type: ignore
        except Exception:
            settings = None  # type: ignore
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or (
            getattr(settings, "ANTHROPIC_API_KEY", None) if settings else None
        )
        # Why the last Claude call failed: "not_configured", "quota", "auth", "rate_limit" or "error"
        self.last_ai_error: Optional[str] = None

    def _claude_parse(self, system: str, content: Any, output_format: Type[T]) -> Optional[T]:
        """One structured-output request to Claude. None on any failure; the reason is in last_ai_error."""
        if not self.anthropic_api_key:
            self.last_ai_error = "not_configured"
            return None
        client = anthropic.Anthropic(api_key=self.anthropic_api_key, timeout=120.0)
        try:
            response = client.beta.messages.parse(
                model=CLAUDE_MODEL,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                output_config={"effort": "low"},
                system=system,
                messages=[{"role": "user", "content": content}],
                output_format=output_format,
            )
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as e:
            logger.error(f"Claude auth error: {e}")
            self.last_ai_error = "auth"
            return None
        except anthropic.RateLimitError as e:
            logger.error(f"Claude rate limited: {e}")
            self.last_ai_error = "rate_limit"
            return None
        except anthropic.BadRequestError as e:
            logger.error(f"Claude bad request: {e}")
            self.last_ai_error = "quota" if "credit balance" in str(e).lower() else "error"
            return None
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            logger.error(f"Claude request failed: {e}")
            self.last_ai_error = "error"
            return None
        if response.stop_reason == "refusal" or response.parsed_output is None:
            logger.error(f"Claude returned no usable output (stop_reason={response.stop_reason})")
            self.last_ai_error = "error"
            return None
        self.last_ai_error = None
        return response.parsed_output

    def _extract_text(self, file_path: str) -> (str, str):
        """Try multiple libraries to extract text; return (text, method_used)."""
        # 1) PyPDF2
        try:
            from PyPDF2 import PdfReader  # type: ignore
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return extracted, "pypdf2"
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {e}")

        # 2) pdfplumber (good at layout)
        try:
            import pdfplumber  # type: ignore
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text_parts.append(page.extract_text() or "")
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return extracted, "pdfplumber"
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

        # 3) pdfminer.six (robust text extraction)
        try:
            from pdfminer.high_level import extract_text  # type: ignore
            mined = extract_text(file_path) or ""
            mined = mined.strip()
            if mined:
                return mined, "pdfminer.six"
        except Exception as e:
            logger.warning(f"pdfminer failed: {e}")

        return "", "none"

    def extract_text_from_pdf(self, file_path: str) -> str:
        text, _ = self._extract_text(file_path)
        return text

    def _analyze_with_claude(self, file_path: str, text: str) -> Optional[Dict[str, Any]]:
        """Send the PDF itself (Claude reads layout and scanned pages); fall back to extracted text if it's too big."""
        size = os.path.getsize(file_path)
        if file_path.lower().endswith(".pdf") and size <= 25 * 1024 * 1024:
            with open(file_path, "rb") as f:
                pdf_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
            content: Any = [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": "This is my resume. Fill in my profile fields from it."},
            ]
        elif text:
            content = f"Resume text:\n\n{text}"
        else:
            return None
        parsed = self._claude_parse(RESUME_SYSTEM, content, _ResumeAnalysis)
        return parsed.model_dump() if parsed else None

    def heuristic_analyze(self, resume_text: str) -> Dict[str, Any]:
        # Enhanced heuristic extraction for common profile fields
        import re
        lines = [l.strip() for l in resume_text.splitlines() if l.strip()]

        def first_nonempty() -> str:
            for l in lines:
                # skip lines that are section headers
                if re.search(r"^(education|experience|skills|summary|objective)[:\s]", l, re.I):
                    continue
                if len(l.split()) >= 2 and len(l) <= 80:
                    return l
            return ""

        # Name (best-effort): take first non-empty, non-header line that looks like a name
        name_line = first_nonempty()
        first_name = last_name = ""
        if name_line and not re.search(r"@|\d", name_line):
            parts = re.sub(r"\s+", " ", name_line).split(" ")
            if 2 <= len(parts) <= 4:
                first_name = parts[0].strip(",()[]{}")
                last_name = parts[-1].strip(",()[]{}")

        # Email
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)
        email = email_match.group(0) if email_match else ""

        # Phone (supports +, spaces, dashes, parentheses)
        phone_match = re.search(r"(\+?\d[\d \-()]{7,}\d)", resume_text)
        phone = phone_match.group(0).strip() if phone_match else ""

        # Location: look for 'Location:' or a line with City, Country pattern
        location = ""
        for l in lines[:6]:
            for seg in re.split(r"\s*[·•|■]\s*", l):
                seg = seg.strip()
                if len(seg) <= 40 and re.fullmatch(r"[A-Z][A-Za-z .'\-]+,\s*[A-Z][A-Za-z .]+", seg):
                    location = seg
                    break
            if location:
                break
        for l in ([] if location else lines[:30]):
            m = re.search(r"location\s*[:\-]\s*(.+)", l, re.I)
            if m:
                location = m.group(1).strip()
                break
            if len(l) <= 60 and re.search(r",\s*[A-Za-z]{2,}($|[^A-Za-z])", l) and not re.search(r"@|\d{3,}", l):
                # looks like 'City, Country/State'
                location = l
                break
        # Clean composite lines like: '■ Kigali, Rwanda | ■ 8+ Years ...'
        if location and '|' in location:
            location = location.split('|')[0]
        location = re.sub(r"^[•■\-\s]+", "", location).strip()

        # Years of experience
        years_experience = None
        ym = re.search(r"(\d{1,2})\+?\s+years?", resume_text, re.I)
        if ym:
            try:
                years_experience = float(ym.group(1))
            except Exception:
                years_experience = None

        # Skills: collect from 'Skills'/'Technologies' sections and comma lists following
        skills: list[str] = []
        lower = [l.lower() for l in lines]
        for idx, l in enumerate(lower):
            if l.startswith("skills") or l.startswith("technical skills") or "technologies" in l:
                # take current line after ':' and next 3 lines for lists
                block = lines[idx: idx + 4]
                for bl in block:
                    after_colon = bl.split(":", 1)[-1] if ":" in bl else bl
                    parts = [p.strip(" ,;•\t") for p in re.split(r",|\u2022|\|", after_colon)]
                    for p in parts:
                        if p and 2 <= len(p) <= 40 and not re.search(r"^skills", p, re.I):
                            skills.append(p)
        skills = list(dict.fromkeys(skills))[:50]

        # Education and Certifications sections (simple block capture)
        def capture_section(title: str) -> str:
            content: list[str] = []
            start = False
            for l in lines:
                if re.match(fr"^{title}[:\s]*$", l, re.I) or re.match(fr"^{title}[:\s]", l, re.I):
                    start = True
                    # keep text after ':' if on same line
                    after = l.split(":", 1)
                    if len(after) == 2 and after[1].strip():
                        content.append(after[1].strip())
                    continue
                if start:
                    if re.match(r"^(experience|work experience|skills|projects|summary|objective)[:\s]", l, re.I):
                        break
                    content.append(l)
            return "\n".join(content).strip()

        education = capture_section("education|education and qualifications|qualifications")
        certifications = capture_section("certifications|certification|licenses|licences|licensing")

        # Parse experience section into items
        def capture_experience_items() -> list[dict]:
            block = capture_section("experience|work experience|employment history|professional experience")
            if not block:
                return []
            items: list[dict] = []
            # Split on bullet/blank lines
            raw_items = re.split(r"\n\s*(?:[•\u2022\-\*]|\d+\.)\s+|\n\s*\n", block)
            for it in raw_items:
                t = it.strip()
                if not t:
                    continue
                # Try to extract role — company (dates)
                role = company = period = ""
                # Common pattern: Role — Company (YYYY–YYYY)
                m = re.search(r"^(?P<role>[^\n\-–—]{3,}?)\s*[\-–—]\s*(?P<company>[^\n(]{2,}?)(?:\s*\((?P<period>[^)]+)\))?", t)
                if m:
                    role = m.group('role').strip()
                    company = m.group('company').strip()
                    period = (m.group('period') or '').strip()
                else:
                    # Fallback: detect date-like spans for period
                    pm = re.search(r"(\d{4}[^\n]{0,20}?\d{4}|\d{4}\s*[-–]\s*Present|Present)", t, re.I)
                    if pm:
                        period = pm.group(0).strip()
                    # Heuristic split by ' at ' or ' @ '
                    hm = re.search(r"^(?P<role>[^@\nat]{3,}?)(?:\s+at\s+|\s+@\s+)(?P<company>[^\n]+)$", t, re.I)
                    if hm:
                        role = hm.group('role').strip()
                        company = hm.group('company').strip()
                items.append({
                    "role": role,
                    "company": company,
                    "period": period,
                    "description": t,
                })
            return items

        experiences = capture_experience_items()

        # Parse education into items by splitting lines that look like entries
        def education_items_from_text(txt: str) -> list[dict]:
            results: list[dict] = []
            if not txt:
                return results
            for line in [l.strip() for l in txt.splitlines() if l.strip()]:
                # Expect patterns like 'University — Degree (years)'
                em = re.search(r"^(?P<institution>[^\u2014\-–—(]{3,}?)[\s\-–—]+(?P<degree>[^()\n]{2,}?)(?:\s*\((?P<period>[^)]+)\))?", line)
                if em:
                    results.append({
                        "institution": em.group('institution').strip(),
                        "degree": em.group('degree').strip(),
                        "period": (em.group('period') or '').strip(),
                        "raw": line,
                    })
                else:
                    # Add as raw if contains university/college keywords
                    if re.search(r"university|college|school|institute", line, re.I):
                        results.append({"institution": "", "degree": "", "period": "", "raw": line})
            return results

        education_items = education_items_from_text(education)

        # Websites
        website_match = re.search(r"https?://[\w\-\./?#%&=]+", resume_text, re.I)
        website = website_match.group(0) if website_match else ""

        linkedin_match = re.search(r"https?://(www\.)?linkedin\.com/[^\s]+", resume_text, re.I)
        linkedin = linkedin_match.group(0) if linkedin_match else ""

        # Bio summary: first few non-header lines
        summary = " ".join(lines[:5])[:600]

        return {
            "extracted": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "phone_number": phone,
                "location": location,
                "years_experience": years_experience,
                "skills": skills,
                "bio": summary or "Experienced professional seeking opportunities.",
                "education": education,
                "education_items": education_items,
                "certifications": certifications,
                "website": website,
                "linkedin": linkedin,
                "experiences": experiences,
            },
            "suggestions": [
                "Quantify achievements (e.g., reduced costs by 20%).",
                "Include modern tools and frameworks you’ve used in the last 2-3 years.",
                "Add concise, role-specific keywords to pass ATS filters.",
            ],
            "rephrased_summaries": [],
        }

    def analyze_resume(self, file_path: str) -> Dict[str, Any]:
        lower = file_path.lower()
        if lower.endswith(".docx"):
            from pathlib import Path
            from app.services.resume_storage import docx_text
            text, method = docx_text(Path(file_path)), "docx"
        elif lower.endswith(".doc"):
            return {"extracted": {}, "suggestions": ["Old Word (.doc) files can't be read automatically. Save your CV as PDF or .docx and try again."], "rephrased_summaries": [], "meta": {"extraction_method": None, "text_chars": 0, "ai_used": False, "ai_error": None}}
        else:
            text, method = self._extract_text(file_path)
        meta: Dict[str, Any] = {"extraction_method": method, "text_chars": len(text)}
        ai = self._analyze_with_claude(file_path, text)
        if ai:
            meta.update(ai_used=True, ai_error=None)
            ai["meta"] = meta
            return ai
        meta.update(ai_used=False, ai_error=self.last_ai_error)
        if text:
            result = self.heuristic_analyze(text)
            result["meta"] = meta
            return result
        return {"extracted": {}, "suggestions": ["Could not read text from this file. Upload a text-based PDF or .docx (not a scanned image)."], "rephrased_summaries": [], "meta": meta}

    def status(self) -> Dict[str, Any]:
        return {"ai_configured": bool(self.anthropic_api_key), "provider": "anthropic", "model": CLAUDE_MODEL}

    def review_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Review an existing profile and suggest targeted improvements.

        Returns {suggested_updates: {field: value}, suggestions: [...], rephrased_bio: [...], ai_used, ai_error}
        """
        fields = [
            f"Name: {profile.get('first_name','')} {profile.get('last_name','')}",
            f"Email: {profile.get('email','')}",
            f"Phone: {profile.get('phone_number','')}",
            f"Location: {profile.get('location','')}",
            f"Years Experience: {profile.get('years_experience','')}",
            f"Hourly Rate: {profile.get('hourly_rate','')}",
            f"Availability: {profile.get('availability','')}",
            f"Bio: {profile.get('bio','')}",
            f"Education: {profile.get('education','')}",
            f"Certifications: {profile.get('certifications','')}",
            f"Website: {profile.get('website','')}",
            f"LinkedIn: {profile.get('linkedin','')}",
            f"Preferred Contact: {profile.get('preferred_contact_method','')}",
        ]
        parsed = self._claude_parse(REVIEW_SYSTEM, "\n".join(fields), _ProfileReview)
        if parsed:
            return {
                "suggested_updates": parsed.suggested_updates.model_dump(exclude_none=True),
                "suggestions": parsed.suggestions,
                "rephrased_bio": parsed.rephrased_bio,
                "ai_used": True,
                "ai_error": None,
            }

        # Heuristic fallback
        suggestions = []
        suggested_updates: Dict[str, Any] = {}
        bio = (profile.get('bio') or '').strip()
        if len(bio) < 80:
            suggestions.append("Bio is short; add 2-3 quantified achievements and core skills.")
        if not profile.get('location'):
            suggestions.append("Add a clear city, country for location.")
        if not profile.get('years_experience'):
            suggestions.append("Specify years of experience to improve matching.")
        if not profile.get('hourly_rate'):
            suggestions.append("Add an hourly rate to set expectations.")
        if not profile.get('education'):
            suggestions.append("Add education details with degree and years.")
        if not profile.get('certifications'):
            suggestions.append("List relevant certifications (e.g., AWS, Azure, security).")
        if not profile.get('linkedin'):
            suggestions.append("Include a LinkedIn URL for credibility.")
        return {
            "suggested_updates": suggested_updates,
            "suggestions": suggestions,
            "rephrased_bio": [],
            "ai_used": False,
            "ai_error": self.last_ai_error,
        }

    def rank_professionals(self, service_request: Dict[str, Any], candidates: list[Dict[str, Any]], top_k: int = 10) -> list[Dict[str, Any]]:
        """Rank professionals for a service request with Claude; heuristic scoring if Claude is unavailable.

        service_request: dict with keys like service_title, service_description, service_category,
                         location_preference, budget_max, remote_work_allowed
        candidates: list of dicts each having first_name, last_name, email, location, years_experience,
                    hourly_rate, rating, specialties (list[str])
        Returns: list of {candidate: obj, score: float, reasons: [str]}
        """
        if candidates:
            payload = json.dumps({"request": service_request, "candidates": candidates}, default=str)
            parsed = self._claude_parse(RANK_SYSTEM, payload, _Ranking)
            if parsed:
                result = []
                for r in parsed.ranking:
                    if 0 <= r.index < len(candidates):
                        result.append({"candidate": candidates[r.index], "score": float(r.score), "reasons": r.reasons})
                result.sort(key=lambda item: item["score"], reverse=True)
                return result[:top_k]

        # Heuristic fallback
        results: list[Dict[str, Any]] = []
        req_cat = (service_request.get("service_category") or "").lower()
        loc_pref = (service_request.get("location_preference") or "").lower()
        remote = bool(service_request.get("remote_work_allowed"))
        budget_max = service_request.get("budget_max")
        estimated_hours = 40
        max_hourly = (budget_max / estimated_hours) if budget_max else None

        for c in candidates:
            score = 0.0
            reasons: list[str] = []
            # verification assumed in caller filter
            # specialty match
            specialties = [s.lower() for s in (c.get("specialties") or [])]
            if req_cat and any(req_cat in s for s in specialties):
                score += 30
                reasons.append("Matching specialty")
            # location
            if not remote and loc_pref and c.get("location"):
                if loc_pref in c["location"].lower():
                    score += 15
                    reasons.append("Local match")
            # experience
            y = c.get("years_experience") or 0
            score += min(25, (y or 0) * 3)
            if y:
                reasons.append(f"{y}+ years experience")
            # rating
            r = c.get("rating") or 0
            score += min(20, (r or 0) * 4)
            if r and r >= 4.0:
                reasons.append("High rating")
            # hourly within budget
            hr = c.get("hourly_rate")
            if max_hourly is not None:
                if hr is None or hr <= max_hourly:
                    score += 10
                    reasons.append("Within budget")
            results.append({"candidate": c, "score": score, "reasons": reasons})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


