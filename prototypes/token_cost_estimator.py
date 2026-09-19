"""Token Usage and Cost Estimator."""

def estimate_token_count(text: str) -> int:
    # Rule of thumb: ~4 characters per token in English code
    return max(1, len(text) // 4)

def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    # Flash pricing: ~$0.075 per 1M input, $0.30 per 1M output
    input_cost = (prompt_tokens / 1_000_000) * 0.075
    output_cost = (completion_tokens / 1_000_000) * 0.30
    return input_cost + output_cost
