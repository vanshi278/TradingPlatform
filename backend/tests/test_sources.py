import asyncio
from datetime import timezone

from data.run_feeds import gather_ticks
from data.sources.synthetic import SyntheticFeedSource


def test_synthetic_emits_normalized_ticks():
    src = SyntheticFeedSource(
        {"RELIANCE": 2900.0, "TCS": 3850.0},
        rate_per_sec=500,
        name="feed-A",
        seed=42,
        max_ticks=25,
    )

    async def run():
        return [t async for t in src.stream()]

    ticks = asyncio.run(run())
    assert len(ticks) == 25
    assert all(t.source == "feed-A" for t in ticks)
    assert all(t.symbol in {"RELIANCE", "TCS"} for t in ticks)
    assert all(t.time.tzinfo == timezone.utc for t in ticks)
    assert all(t.price > 0 for t in ticks)


def test_three_sources_run_concurrently():
    sources = [
        SyntheticFeedSource({"A": 100.0}, rate_per_sec=200, name="s1", seed=1),
        SyntheticFeedSource({"B": 200.0}, rate_per_sec=200, name="s2", seed=2),
        SyntheticFeedSource({"C": 300.0}, rate_per_sec=200, name="s3", seed=3),
    ]
    ticks = asyncio.run(gather_ticks(sources, seconds=0.5))
    # all three feeds produced ticks in the same window => true concurrency
    assert {t.source for t in ticks} == {"s1", "s2", "s3"}
    assert all(t.time.tzinfo == timezone.utc for t in ticks)
