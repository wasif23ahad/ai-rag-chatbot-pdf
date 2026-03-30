"""
Query Expansion — Generate query variations to improve retrieval coverage.

Expands a single user query into multiple variants using:
1. Synonym replacement (simple word-level)
2. Query restructuring (who/what/where/when/how variants)
3. Keyword extraction and focus shifts

This improves recall by matching chunks that use different terminology
or emphasize different aspects of the same information.
"""

import re
from typing import List


class QueryExpander:
    """
    Expands queries into multiple variants for multi-query retrieval.

    Example:
        Input:  "What are the coding challenge requirements?"
        Output: [
            "What are the coding challenge requirements?",
            "coding challenge requirements",
            "What does the coding challenge ask for?",
            "requirements for the coding challenge",
        ]
    """

    # Common synonym mappings for technical/assessment contexts
    SYNONYMS = {
        "requirements": ["requirements", "needs", "criteria", "specifications"],
        "coding": ["coding", "programming", "development", "implementation"],
        "challenge": ["challenge", "task", "assignment", "project"],
        "document": ["document", "file", "pdf", "content"],
        "function": ["function", "method", "routine", "procedure"],
        "data": ["data", "information", "content"],
        "create": ["create", "build", "implement", "develop"],
        "use": ["use", "utilize", "employ", "apply"],
        "must": ["must", "should", "required to", "needs to"],
    }

    def __init__(self, max_variants: int = 4) -> None:
        self._max_variants = max_variants

    def expand(self, query: str) -> List[str]:
        """
        Generate query variations for improved retrieval.

        Args:
            query: Original user question.

        Returns:
            List of query variants (deduplicated, includes original).
        """
        variants = {query.strip()}

        # Variant 1: Keyword extraction (remove filler words)
        keywords = self._extract_keywords(query)
        if keywords:
            variants.add(keywords)

        # Variant 2: Synonym substitution
        synonym_variant = self._apply_synonyms(query)
        if synonym_variant != query:
            variants.add(synonym_variant)

        # Variant 3: Question reformulation
        reformulated = self._reformulate_question(query)
        if reformulated:
            variants.add(reformulated)

        # Variant 4: Focus on key nouns
        noun_focus = self._extract_noun_phrases(query)
        if noun_focus:
            variants.add(noun_focus)

        return list(variants)[: self._max_variants]

    def _extract_keywords(self, query: str) -> str:
        """Remove common filler words to get core keywords."""
        filler_words = {
            "what",
            "are",
            "the",
            "is",
            "a",
            "an",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "and",
            "or",
            "does",
            "do",
            "did",
            "can",
            "could",
            "would",
            "should",
            "will",
            "how",
            "why",
            "when",
            "where",
            "who",
            "tell",
            "me",
            "about",
            "explain",
            "describe",
        }
        words = query.lower().split()
        keywords = [w for w in words if w not in filler_words and len(w) > 2]
        return " ".join(keywords) if keywords else ""

    def _apply_synonyms(self, query: str) -> str:
        """Replace key terms with synonyms."""
        result = query.lower()
        for word, synonyms in self.SYNONYMS.items():
            if word in result:
                # Replace with first synonym that's different
                for syn in synonyms:
                    if syn != word:
                        result = result.replace(word, syn, 1)
                        break
                break  # Only substitute one term per variant
        return result

    def _reformulate_question(self, query: str) -> str:
        """Reformulate question structure."""
        query_lower = query.lower().strip()

        # What is/are X → How does X work / Tell me about X
        if query_lower.startswith("what is "):
            return "Tell me about " + query[8:]
        if query_lower.startswith("what are "):
            return "Explain the " + query[9:]

        # How to X → X implementation / How do I X
        if query_lower.startswith("how to "):
            return "How do I " + query[7:]

        # Remove leading question words for keyword search
        for prefix in ["what is ", "what are ", "how does ", "explain ", "describe "]:
            if query_lower.startswith(prefix):
                return query[len(prefix) :].strip().capitalize()

        return ""

    def _extract_noun_phrases(self, query: str) -> str:
        """Extract likely noun phrases (simple heuristic)."""
        # Look for patterns like "X requirements", "Y features", "Z components"
        patterns = [
            r"(\w+)\s+(requirements?|features?|components?|functions?|steps?|rules?)",
            r"(coding|programming|technical|system)\s+(\w+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query.lower())
            if matches:
                # Return the matched phrase
                if isinstance(matches[0], tuple):
                    return " ".join(matches[0])
                return matches[0]

        return ""
