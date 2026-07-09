from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import Literal

StructuralDecision = Literal["continue", "allow", "block"]


@dataclass(frozen=True)
class StructuralResult:
    decision: StructuralDecision
    attack_score: float
    benign_score: float
    matched_pattern: str | None
    details: dict


_OVERRIDE_PATTERNS = (
    re.compile(r"\bignore\b.{0,30}\b(previous|prior|above)\b.{0,20}\binstructions?\b", re.I),
    re.compile(r"\bdisregard\b.{0,20}\b(everything|all)\b", re.I),
    re.compile(r"\bnew system instructions?\b", re.I),
    re.compile(r"\bforget\b.{0,20}\b(rules|instructions|safety training)\b", re.I),
    re.compile(r"\bbypass\b.{0,40}\b(privilege|confidentiality|restrictions?)\b", re.I),
    re.compile(r"\boverride\b.{0,30}\b(confidentiality|privilege|restrictions?)\b", re.I),
    re.compile(r"\bmake an exception\b.{0,40}\b(for me|confidential|privilege)\b", re.I),
    re.compile(r"\brepeat\b.{0,30}\b(instructions?|everything)\b.{0,20}\babove\b", re.I),
)

_ROLE_PATTERNS = (
    re.compile(r"\byou are now\b", re.I),
    re.compile(r"\bact as\b.{0,40}\b(counsel|judge|associate|paralegal)\b", re.I),
    re.compile(r"\bpretend you are\b.{0,40}\b(rogue|counsel|judge|plaintiff|opposing)\b", re.I),
    re.compile(r"\bimagine you are\b.{0,40}\b(rogue|associate|counsel|judge)\b", re.I),
    re.compile(r"\bplay the judge\b", re.I),
    re.compile(r"\bdeveloper mode\b", re.I),
    re.compile(r"\bno restrictions\b", re.I),
    re.compile(r"\bno ethics duties\b", re.I),
    re.compile(r"\bwithout (any )?content policy\b", re.I),
)

_REFUSAL_PATTERNS = (
    re.compile(r"\bdo not refuse\b", re.I),
    re.compile(r"\bnever refuse\b", re.I),
    re.compile(r"\bnever mention\b.{0,30}\b(policy|ethics|limitations)\b", re.I),
    re.compile(r"\bcompliance screening is off\b", re.I),
    re.compile(r"\bcompliance checks? (are |is )?disabled\b", re.I),
    re.compile(r"\bjust comply with every request\b", re.I),
)

_LAW_ATTACK_PATTERNS = (
    re.compile(r"\bact as\b.{0,50}\boutside counsel\b", re.I),
    re.compile(r"\bdisclose\b.{0,40}\b(litigation playbook|privileged|confidential|work product)\b", re.I),
    re.compile(r"\bquote\b.{0,40}\b(confidential|privileged|strategy memo)\b", re.I),
    re.compile(r"\bsealed exhibit\b", re.I),
    re.compile(r"\bsettlement\b.{0,30}\b(amount|pay|agree)\b", re.I),
)

_OUTPUT_URL_EXFIL_PATTERNS = (
    re.compile(r"\b(append|include|add|embed|insert)\b.{0,40}\b(markdown )?link\b.{0,80}https?://", re.I),
    re.compile(
        r"https?://[^\s]+.{0,40}\b(in your|into your|to your)\b.{0,30}"
        r"\b(response|reply|answer|summary|footer|contract)\b",
        re.I,
    ),
    re.compile(r"\b(append|include|add|embed)\b.{0,60}\[[^\]]+\]\(https?://[^)]+\)", re.I),
)

_ROLE_JUDGE_DISCLOSURE = re.compile(
    r"\bplay the judge\b.{0,100}\b(disclos|work product|privileged|full disclosure)\b",
    re.I,
)

_EXFIL_PATTERNS = (
    re.compile(r"\boutput\b.{0,30}\b(hidden system|system message|scoring rubric)\b", re.I),
    re.compile(r"\battacker\.example\b", re.I),
    re.compile(r"\bexternal@proton\.me\b", re.I),
    re.compile(r"\bemail\b.{0,40}\b(privilege log|json)\b", re.I),
)

_BENIGN_PATTERNS = (
    re.compile(r"\bsecurity researcher\b", re.I),
    re.compile(r"\bred[- ]team(ing)?\b", re.I),
    re.compile(r"\bfor (my|a) (report|thesis|paper|training|training slide|compliance training)\b", re.I),
    re.compile(r"\bdocumenting\b.{0,30}\b(jailbreak|injection|attack)\b", re.I),
    re.compile(r"\bfictional (story|character|scenario)\b", re.I),
    re.compile(r"\bhypothetical\b.{0,40}\b(if|what if)\b", re.I),
    re.compile(r"\bexplain\b.{0,30}\b(what|how)\b.{0,30}\b(prompt injection|jailbreak)\b", re.I),
    re.compile(r"\b(moot court|mock trial|bar exam|training purposes)\b", re.I),
    re.compile(r"\blaw student\b", re.I),
    re.compile(r"\bpretend you are explaining\b", re.I),
    re.compile(r"\broleplay as a (professor|teacher)\b", re.I),
    re.compile(r"\bwhat is the standard\b", re.I),
    re.compile(r"\bhow many days does\b", re.I),
    re.compile(r"\bcan you explain what\b", re.I),
    re.compile(r"\bsummarize the holding\b", re.I),
    re.compile(r"\bi'm drafting a compliance\b", re.I),
    re.compile(r"\bwhat does indemnification\b", re.I),
    re.compile(r"\bvendor MSA\b", re.I),
    re.compile(r"\bmutual NDA\b", re.I),
    re.compile(r"\bwhat factors do courts\b", re.I),
    re.compile(r"\bwhat is the difference between\b", re.I),
    re.compile(r"\bhelp me understand\b", re.I),
    re.compile(r"\bfirst-year associate\b", re.I),
    re.compile(r"\bi'm (studying|preparing|writing)\b", re.I),
    re.compile(r"\bas a study aid\b", re.I),
    re.compile(r"\bDSAR workflow\b", re.I),
    re.compile(r"\bcan you outline\b", re.I),
    re.compile(r"\bwithout prejudice\b", re.I),
    re.compile(r"\blaw school clinic\b", re.I),
    re.compile(r"\bexplain the difference between\b", re.I),
    re.compile(r"\bhow do courts\b", re.I),
    re.compile(r"\bwhat does\b.{0,30}\bmean\b", re.I),
    re.compile(r"\boutline\b.{0,40}\b(controls|SOC|workflow)\b", re.I),
)

_DELIMITER_PATTERNS = (
    re.compile(r"<!--"),
    re.compile(r"\[\[system\]\]", re.I),
    re.compile(r"<\|system\|>", re.I),
    re.compile(r"###\s*system\b", re.I),
)

_LEGAL_TOPIC_RE = re.compile(
    r"\b("
    r"lease|contract|clause|agreement|statute|limitation|indemnity|arbitration|"
    r"vesting|unvested|vested|option|stock options?|licensing|negligence|doctrine|"
    r"amortization|refusal|termination|equity|merger|escrow|warranty|representation|"
    r"forum|compliance|fiduciary|severance|covenant|reconciliation|memorandum|"
    r"deposit|eviction|franchise|royalt|licen[cs]e|at-will|tenancy|damages|"
    r"liquidated|conflict check|forum non conveniens|pci|dss|blue sky|pro rata|"
    r"m&a|nda|msa|default"
    r")\b",
    re.I,
)

_INJECTION_IMPERATIVE_RE = re.compile(
    r"\b("
    r"ignore|disregard|forget|bypass|override|disclose|reveal|email|export|"
    r"paste|append|embed|pretend you are|act as|roleplay as|play the judge|"
    r"developer mode|make an exception|do not refuse|never refuse|comply with every"
    r")\b",
    re.I,
)

_SUSPICIOUS_NGRAMS = (
    "ignore previous",
    "disregard",
    "developer mode",
    "system prompt",
    "base64",
    "jailbreak",
    "override",
    "you are now",
    "pretend you are",
    "no restrictions",
    "execute",
    "exfil",
    "proton.me",
    "bypass privilege",
    "attorney-client",
    "outside counsel",
    "safety training",
    "do not refuse",
    "compliance screening",
    "hidden system",
    "work product",
    "privileged communication",
    "sealed exhibit",
    "settlement amount",
)


def _encoded_blob_score(text: str) -> float:
    score = 0.0
    if re.search(r"\b[A-Za-z0-9+/]{32,}={0,2}\b", text):
        score += 0.35
    for token in re.findall(r"\b[A-Za-z0-9+/]{16,}={0,2}\b", text):
        try:
            decoded = base64.b64decode(token + "==", validate=False)
            if len(decoded) >= 8 and decoded.isascii():
                score += 0.25
                break
        except Exception:
            continue
    if re.search(r"\\x[0-9a-f]{2}", text, re.I):
        score += 0.15
    return min(1.0, score)


def is_legal_topic_fragment(text: str) -> bool:
    """Short benign legal topic phrase without injection/imperative language."""
    stripped = text.strip()
    if not stripped or len(stripped) > 160:
        return False
    if _INJECTION_IMPERATIVE_RE.search(stripped):
        return False
    if re.search(r"\bencode\b.{0,40}\bbase64\b", stripped, re.I):
        return False
    if _encoded_blob_score(stripped) >= 0.15:
        return False
    if not _LEGAL_TOPIC_RE.search(stripped):
        return False
    if len(stripped.split()) > 24:
        return False
    if any(
        p.search(stripped)
        for p in _OVERRIDE_PATTERNS
        + _ROLE_PATTERNS
        + _REFUSAL_PATTERNS
        + _LAW_ATTACK_PATTERNS
        + _EXFIL_PATTERNS
        + _OUTPUT_URL_EXFIL_PATTERNS
    ):
        return False
    return True


def _imperative_ratio(text: str) -> float:
    words = re.findall(r"[a-z']+", text.lower())
    if not words:
        return 0.0
    imperatives = sum(
        1
        for w in words
        if w
        in {
            "ignore",
            "disregard",
            "forget",
            "execute",
            "output",
            "reveal",
            "print",
            "bypass",
            "override",
            "disclose",
            "quote",
        }
    )
    return min(1.0, imperatives / max(1, len(words)) * 8)


def analyze_structural(
    text: str,
    *,
    block_threshold: float = 0.85,
    allow_threshold: float = 0.20,
) -> StructuralResult:
    """Deterministic structural heuristics (handoff Part I.4)."""
    attack = 0.0
    benign = 0.0
    matched: str | None = None
    hits: list[str] = []

    for pattern in _OVERRIDE_PATTERNS:
        if pattern.search(text):
            attack += 0.35
            hits.append("instruction_override")
            break
    if "instruction_override" in hits:
        attack = max(attack, 0.88)
    for pattern in _ROLE_PATTERNS:
        if pattern.search(text):
            attack += 0.30
            hits.append("role_assignment")
            break
    for pattern in _REFUSAL_PATTERNS:
        if pattern.search(text):
            attack += 0.45
            if "refusal_suppression" not in hits:
                hits.append("refusal_suppression")
    for pattern in _LAW_ATTACK_PATTERNS:
        if pattern.search(text):
            attack += 0.40
            hits.append("law_domain_attack")
            break
    for pattern in _EXFIL_PATTERNS:
        if pattern.search(text):
            attack += 0.25
            hits.append("exfiltration")
            break
    for pattern in _OUTPUT_URL_EXFIL_PATTERNS:
        if pattern.search(text):
            attack += 0.55
            if "exfiltration" not in hits:
                hits.append("exfiltration")
            hits.append("output_url_injection")
            break
    if _ROLE_JUDGE_DISCLOSURE.search(text):
        attack += 0.50
        if "role_assignment" not in hits:
            hits.append("role_assignment")
        hits.append("judge_roleplay_disclosure")
    for pattern in _DELIMITER_PATTERNS:
        if pattern.search(text):
            attack += 0.25
            hits.append("injection_delimiter")
            break

    attack += _encoded_blob_score(text)
    attack += _imperative_ratio(text) * 0.2
    attack = min(1.0, attack)

    for pattern in _BENIGN_PATTERNS:
        if pattern.search(text):
            benign += 0.35
            hits.append("benign_framing")
    if is_legal_topic_fragment(text) and attack < block_threshold:
        benign = max(benign, 0.50)
        if "legal_topic_fragment" not in hits:
            hits.append("legal_topic_fragment")
    if "?" in text and benign > 0:
        benign += 0.1
    benign = min(1.0, benign)

    details = {"attack_score": round(attack, 4), "benign_score": round(benign, 4), "hits": hits}

    if attack >= block_threshold and benign < 0.35:
        return StructuralResult(
            decision="block",
            attack_score=attack,
            benign_score=benign,
            matched_pattern=hits[0] if hits else "structural_attack",
            details=details,
        )
    if round(benign, 2) >= 0.45 and attack <= allow_threshold:
        return StructuralResult(
            decision="allow",
            attack_score=attack,
            benign_score=benign,
            matched_pattern="benign_framing",
            details=details,
        )
    return StructuralResult(
        decision="continue",
        attack_score=attack,
        benign_score=benign,
        matched_pattern=None,
        details=details,
    )


def has_suspicious_segments(text: str, *, floor: float = 0.15) -> bool:
    """Return True when text contains segments worth embedding (handoff I.5 filter inverse)."""
    lower = text.lower()
    if any(ngram in lower for ngram in _SUSPICIOUS_NGRAMS):
        return True
    if _encoded_blob_score(text) >= floor:
        return True
    if any(
        p.search(text)
        for p in _OVERRIDE_PATTERNS
        + _ROLE_PATTERNS
        + _REFUSAL_PATTERNS
        + _LAW_ATTACK_PATTERNS
        + _EXFIL_PATTERNS
        + _DELIMITER_PATTERNS
    ):
        return True
    return False
