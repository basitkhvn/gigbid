"""C3: structured hand-offs. Agents exchange these Pydantic objects, never free text, for anything a later step decides on."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    title: str
    deliverables: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    budget_min: float | None = None
    budget_max: float | None = None
    timeline_days: int | None = None
    screening_questions: list[str] = Field(default_factory=list)
    hidden_needs: list[str] = Field(default_factory=list)
    category: str = ""


class RiskReport(BaseModel):
    score: float = Field(ge=0, le=1)
    flags: list[str] = Field(default_factory=list)
    client_quality: float = Field(default=0.5, ge=0, le=1)
    explanation: str = ""
    injection_detected: bool = False


class RequirementMatch(BaseModel):
    requirement: str
    supported: bool
    evidence_ids: list[str] = Field(default_factory=list)
    best_score: float = 0.0


class FitReport(BaseModel):
    score: float = Field(ge=0, le=1)
    matches: list[RequirementMatch] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class BidDecision(BaseModel):
    action: Literal["skip", "watch", "bid"]
    reasons: list[str] = Field(default_factory=list)
    auto: bool = False


class PriceQuote(BaseModel):
    bid: float
    low: float
    high: float
    connects_cost: int
    worth_connects: bool
    rationale: str


class Claim(BaseModel):
    text: str
    verdict: Literal["supported", "partial", "unsupported", "not_a_claim"]
    evidence_ids: list[str] = Field(default_factory=list)


class ProposalDraft(BaseModel):
    job_id: str
    cover_letter: str
    screening_answers: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    revision: int = 0


class Critique(BaseModel):
    ok: bool
    score: float = Field(ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    revision_instructions: str = ""


class ComplianceVerdict(BaseModel):
    passed: bool
    blocked: bool = False
    violations: list[str] = Field(default_factory=list)
    sanitized_text: str = ""
    reason: str = ""


class ConversationReply(BaseModel):
    intent: Literal["question", "negotiation", "interview_request", "scam_signal"]
    reply: str
    slots: list[str] = Field(default_factory=list)
