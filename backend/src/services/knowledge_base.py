"""
Bharat Voice AI — RAG Knowledge Base Service

Provides grounded retrieval over official Indian government scheme documents,
crop advisories (Farm & Field), financial eligibility rules, and health triage guidelines.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent.logger import COMPONENT_AGENT, get_logger

logger = get_logger(COMPONENT_AGENT)


@dataclass
class KnowledgeDocument:
    doc_id: str
    track: str
    title: str
    content: str
    tags: list[str]


# Knowledge repository of grounded scheme PDFs, crop advisories, and track guidelines
KNOWLEDGE_BASE: list[KnowledgeDocument] = [
    KnowledgeDocument(
        doc_id="farm_crop_advisory_cotton_01",
        track="Farm & Field",
        title="Cotton Pink Bollworm Spraying & Pest Management Advisory",
        content=(
            "For Pink Bollworm in Cotton crops during mid-season flowering: Apply Neem-based formulations "
            "(Azadirachtin 1500 ppm) at 5ml/L initial stage. If infestation exceeds 10% damaged flowers, "
            "spray Profenofos 50% EC at 2ml/L water. Ensure spraying is done in early morning or evening. "
            "Maintain proper field sanitation and install pheromone traps at 2 traps per acre."
        ),
        tags=["cotton", "pink bollworm", "spraying", "pest", "irrigation", "kheda", "crops"],
    ),
    KnowledgeDocument(
        doc_id="farm_pm_kisan_02",
        track="Farm & Field",
        title="PM-Kisan Samman Nidhi Scheme Eligibility & Benefits",
        content=(
            "PM-Kisan provides ₹6,000 per year in 3 equal installments of ₹2,000 to eligible landholder farmer families. "
            "Small and marginal farmers holding cultivable land in their name qualify. Requires e-KYC completion and "
            "Aadhaar bank account seeding. Excludes institutional landholders and high income taxpayers."
        ),
        tags=["pm-kisan", "pm kisan", "scheme", "farmer", "subsidy", "eligibility", "6000"],
    ),
    KnowledgeDocument(
        doc_id="fin_pmjjby_01",
        track="Financial Services",
        title="Pradhan Mantri Jeevan Jyoti Bima Yojana (PMJJBY) Life Insurance",
        content=(
            "PMJJBY offers life insurance cover of ₹2 Lakh for death due to any cause. Premium is ₹436 per annum, "
            "auto-debited from savings account. Eligible for individuals aged 18 to 50 years with a bank account. "
            "Cover period is June 1 to May 31 each year."
        ),
        tags=["pmjjby", "life insurance", "insurance", "436", "lakh", "scheme", "financial"],
    ),
    KnowledgeDocument(
        doc_id="fin_kcc_02",
        track="Financial Services",
        title="Kisan Credit Card (KCC) Scheme Rules & Interest Subvention",
        content=(
            "KCC provides short-term crop loans up to ₹3 Lakh at a benchmark 7% per annum interest rate. "
            "Prompt repayment earns an additional 3% interest subvention, making effective interest rate 4% per annum. "
            "Covers crop cultivation, post-harvest expense, and allied activities like dairy and fisheries."
        ),
        tags=["kcc", "kisan credit card", "loan", "interest", "crop loan", "financial"],
    ),
    KnowledgeDocument(
        doc_id="health_triage_hypertension_01",
        track="Health Access",
        title="Hypertension & Routine Triage Guidance",
        content=(
            "For adults aged 30-60 with ongoing hypertension: Recommend daily salt restriction (<5g/day), "
            "30 minutes walking, and monthly blood pressure checkup at Primary Health Centre (PHC). "
            "Immediate emergency triage required if blood pressure exceeds 180/120 mmHg or symptoms include "
            "severe headache, chest pain, or blurred vision."
        ),
        tags=["health", "hypertension", "blood pressure", "triage", "phc", "age band"],
    ),
    KnowledgeDocument(
        doc_id="learning_math_subtraction_01",
        track="Learning & Literacy",
        title="Multi-Digit Subtraction with Regrouping (Borrowing) Method",
        content=(
            "When students make repeated mistakes borrowing across zeros in multi-digit subtraction: "
            "Use place value blocks (tens and ones). Explain regrouping by breaking 1 Ten into 10 Ones. "
            "Practice step-by-step subtraction starting from ones column first before tens."
        ),
        tags=["learning", "subtraction", "borrowing", "math", "regrouping", "mistakes"],
    ),
    KnowledgeDocument(
        doc_id="disaster_shelter_ward4_01",
        track="Disaster Response",
        title="Disaster Evacuation & Relief Camp Operations Guide",
        content=(
            "Relief Camp B (Ward 4) provides drinking water, medical triage, and wheelchair mobility assistance "
            "for elderly and disabled residents. Check-ins conducted twice daily at 8 AM and 6 PM. Emergency helpline: 1077."
        ),
        tags=["disaster", "relief camp", "ward 4", "mobility", "shelter", "evacuation"],
    ),
]


class KnowledgeBaseService:
    """RAG Service performing grounded keyword & semantic retrieval over knowledge base documents."""

    def __init__(self, documents: list[KnowledgeDocument] | None = None) -> None:
        self.documents = documents or KNOWLEDGE_BASE

    def search(self, query: str, track: str | None = None, top_k: int = 2) -> list[dict[str, Any]]:
        """
        Search knowledge base for relevant grounded documents matching user query.

        Args:
            query: User's question or search prompt.
            track: Optional domain track filter.
            top_k: Number of relevant snippets to return.

        Returns:
            List of matching document result dictionaries.
        """
        if not query:
            return []

        query_terms = set(re.findall(r"\w+", query.lower()))
        scores: list[tuple[float, KnowledgeDocument]] = []

        for doc in self.documents:
            if track and doc.track.lower() != track.lower():
                continue

            doc_text = f"{doc.title} {doc.content} {' '.join(doc.tags)}".lower()
            doc_words = set(re.findall(r"\w+", doc_text))

            overlap = query_terms.intersection(doc_words)
            if not overlap:
                continue

            # Calculate keyword match score + tag match bonus
            score = len(overlap) * 1.5
            for tag in doc.tags:
                if tag.lower() in query.lower():
                    score += 3.0

            scores.append((score, doc))

        scores.sort(key=lambda x: x[0], reverse=True)
        top_results = scores[:top_k]

        logger.info("Knowledge Base Search query='%s' found %d matching documents", query, len(top_results))

        return [
            {
                "doc_id": doc.doc_id,
                "track": doc.track,
                "title": doc.title,
                "grounded_content": doc.content,
            }
            for _, doc in top_results
        ]


# Singleton knowledge base service
_kb_service_instance: KnowledgeBaseService | None = None


def get_knowledge_base_service() -> KnowledgeBaseService:
    """Get singleton KnowledgeBaseService instance."""
    global _kb_service_instance
    if _kb_service_instance is None:
        _kb_service_instance = KnowledgeBaseService()
    return _kb_service_instance
