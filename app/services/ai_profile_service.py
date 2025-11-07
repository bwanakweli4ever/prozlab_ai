import os
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

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
        # Support common env var names
        self.openai_api_key = (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OPENAI_APIKEY")
            or os.getenv("OPENAI_KEY")
            or (getattr(settings, 'OPENAI_API_KEY', None) if settings else None)
            or (getattr(settings, 'OPENAI_APIKEY', None) if settings else None)
        )

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

    def _call_openai(self, resume_text: str) -> Optional[Dict[str, Any]]:
        if not self.openai_api_key:
            return None
        try:
            import http.client, json
            conn = http.client.HTTPSConnection("api.openai.com")
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert tech recruiter and career coach. Analyze resumes and suggest improvements and profile fields."},
                    {"role": "user", "content": f"Resume text:\n\n{resume_text}\n\nExtract structured fields (name, email, phone, location, years_experience, skills, bio summary). Suggest improvements and rephrase the summary in 2 variants. Return JSON with keys: extracted, suggestions, rephrased_summaries (array)."}
                ],
                "response_format": {"type": "json_object"}
            }
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.openai_api_key}'
            }
            conn.request("POST", "/v1/chat/completions", body=json.dumps(payload), headers=headers)
            res = conn.getresponse()
            data = res.read()
            if res.status >= 400:
                logger.error(f"OpenAI API error {res.status}: {data.decode('utf-8')}")
                return None
            raw = data.decode('utf-8')
            import json as _json
            obj = _json.loads(raw)
            content = obj['choices'][0]['message']['content']
            return _json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return None

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
        for l in lines[:30]:
            m = re.search(r"location\s*[:\-]\s*(.+)", l, re.I)
            if m:
                location = m.group(1).strip()
                break
            if re.search(r",\s*[A-Za-z]{2,}($|[^A-Za-z])", l) and not re.search(r"@|\d{3,}", l):
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
            "rephrased_summaries": [
                "Results-driven professional with a proven track record delivering impactful solutions across multiple domains.",
                "Detail-oriented specialist focused on quality, efficiency, and measurable outcomes in every engagement.",
            ],
        }

    def analyze_resume(self, file_path: str) -> Dict[str, Any]:
        text, method = self._extract_text(file_path)
        meta = {"extraction_method": method, "text_chars": len(text)}
        if not text:
            # Try OpenAI even without text to return useful templates/suggestions
            ai = self._call_openai("The uploaded PDF text could not be extracted. Provide a generic, high-quality professional profile summary template and suggestions.")
            if ai:
                ai.setdefault("meta", meta)
                return ai
        ai = self._call_openai(text) if text else None
        if ai:
            ai.setdefault("meta", meta)
            return ai
        if text:
            result = self.heuristic_analyze(text)
            result.setdefault("meta", meta)
            return result
        return {"extracted": {}, "suggestions": ["Could not read PDF text. Please upload a text-based PDF (not a scanned image)."], "rephrased_summaries": [], "meta": meta}

    def status(self) -> Dict[str, Any]:
        return {"openai_configured": bool(self.openai_api_key)}

    def review_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Review an existing profile and suggest targeted improvements.

        Returns:
          {
            suggested_updates: { field: value, ... },
            suggestions: [..human-readable tips..],
            rephrased_bio: [..options..]
          }
        """
        # Build input text
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
        input_text = "\n".join(fields)

        # If OpenAI is available, ask for structured JSON with suggested_updates per field
        if self.openai_api_key:
            try:
                import http.client, json
                conn = http.client.HTTPSConnection("api.openai.com")
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a senior recruiter and profile optimization expert."},
                        {"role": "user", "content": (
                            "Here is a professional profile. Critique it and suggest targeted improvements.\n"
                            "Return JSON with keys: suggested_updates (object of only fields that should change: bio, location, years_experience, hourly_rate, availability, education, certifications, website, linkedin, preferred_contact_method),"
                            " suggestions (array of concise tips), rephrased_bio (array of 2-3 improved bios).\n\n" + input_text
                        )}
                    ],
                    "response_format": {"type": "json_object"}
                }
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.openai_api_key}'
                }
                conn.request("POST", "/v1/chat/completions", body=json.dumps(payload), headers=headers)
                res = conn.getresponse()
                data = res.read()
                if res.status < 400:
                    raw = data.decode('utf-8')
                    obj = json.loads(raw)
                    content = obj['choices'][0]['message']['content']
                    return json.loads(content)
            except Exception as e:
                logger.error(f"OpenAI review_profile failed: {e}")

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
        rephrased_bio = []
        if bio:
            rephrased_bio = [
                "Impact-focused engineer with a track record of delivering scalable, reliable systems and measurable outcomes.",
                "Versatile professional specializing in high-quality solutions, collaboration, and continuous improvement.",
            ]
        return {"suggested_updates": suggested_updates, "suggestions": suggestions, "rephrased_bio": rephrased_bio}

    def rank_professionals(self, service_request: Dict[str, Any], candidates: list[Dict[str, Any]], top_k: int = 10) -> list[Dict[str, Any]]:
        """Rank professionals for a service request. Uses OpenAI if configured; otherwise heuristic.

        service_request: dict with keys like service_title, service_description, service_category,
                         location_preference, budget_max, remote_work_allowed
        candidates: list of dicts each having first_name, last_name, email, location, years_experience,
                    hourly_rate, rating, specialties (list[str])
        Returns: list of {candidate: obj, score: float, reasons: [str]}
        """
        # If OpenAI available, request a JSON ranking
        if self.openai_api_key and candidates:
            try:
                import http.client, json
                conn = http.client.HTTPSConnection("api.openai.com")
                prompt = {
                    "request": service_request,
                    "candidates": candidates,
                    "instructions": "Rank candidates for best match. Return JSON array sorted desc by score with objects {index, score (0-100), reasons (array of short strings)}. index refers to the index in candidates array. Favor matching specialty/category, sufficient experience, reasonable hourly within budget, local if not remote, higher rating."
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a matching engine producing numeric scores and concise reasons."},
                        {"role": "user", "content": json.dumps(prompt)}
                    ],
                    "response_format": {"type": "json_object"}
                }
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.openai_api_key}'
                }
                conn.request("POST", "/v1/chat/completions", body=json.dumps(payload), headers=headers)
                res = conn.getresponse()
                data = res.read()
                if res.status < 400:
                    obj = json.loads(data.decode('utf-8'))
                    content = obj['choices'][0]['message']['content']
                    ranked = json.loads(content)
                    # Expect ranked to be {"ranking": [{index, score, reasons:[]}, ...]} or array itself
                    items = ranked.get("ranking") if isinstance(ranked, dict) else ranked
                    result = []
                    for r in (items or []):
                        try:
                            idx = int(r.get("index"))
                            if 0 <= idx < len(candidates):
                                result.append({
                                    "candidate": candidates[idx],
                                    "score": float(r.get("score", 0)),
                                    "reasons": r.get("reasons", [])
                                })
                        except Exception:
                            continue
                    return result[:top_k]
            except Exception as e:
                logger.error(f"OpenAI rank_professionals failed: {e}")

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


