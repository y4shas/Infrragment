"""
LLM verification layer using Gemini Flash Lite.

This module is a VERIFIER, not a generator:
- For boundaries: confirms or flags deterministic boundary decisions
- For tables: flags likely structural issues in extracted tables
- All calls are logged with token counts for cost transparency

The verification layer is fully optional and toggleable via ENABLE_LLM_VERIFICATION.
The pipeline works without it — verification only catches deterministic pipeline errors.

Cost model (gemini-3.1-flash-lite):
    - Input:  $0.25 per 1M tokens
    - Output: $1.50 per 1M tokens
    - Average call: ~800 input tokens, ~50 output tokens
    - Per call cost: ~$0.000275
    - 2000-page PDF (~80 calls): ~$0.022
"""
import json
import logging
from typing import Optional
from dataclasses import dataclass, field

from config import ENABLE_LLM_VERIFICATION, GEMINI_API_KEY, GEMINI_MODEL
from config import INPUT_TOKEN_COST_PER_M, OUTPUT_TOKEN_COST_PER_M

logger = logging.getLogger(__name__)


@dataclass
class VerifierStats:
    """Tracks verification call statistics for cost transparency."""
    total_calls: int = 0
    boundary_calls: int = 0
    table_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    agreements: int = 0
    disagreements: int = 0
    errors: int = 0
    call_log: list[dict] = field(default_factory=list)

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.total_input_tokens / 1_000_000) * INPUT_TOKEN_COST_PER_M
        output_cost = (self.total_output_tokens / 1_000_000) * OUTPUT_TOKEN_COST_PER_M
        return input_cost + output_cost


class Verifier:
    """
    Gemini Flash Lite verifier for boundary and table decisions.

    Usage:
        verifier = Verifier()
        if verifier.is_available:
            result = verifier.verify_boundary(prev_text, curr_text, is_boundary=True)
    """

    def __init__(self):
        self.stats = VerifierStats()
        self._client = None
        self._available = False

        if ENABLE_LLM_VERIFICATION and GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=GEMINI_API_KEY)
                self._available = True
                logger.info(f"Verifier initialized with model {GEMINI_MODEL}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self._available = False
        else:
            if not ENABLE_LLM_VERIFICATION:
                logger.info("LLM verification disabled (ENABLE_LLM_VERIFICATION=false)")
            elif not GEMINI_API_KEY:
                logger.info("LLM verification disabled (no GEMINI_API_KEY)")

    @property
    def is_available(self) -> bool:
        return self._available

    def verify_boundary(
        self,
        prev_page_text: str,
        curr_page_text: str,
        is_boundary: bool,
        boundary_score: float,
    ) -> dict:
        """
        Verify a single boundary decision.

        Args:
            prev_page_text: Text from the last page of the previous document
            curr_page_text: Text from the first page of the next document
            is_boundary: The deterministic pipeline's decision
            boundary_score: The confidence score

        Returns:
            dict with keys: agreed, reason, error
        """
        if not self._available:
            return {"agreed": None, "reason": "Verifier not available", "error": None}

        # Truncate text to keep token usage low
        prev_snippet = prev_page_text[:600].strip()
        curr_snippet = curr_page_text[:600].strip()

        prompt = f"""You are verifying a document boundary detection decision in a multi-document PDF.

The deterministic pipeline decided that the transition between these two consecutive pages {"IS" if is_boundary else "IS NOT"} a document boundary (confidence: {boundary_score:.2f}).

=== END OF PREVIOUS PAGE ===
{prev_snippet}

=== START OF NEXT PAGE ===
{curr_snippet}

Do you agree with the decision that this transition {"IS" if is_boundary else "IS NOT"} a real document boundary?
Reply in exactly this format:
AGREE or DISAGREE
Reason: <one sentence explanation>"""

        return self._call_llm(prompt, "boundary")

    def verify_table(
        self,
        headers: list[str],
        first_rows: list[list[str]],
        last_rows: list[list[str]],
        total_rows: int,
    ) -> dict:
        """
        Verify an extracted table's structural correctness.

        Args:
            headers: Table column headers
            first_rows: First 3 rows of data
            last_rows: Last 3 rows of data
            total_rows: Total number of rows

        Returns:
            dict with keys: agreed, reason, error
        """
        if not self._available:
            return {"agreed": None, "reason": "Verifier not available", "error": None}

        # Build compact table representation
        header_str = " | ".join(headers)
        first_str = "\n".join(" | ".join(r) for r in first_rows[:3])
        last_str = "\n".join(" | ".join(r) for r in last_rows[:3])

        prompt = f"""You are verifying the structural correctness of a table extracted from a PDF document.

Headers: {header_str}
Total rows: {total_rows}

First rows:
{first_str}

Last rows:
{last_str}

Check for these common extraction errors:
1. Misaligned columns (data in wrong columns)
2. Merged cells that should be separate
3. Missing or incorrect headers
4. Data that doesn't match header types

Reply in exactly this format:
OK or ISSUES
Notes: <brief description of any issues found, or "None">"""

        return self._call_llm(prompt, "table")

    def _call_llm(self, prompt: str, call_type: str) -> dict:
        """Make a single LLM call and log the result."""
        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )

            text = response.text.strip()

            # Parse response
            agreed = None
            reason = text

            if call_type == "boundary":
                if text.upper().startswith("AGREE"):
                    agreed = True
                elif text.upper().startswith("DISAGREE"):
                    agreed = False
            elif call_type == "table":
                if text.upper().startswith("OK"):
                    agreed = True
                elif text.upper().startswith("ISSUES"):
                    agreed = False

            # Extract reason line if present
            for line in text.split("\n"):
                if line.strip().startswith(("Reason:", "Notes:")):
                    reason = line.split(":", 1)[1].strip()
                    break

            # Track stats
            input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else len(prompt) // 4
            output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else len(text) // 4

            self.stats.total_calls += 1
            self.stats.total_input_tokens += input_tokens
            self.stats.total_output_tokens += output_tokens

            if call_type == "boundary":
                self.stats.boundary_calls += 1
            else:
                self.stats.table_calls += 1

            if agreed is True:
                self.stats.agreements += 1
            elif agreed is False:
                self.stats.disagreements += 1

            self.stats.call_log.append({
                "type": call_type,
                "agreed": agreed,
                "reason": reason,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            })

            logger.debug(
                f"Verifier [{call_type}]: {'AGREED' if agreed else 'DISAGREED'} "
                f"(in={input_tokens}, out={output_tokens})"
            )

            return {"agreed": agreed, "reason": reason, "error": None}

        except Exception as e:
            self.stats.errors += 1
            self.stats.total_calls += 1
            logger.warning(f"Verifier call failed: {e}")
            return {"agreed": None, "reason": "", "error": str(e)}

    def get_stats_dict(self) -> dict:
        """Return stats as a serializable dict."""
        return {
            "total_calls": self.stats.total_calls,
            "boundary_calls": self.stats.boundary_calls,
            "table_calls": self.stats.table_calls,
            "total_input_tokens": self.stats.total_input_tokens,
            "total_output_tokens": self.stats.total_output_tokens,
            "agreements": self.stats.agreements,
            "disagreements": self.stats.disagreements,
            "errors": self.stats.errors,
            "estimated_cost_usd": self.stats.estimated_cost_usd,
        }
