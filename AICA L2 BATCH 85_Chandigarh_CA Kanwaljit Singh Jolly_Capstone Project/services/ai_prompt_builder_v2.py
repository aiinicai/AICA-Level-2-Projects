"""
AI Prompt Builder V2 - Generic Token Utilities

This file now contains only generic token counting utilities.
Task-specific prompt building has been moved to respective task packs.
"""


def estimate_token_count(prompt: str) -> int:
    """
    Estimate token count for prompt.

    Args:
        prompt: Text to estimate tokens for

    Returns:
        Estimated token count (rough approximation: 4 chars per token)
    """
    # Rough estimate: 4 characters per token
    return len(prompt) // 4
