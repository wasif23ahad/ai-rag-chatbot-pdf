"""
Guard — two independent safety checks:

1. check_injection(text)
   Scans raw user input for prompt injection patterns BEFORE the LLM is called.
   Returns (True, pattern_name) if the text is an attack.
   Callers must reject with HTTP 400: { "error": "Invalid input detected." }
   NEVER reveal the pattern_name to the API caller — log it internally only.

2. check_similarity_threshold(scores, threshold)
   Prevents hallucination by skipping the LLM entirely when the best retrieved
   chunk is below the similarity threshold.
   Returns True if the request should proceed to the LLM.

3. validate_response(response)
   Post-LLM heuristic check: returns True if the answer appears grounded
   (i.e. not the exact refusal string).

Security hardening (T7):
   - Category 1: Direct instruction override ("ignore previous instructions", etc.)
   - Category 2: Role / persona injection ("you are now", "pretend to be", "new persona", etc.)
   - Category 3: Delimiter injection (<|system|>, [INST], ### System:, <<SYS>>, etc.)
   - Category 4: Encoding / obfuscation (Base64, Unicode escape sequences, URL encoding)
   - Category 5: Context poisoning ("the document says to ignore...")
   - Category 6: Jailbreak keywords (DAN, JAILBREAK, developer mode, unrestricted AI)
   - Category 7: Subtle overrides ("override system", "bypass", "disregard constraints")
"""

import base64
import re
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Injection patterns — compiled once at module load for performance.
# Each entry: (category_name, compiled_pattern)
# Ordered from most specific to most general to minimise false positives.
# ---------------------------------------------------------------------------

INJECTION_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    # -----------------------------------------------------------------------
    # Category 1: Direct instruction override
    # -----------------------------------------------------------------------
    (
        "instruction_override",
        re.compile(
            r"ignore\s+(previous|all|your|the|any|prior)\s+"
            r"(instructions?|rules?|prompts?|constraints?|context|guidelines?)",
            re.IGNORECASE,
        ),
    ),
    (
        "forget_prompt",
        re.compile(
            r"forget\s+(your|the|all|every|prior)\s+(system\s+)?prompt",
            re.IGNORECASE,
        ),
    ),
    (
        "disregard",
        re.compile(
            r"disregard\s+(all|your|previous|the|any|prior)\s+"
            r"(instructions?|rules?|context|constraints?|guidelines?)",
            re.IGNORECASE,
        ),
    ),
    (
        "override_system",
        re.compile(
            r"(override|bypass|circumvent|neutralise|neutralize|nullify)\s+"
            r"(your\s+)?(system|instructions?|rules?|constraints?|filters?|safety)",
            re.IGNORECASE,
        ),
    ),
    (
        "prior_instructions",
        re.compile(
            r"(disregard|cancel|erase|delete|remove|clear)\s+(all\s+)?"
            r"(prior|previous|earlier|above|preceding)\s+(instructions?|rules?|context)",
            re.IGNORECASE,
        ),
    ),

    # -----------------------------------------------------------------------
    # Category 2: Role / persona injection
    # -----------------------------------------------------------------------
    (
        "role_override",
        re.compile(
            r"you\s+are\s+now\s+(a|an|the)\s+\w+",
            re.IGNORECASE,
        ),
    ),
    (
        "pretend",
        re.compile(
            r"(pretend|act|behave|simulate)\s+"
            r"(you\s+are|as\s+if|like|to\s+be)\s+(a|an|you|an?\s+\w+)?",
            re.IGNORECASE,
        ),
    ),
    (
        "new_persona",
        re.compile(
            r"(new\s+persona|your\s+new\s+(role|identity|name|purpose)|"
            r"your\s+name\s+is\s+now|henceforth\s+you\s+(are|will\s+be)|"
            r"from\s+now\s+on\s+you\s+(are|will\s+be))",
            re.IGNORECASE,
        ),
    ),
    (
        "unrestricted_ai",
        re.compile(
            r"(you\s+are|act\s+as)\s+(an?\s+)?(fully\s+)?"
            r"(unrestricted|uncensored|unfiltered|free|evil|unaligned)\s+"
            r"(AI|assistant|chatbot|model|llm)?",
            re.IGNORECASE,
        ),
    ),
    (
        "no_rules",
        re.compile(
            r"(you\s+have|without|no)\s+(no\s+)?"
            r"(restrictions?|rules?|limits?|constraints?|guidelines?|filters?)\s*"
            r"(now|anymore|applied|whatsoever)?",
            re.IGNORECASE,
        ),
    ),

    # -----------------------------------------------------------------------
    # Category 3: Special / delimiter injection
    # -----------------------------------------------------------------------
    (
        "delimiter_injection",
        re.compile(
            r"(<\|system\|>|\[INST\]|###\s*system|<system>|<<SYS>>|"
            r"\[/INST\]|<\|im_start\|>|<\|im_end\|>|"
            r"<\|assistant\|>|<\|user\|>|\[SYSTEM\]|"
            r"<s>\s*\[INST\]|\[SYS\])",
            re.IGNORECASE,
        ),
    ),

    # -----------------------------------------------------------------------
    # Category 4: Encoding / obfuscation tricks
    # -----------------------------------------------------------------------
    (
        "base64_trick",
        re.compile(
            # Matches "base64:" with a payload, commonly used to encode injection
            r"base64\s*:\s*[A-Za-z0-9+/]{8,}={0,2}",
            re.IGNORECASE,
        ),
    ),
    (
        "unicode_escape",
        re.compile(
            # Unicode escape sequences — common in obfuscated injections
            r"\\u[0-9a-fA-F]{4}",
            re.IGNORECASE,
        ),
    ),
    (
        "url_encoding",
        re.compile(
            # URL-encoded characters often used to sneak past regex
            # %69 = 'i', %67 = 'g', %6e = 'n', %6f = 'o', %72 = 'r', %65 = 'e'
            r"%[0-9a-fA-F]{2}(%[0-9a-fA-F]{2}){2,}",
            re.IGNORECASE,
        ),
    ),

    # -----------------------------------------------------------------------
    # Category 5: Context poisoning via question framing
    # -----------------------------------------------------------------------
    (
        "context_poisoning",
        re.compile(
            r"the\s+document\s+(says?|states?|instructs?|tells?\s+you)\s+to\s+"
            r"(ignore|disregard|forget|bypass|override)",
            re.IGNORECASE,
        ),
    ),
    (
        "context_poisoning_variant",
        re.compile(
            r"(according\s+to|as\s+per)\s+(the\s+)?"
            r"(document|text|context|source)\s*[,:]?\s+"
            r"(ignore|disregard|forget|bypass|you\s+should)",
            re.IGNORECASE,
        ),
    ),

    # -----------------------------------------------------------------------
    # Category 6: Known jailbreak keywords
    # -----------------------------------------------------------------------
    (
        "jailbreak_terms",
        re.compile(
            r"\b(DAN|JAILBREAK|developer\s+mode|god\s+mode|"
            r"unrestricted\s+(AI|mode)|no-filter|evil\s+(mode|bot)|"
            r"jail\s*break|do\s+anything\s+now)\b",
            re.IGNORECASE,
        ),
    ),

    # -----------------------------------------------------------------------
    # Category 7: Subtle override / system manipulation phrases
    # -----------------------------------------------------------------------
    (
        "token_manipulation",
        re.compile(
            # Attempts to use special tokens or end-of-sequence markers
            r"(<\|endoftext\|>|<EOT>|</s>|<eos>|<pad>|\[END\]|\[STOP\])",
            re.IGNORECASE,
        ),
    ),
    (
        "indirect_role_change",
        re.compile(
            r"(switch|change|alter|transform|update|set|make)\s+"
            r"(your\s+)?(role|persona|identity|mode|behavior|behaviour|instructions?)\s+"
            r"(to|into|as|so\s+that)",
            re.IGNORECASE,
        ),
    ),
    (
        "ignore_previous",
        re.compile(
            r"ignore\s+previous",
            re.IGNORECASE,
        ),
    ),
]

# The exact refusal string the LLM is instructed to return
REFUSAL_STRING = "This information is not present in the provided document."

# ---------------------------------------------------------------------------
# Base64 semantic check (secondary layer for encoded injections)
# ---------------------------------------------------------------------------

_BASE64_INJECTION_KEYWORDS = [
    b"ignore",
    b"system",
    b"prompt",
    b"instruction",
    b"jailbreak",
    b"pretend",
    b"persona",
    b"override",
    b"disregard",
    b"forget",
]


def _contains_encoded_injection(text: str) -> bool:
    """
    Attempt to decode any Base64-looking blobs in the text and check if
    the decoded content contains injection keywords.

    Returns True if a decoded blob contains an injection keyword.
    """
    # Find all plausible Base64 tokens (≥ 16 chars to avoid false positives)
    candidates = re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", text)
    for candidate in candidates:
        try:
            decoded = base64.b64decode(candidate + "==")  # Pad to avoid errors
            decoded_lower = decoded.lower()
            for keyword in _BASE64_INJECTION_KEYWORDS:
                if keyword in decoded_lower:
                    return True
        except Exception:
            pass
    return False


class Guard:
    """
    Stateless safety checker. All methods are pure functions with no side effects.
    Instantiate once and reuse across requests.

    Security model:
      - Every check is performed BEFORE the LLM is called.
      - Failed checks must return HTTP 400 with a generic error message.
      - The detected pattern_name is for INTERNAL LOGGING ONLY — never
        expose it to the API caller.
    """

    def check_injection(self, text: str) -> Tuple[bool, str]:
        """
        Scan text for prompt injection patterns.

        Performs two passes:
          1. Regex scan against INJECTION_PATTERNS (covers all 7 categories).
          2. Base64 semantic decode check (catches encoded payloads).

        Returns:
            (is_injection: bool, pattern_name: str)
            pattern_name is an empty string when no injection is detected.
            Log pattern_name internally; NEVER expose it to the API caller.
        """
        # Pass 1 — regex scan
        for pattern_name, pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                return True, pattern_name

        # Pass 2 — Base64 semantic decode
        if _contains_encoded_injection(text):
            return True, "base64_semantic"

        return False, ""

    def check_similarity_threshold(
        self,
        scores: List[float],
        threshold: float,
    ) -> bool:
        """
        Decide whether to proceed to the LLM based on retrieval quality.

        Returns:
            True  → max score >= threshold → proceed to LLM
            False → max score <  threshold → skip LLM, return refusal directly

        This is the hallucination gate (Layer 2 defense). Calling the LLM
        when no relevant chunk exists guarantees a hallucinated answer.
        """
        if not scores:
            return False
        return max(scores) >= threshold

    def validate_response(self, response: str) -> bool:
        """
        Post-LLM heuristic: determine whether the response is grounded.

        Returns:
            True  → response appears grounded (not the exact refusal string)
            False → response is the refusal string (LLM found nothing relevant)

        Note: This is a simple exact-match check. The system prompt instructs the
        LLM to use the refusal string verbatim, so this check is reliable.
        """
        return response.strip() != REFUSAL_STRING
