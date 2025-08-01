"""Service for evaluating governance proposals."""

from typing import Dict, Any, List
import re
from models import Proposal, VoteDecision


class ProposalEvaluationService:
    """Service for evaluating governance proposals."""

    def __init__(self):
        """Initialize the evaluation service."""
        # Define patterns for treasury amount detection
        self.treasury_patterns = [
            # Dollar format with M/K: $2.5M USDC or $5M in USDC
            (r"\$(\d+(?:\.\d+)?)([MK])(?:\s+in)?\s+([A-Z]{2,6})\b", "dollar_mk"),
            # Standard format with commas: 1,000,000 USDC
            (r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+([A-Z]{2,6})\b", "standard"),
            # Shorthand with M/K: 1M DAI
            (r"(\d+(?:\.\d+)?)([MK])\s+([A-Z]{2,6})\b", "shorthand"),
            # Simple number: 50 ETH
            (r"(\d+(?:\.\d+)?)\s+([A-Z]{2,6})\b", "simple"),
        ]

        # Risk keywords for governance evaluation
        self.governance_risk_keywords = {
            "high": [
                "voting",
                "mechanism",
                "governance",
                "quorum",
                "threshold",
                "power",
            ],
            "medium": ["parameter", "update", "change", "modify", "adjust"],
            "low": ["documentation", "typo", "fix", "minor", "cosmetic"],
        }

    async def analyze_proposal_impact(self, proposal: Proposal) -> Dict[str, Any]:
        """Analyze potential impact of proposal.

        Args:
            proposal: The proposal to analyze

        Returns:
            Dictionary containing impact analysis
        """
        # Check for financial impact
        treasury_result = await self.assess_treasury_implications(proposal)
        has_financial_impact = treasury_result["treasury_impact"] is not None

        # Determine impact level based on amount
        impact_level = "low"
        if has_financial_impact and treasury_result["treasury_impact"]:
            amount = treasury_result["treasury_impact"]["amount"]
            if amount >= 500000:
                impact_level = "high"
            elif amount >= 100000:
                impact_level = "medium"

        return {
            "has_financial_impact": has_financial_impact,
            "estimated_amount": treasury_result["treasury_impact"]["amount"]
            if treasury_result["treasury_impact"]
            else 0,
            "impact_level": impact_level,
        }

    async def assess_treasury_implications(self, proposal: Proposal) -> Dict[str, Any]:
        """Assess treasury and financial impact using regex.

        Args:
            proposal: The proposal to analyze

        Returns:
            Dictionary with treasury impact details
        """
        # Combine title and body for analysis
        text = f"{proposal.title} {proposal.body}"

        # Try each pattern
        for pattern, pattern_type in self.treasury_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    if pattern_type == "dollar_mk":
                        # $2.5M USDC
                        amount = float(match.group(1))
                        multiplier = 1000000 if match.group(2).upper() == "M" else 1000
                        amount *= multiplier
                        currency = match.group(3).upper()
                    elif pattern_type == "standard":
                        # 1,000,000 USDC
                        amount = float(match.group(1).replace(",", ""))
                        currency = match.group(2).upper()
                    elif pattern_type == "shorthand":
                        # 1M DAI
                        amount = float(match.group(1))
                        multiplier = 1000000 if match.group(2).upper() == "M" else 1000
                        amount *= multiplier
                        currency = match.group(3).upper()
                    else:  # simple
                        # 50 ETH
                        amount = float(match.group(1))
                        currency = match.group(2).upper()

                    # Only return if currency looks valid (2-6 uppercase letters)
                    # and is not a generic term
                    if re.match(r"^[A-Z]{2,6}$", currency) and currency not in [
                        "TOKENS",
                        "TOKEN",
                        "COINS",
                        "COIN",
                    ]:
                        return {
                            "treasury_impact": {"amount": amount, "currency": currency}
                        }
                except:
                    continue

        # No financial impact detected
        return {"treasury_impact": None}

    async def evaluate_governance_risk(self, proposal: Proposal) -> Dict[str, Any]:
        """Evaluate governance and protocol risks.

        Args:
            proposal: The proposal to analyze

        Returns:
            Dictionary with risk assessment
        """
        # Combine title and body for analysis
        text = f"{proposal.title} {proposal.body}".lower()

        # Check for risk keywords
        risk_factors = []
        risk_level = "low"

        # Check low risk keywords first (to prioritize them)
        for keyword in self.governance_risk_keywords["low"]:
            if keyword in text:
                # If low risk keyword found, keep it low
                return {
                    "risk_level": "low",
                    "risk_factors": [],
                    "requires_careful_review": False,
                }

        # Check high risk keywords
        for keyword in self.governance_risk_keywords["high"]:
            if keyword in text:
                risk_factors.append(keyword)
                risk_level = "high"

        # If no high risk, check medium
        if risk_level == "low":
            for keyword in self.governance_risk_keywords["medium"]:
                if keyword in text:
                    risk_factors.append(keyword)
                    risk_level = "medium"

        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "requires_careful_review": risk_level == "high",
        }

    async def check_proposal_precedent(
        self, proposal: Proposal, history: List[VoteDecision]
    ) -> Dict[str, Any]:
        """Check against voting history precedents.

        Args:
            proposal: The proposal to analyze
            history: List of previous voting decisions

        Returns:
            Dictionary with precedent analysis
        """
        if not history:
            return {
                "has_precedent": False,
                "similar_votes": 0,
                "historical_stance": "none",
            }

        # Look for similar proposals in history
        similar_votes = 0
        supportive_votes = 0

        proposal_keywords = set(proposal.title.lower().split())

        for decision in history:
            # Check if reasoning mentions similar keywords
            if decision.reasoning:
                reasoning_keywords = set(decision.reasoning.lower().split())
                if proposal_keywords & reasoning_keywords:
                    similar_votes += 1
                    if decision.vote.value == "FOR":
                        supportive_votes += 1

        has_precedent = similar_votes > 0

        # Determine historical stance
        if not has_precedent:
            historical_stance = "none"
        elif supportive_votes > similar_votes / 2:
            historical_stance = "supportive"
        else:
            historical_stance = "opposed"

        return {
            "has_precedent": has_precedent,
            "similar_votes": similar_votes,
            "historical_stance": historical_stance,
        }

    async def analyze_community_sentiment(self, proposal: Proposal) -> Dict[str, Any]:
        """Analyze voting patterns and community response.

        Args:
            proposal: The proposal to analyze

        Returns:
            Dictionary with sentiment analysis
        """
        # Check if scores are available
        if not hasattr(proposal, "scores") or not proposal.scores:
            return {
                "sentiment": "unknown",
                "support_percentage": 0.0,
                "participation_level": "unknown",
            }

        # Calculate support percentage
        scores = proposal.scores
        total_votes = getattr(proposal, "scores_total", sum(scores))

        if total_votes == 0:
            return {
                "sentiment": "unknown",
                "support_percentage": 0.0,
                "participation_level": "low",
            }

        # Assume first choice is "For"
        support_percentage = (scores[0] / total_votes) * 100 if total_votes > 0 else 0

        # Determine sentiment
        if support_percentage >= 70:
            sentiment = "positive"
        elif support_percentage >= 40:
            sentiment = "mixed"
        else:
            sentiment = "negative"

        # Determine participation level
        if total_votes >= 1000:
            participation_level = "high"
        elif total_votes >= 100:
            participation_level = "medium"
        else:
            participation_level = "low"

        return {
            "sentiment": sentiment,
            "support_percentage": support_percentage,
            "participation_level": participation_level,
        }
