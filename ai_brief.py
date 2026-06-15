import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def generate_trading_brief(sig: dict, metrics: dict, trades_summary: str, ticker: str, short_w: int, long_w: int) -> str:
    prompt = f"""You are a quantitative analyst giving a plain-English trading brief to a retail investor.

ASSET: {ticker}
STRATEGY: Moving average crossover ({short_w}-day MA vs {long_w}-day MA)

CURRENT SIGNAL STATE:
- Position: {sig['state']}
- Current price: {sig['price']}
- {short_w}-day MA: {sig['ma_short']}
- {long_w}-day MA: {sig['ma_long']}
- Gap between MAs: {sig['ma_gap_pct']:+.2f}%
- Last crossover: {sig['last_cross_date']} ({sig['last_cross_type']})

BACKTEST PERFORMANCE (5-year):
{chr(10).join(f"- {k}: {v}" for k, v in metrics.items())}

TRADE HISTORY:
{trades_summary}

Write a concise trading brief (200-250 words) covering:
1. What the bot is doing right now and why — in plain English, not jargon
2. What would need to happen in the market to trigger the next signal change (roughly how far would the price need to move?)
3. An honest one-sentence verdict on whether this strategy is actually beating buy-and-hold and what that tells us

Be direct and honest. Do not hype the strategy. If buy-and-hold is winning, say so and explain why that is expected in this market environment. Write like a knowledgeable friend, not a financial advisor."""

    message = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text
