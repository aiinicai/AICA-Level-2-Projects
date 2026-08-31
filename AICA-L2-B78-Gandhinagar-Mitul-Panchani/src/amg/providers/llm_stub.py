"""Deterministic offline maker, checker, and entailment implementation."""

from __future__ import annotations

import re
from collections.abc import Iterable

from amg.models import (
    AssertionType,
    CandidateFact,
    CheckerReasonCode,
    CheckerVerdict,
    EntailmentVerdict,
    SourceType,
)
from amg.providers.llm_base import LLMProvider


_FIRST_PERSON = re.compile(
    r"\b(?:i|i['’](?:m|ve|d|ll)|my|our)\b", re.IGNORECASE
)
_USER_SUBJECT = re.compile(r"\b(?:the\s+)?user\b", re.IGNORECASE)
_INFERENCE_HEDGE = re.compile(
    r"\b(?:likely|probably|may|might|could|possibly|appears?|seems?)\b",
    re.IGNORECASE,
)
_BARE_ATTRIBUTION = re.compile(
    r"\b(?:the\s+)?user\s+(?:likely\s+|probably\s+|may\s+)?"
    r"(?:said|stated|reported|mentioned|wrote)\b",
    re.IGNORECASE,
)
_HYPOTHETICAL = re.compile(
    r"\b(?:if\s+i\s+were|suppose|imagine|would\s+be|i['’]d\s+be)\b",
    re.IGNORECASE,
)
_THIRD_PARTY = re.compile(
    r"\b(?:my\s+(?:colleague|coworker|friend|manager)|he|she|they)\b|\bthey\s+said\b",
    re.IGNORECASE,
)
_QUOTED = re.compile(r"[\"“”]|\b(?:said|wrote|quoted)\s*:", re.IGNORECASE)

_BASE_INSTRUCTION_PATTERNS = (
    re.compile(r"ignore\s+(?:all\s+)?previous", re.IGNORECASE),
    re.compile(r"^\s*system\s*:", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\b", re.IGNORECASE),
    re.compile(r"\bdebug\s+mode\b", re.IGNORECASE),
    re.compile(r"\bprint\s+(?:the\s+)?complete\b", re.IGNORECASE),
    re.compile(r"\boutput\s+(?:everything|all)\b", re.IGNORECASE),
    re.compile(r"\brole[ -]?play\b", re.IGNORECASE),
    re.compile(r"\bno\s+filtering\b", re.IGNORECASE),
    re.compile(r"\bdisregard\b", re.IGNORECASE),
    re.compile(r"\boverride\b", re.IGNORECASE),
)
_BALANCED_INSTRUCTION_PATTERNS = (
    re.compile(r"\bforget\s+(?:your|all|the)\s+(?:rules|instructions)\b", re.IGNORECASE),
    re.compile(r"\bpretend\s+(?:that\s+)?you\s+are\b", re.IGNORECASE),
)
_STRICT_INSTRUCTION_PATTERNS = (
    re.compile(r"^\s*(?:developer|assistant)\s*:", re.IGNORECASE),
    re.compile(r"\b(?:reveal|dump|exfiltrate)\b.*\b(?:memory|data|store)\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\b", re.IGNORECASE),
)


class StubProvider(LLMProvider):
    """Rule-based safety net designed to exercise every offline demo scenario."""

    def __init__(self, checker_strictness: str = "balanced") -> None:
        self._checker_strictness = checker_strictness

    @property
    def name(self) -> str:
        return "stub"

    def extract_candidates(self, user_text: str) -> list[CandidateFact]:
        candidates: list[CandidateFact] = []
        for sentence in self._sentences(user_text):
            if not self._looks_extractable(sentence):
                continue
            assertion_type = self._assertion_type(sentence)
            subject_key, category = self._subject_and_category(sentence)
            direct = CandidateFact(
                content=sentence,
                subject_key=subject_key,
                category=category,
                assertion_type=assertion_type,
                source_type=SourceType.USER_STATED,
            )
            candidates.append(direct)
            if assertion_type is AssertionType.DIRECT_SELF_STATEMENT:
                candidates.extend(self._inferences_for(direct))
        return candidates

    def check_candidate(
        self,
        content: str,
        assertion_type: AssertionType,
        source_type: SourceType,
    ) -> CheckerVerdict:
        stripped = content.strip()
        if len(stripped) < 3 or not re.search(r"[A-Za-z]", stripped):
            return self._rejected(
                CheckerReasonCode.EMPTY_OR_TRIVIAL,
                "The candidate contains no substantive statement.",
            )
        if self._instruction_shaped(stripped):
            return self._rejected(
                CheckerReasonCode.INSTRUCTION_SHAPED,
                "The candidate contains directive or role-override language.",
            )

        # The first-person proof is specific to the user_stated claim. An
        # inference makes a different claim and must instead remain visibly
        # third-person and uncertain so provenance is not blurred.
        if source_type is SourceType.AI_INFERRED:
            return self._check_inference(stripped, assertion_type)

        return self._check_user_statement(stripped, assertion_type)

    def _check_user_statement(
        self, stripped: str, assertion_type: AssertionType
    ) -> CheckerVerdict:
        if assertion_type is AssertionType.HYPOTHETICAL:
            return self._rejected(
                CheckerReasonCode.HYPOTHETICAL_FRAMING,
                "Hypothetical framing is not a current self-statement.",
            )
        if assertion_type is AssertionType.THIRD_PARTY:
            return self._rejected(
                CheckerReasonCode.THIRD_PARTY_SUBJECT,
                "The statement is about a third party.",
            )
        if assertion_type is AssertionType.QUOTED:
            return self._rejected(
                CheckerReasonCode.QUOTED_SPEECH,
                "Quoted speech is not independently attributable to the user.",
            )
        if _HYPOTHETICAL.search(stripped):
            return self._rejected(
                CheckerReasonCode.HYPOTHETICAL_FRAMING,
                "The text itself is hypothetical despite the claimed type.",
            )
        if _THIRD_PARTY.search(stripped):
            return self._rejected(
                CheckerReasonCode.THIRD_PARTY_SUBJECT,
                "The text itself has a third-party subject.",
            )
        if _QUOTED.search(stripped):
            return self._rejected(
                CheckerReasonCode.QUOTED_SPEECH,
                "The text itself is framed as quoted speech.",
            )
        if assertion_type is not AssertionType.DIRECT_SELF_STATEMENT or not _FIRST_PERSON.search(
            stripped
        ):
            return self._rejected(
                CheckerReasonCode.NOT_FIRST_PERSON,
                "The candidate does not read as a direct first-person statement.",
            )
        return CheckerVerdict(
            approved=True,
            reason_code=CheckerReasonCode.OK,
            notes="Direct first-person self-statement with no injection indicators.",
        )

    def _check_inference(
        self, stripped: str, assertion_type: AssertionType
    ) -> CheckerVerdict:
        # assertion_type describes the originating statement. Inferences may
        # only be derived from an origin that passed the direct-statement path.
        if assertion_type is AssertionType.HYPOTHETICAL:
            return self._rejected(
                CheckerReasonCode.HYPOTHETICAL_FRAMING,
                "An inference cannot be derived from hypothetical framing.",
            )
        if assertion_type is AssertionType.THIRD_PARTY:
            return self._rejected(
                CheckerReasonCode.THIRD_PARTY_SUBJECT,
                "An inference cannot be attributed to a third-party origin.",
            )
        if assertion_type is AssertionType.QUOTED:
            return self._rejected(
                CheckerReasonCode.QUOTED_SPEECH,
                "An inference cannot be derived from quoted speech.",
            )
        if _FIRST_PERSON.search(stripped) or not _USER_SUBJECT.search(stripped):
            return self._rejected(
                CheckerReasonCode.NOT_INFERENCE_SHAPED,
                "An AI inference must be phrased in third person about the user.",
            )
        if not _INFERENCE_HEDGE.search(stripped):
            return self._rejected(
                CheckerReasonCode.OVERCLAIMS_CERTAINTY,
                "An AI inference must use uncertainty language rather than assert a fact.",
            )
        if _BARE_ATTRIBUTION.search(stripped):
            return self._rejected(
                CheckerReasonCode.NOT_INFERENCE_SHAPED,
                "An AI inference must add a derived proposition, not merely attribute speech.",
            )
        return CheckerVerdict(
            approved=True,
            reason_code=CheckerReasonCode.OK,
            notes="Hedged third-person inference with no injection indicators.",
        )

    def check_entailment(
        self, new_fact: str, existing_fact: str
    ) -> EntailmentVerdict:
        new_text = self._normalized(new_fact)
        existing_text = self._normalized(existing_fact)

        if self._is_additive_detail(new_text) or self._is_additive_detail(existing_text):
            return EntailmentVerdict(
                contradicts=False,
                confidence=0.94,
                reason="Location or office detail complements an employer fact rather than replacing it.",
            )

        new_employer = self._employer_value(new_fact)
        existing_employer = self._employer_value(existing_fact)
        if new_employer and existing_employer:
            if new_employer != existing_employer:
                return EntailmentVerdict(
                    contradicts=True,
                    confidence=0.96,
                    reason="Both facts state a current employer but name different organizations.",
                )
            return EntailmentVerdict(
                contradicts=False,
                confidence=0.98,
                reason="Both facts identify the same employer.",
            )

        exclusive_pairs = (
            ("vegetarian", "eat meat"),
            ("vegan", "eat eggs"),
        )
        for left, right in exclusive_pairs:
            if (left in new_text and right in existing_text) or (
                right in new_text and left in existing_text
            ):
                return EntailmentVerdict(
                    contradicts=True,
                    confidence=0.90,
                    reason="The two stated preferences are mutually exclusive.",
                )

        return EntailmentVerdict(
            contradicts=False,
            confidence=0.82,
            reason="No mutually exclusive values were found; related detail may be additive.",
        )

    @staticmethod
    def _sentences(user_text: str) -> Iterable[str]:
        for part in re.split(r"(?<=[.!?])\s+|[\r\n]+", user_text.strip()):
            sentence = part.strip()
            if sentence:
                yield sentence

    @staticmethod
    def _looks_extractable(sentence: str) -> bool:
        # Suspicious memory directives are deliberately emitted as candidates so
        # the independent checker can reject and account for them downstream.
        return bool(
            _FIRST_PERSON.search(sentence)
            or _THIRD_PARTY.search(sentence)
            or re.search(r"^\s*system\s*:|\bremember\s+that\b", sentence, re.IGNORECASE)
        )

    @staticmethod
    def _assertion_type(sentence: str) -> AssertionType:
        if _HYPOTHETICAL.search(sentence):
            return AssertionType.HYPOTHETICAL
        if _THIRD_PARTY.search(sentence):
            return AssertionType.THIRD_PARTY
        if _QUOTED.search(sentence):
            return AssertionType.QUOTED
        return AssertionType.DIRECT_SELF_STATEMENT

    @staticmethod
    def _subject_and_category(sentence: str) -> tuple[str, str]:
        text = sentence.casefold()
        if re.search(
            r"\b(?:qualification|degree|certification|certified|chartered accountant|ca|cpa)\b",
            text,
        ):
            return "professional_qualification", "professional"
        if re.search(r"\b(?:vegetarian|vegan|eat|diet)\b", text):
            return "dietary_preference", "preference"
        if re.search(
            r"\b(?:work|employer|company|financial controller|moved on)\b|\bi['’]m\s+at\b|\bi\s+am\s+at\b",
            text,
        ):
            return "employer", "professional"
        if re.search(r"\b(?:office|area)\b", text):
            return "employer", "professional"
        if re.search(r"\b(?:city|located|location)\b", text):
            return "location", "profile"
        return "general", "profile"

    @staticmethod
    def _inferences_for(parent: CandidateFact) -> list[CandidateFact]:
        text = parent.content.casefold()
        inference: str | None = None
        subject_key = parent.subject_key
        category = parent.category
        if "vegetarian" in text:
            inference = "User likely avoids leather goods"
        elif "financial controller" in text:
            inference = "User likely has professional accounting and finance expertise"
            subject_key = "professional_expertise"
        if inference is None:
            return []
        return [
            CandidateFact(
                content=inference,
                subject_key=subject_key,
                category=category,
                assertion_type=AssertionType.DIRECT_SELF_STATEMENT,
                source_type=SourceType.AI_INFERRED,
                inferred_from_content=parent.content,
            )
        ]

    def _instruction_shaped(self, content: str) -> bool:
        patterns = _BASE_INSTRUCTION_PATTERNS
        if self._checker_strictness in {"balanced", "strict"}:
            patterns += _BALANCED_INSTRUCTION_PATTERNS
        if self._checker_strictness == "strict":
            patterns += _STRICT_INSTRUCTION_PATTERNS
        return any(pattern.search(content) for pattern in patterns)

    @staticmethod
    def _rejected(reason: CheckerReasonCode, notes: str) -> CheckerVerdict:
        return CheckerVerdict(approved=False, reason_code=reason, notes=notes)

    @staticmethod
    def _normalized(text: str) -> str:
        return re.sub(r"\s+", " ", text.casefold()).strip(" .")

    @staticmethod
    def _is_additive_detail(text: str) -> bool:
        return bool(
            re.search(r"\b(?:our|the|my)\s+office\b", text)
            or (re.search(r"\b(?:area|located|location)\b", text) and "work at" not in text)
        )

    @staticmethod
    def _employer_value(text: str) -> str | None:
        patterns = (
            r"\bwork(?:ing)?\s+(?:as\s+.+?\s+)?at\s+([A-Z][\w&'-]*(?:\s+[A-Z][\w&'-]*){0,3})",
            r"\b(?:I['’]m|I\s+am)\s+at\s+([A-Z][\w&'-]*(?:\s+[A-Z][\w&'-]*){0,3})",
            r"\bfinancial\s+controller\s+at\s+([A-Z][\w&'-]*(?:\s+[A-Z][\w&'-]*){0,3})",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value = re.split(r"\s+(?:in|now|and|but)\b", match.group(1), maxsplit=1)[0]
                return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
        return None
