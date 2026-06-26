"""Run multiple feed sources concurrently → normalize → Redis pub/sub, with an
optional TimescaleDB writer. The Phase 1 "concurrent real-time pipeline" demo.

    # zero infra (no Docker): 3 concurrent sources, normalized, printed
    cd backend && python -m data.run_feeds --no-redis --seconds 8

    # full pipeline (needs Docker: Redis + TimescaleDB)
    #   publishers -> Redis -> two INDEPENDENT subscribers (console + DB writer)
    cd backend && python -m data.run_feeds --seconds 15

By default it runs THREE synthetic sources over disjoint symbol sets — stand-ins
for three broker/public feeds — all emitting one normalized Tick format.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
from typing import Optional

from data.bus import close_redis, get_redis, publish_tick, subscribe
from data.models import Tick
from data.sources.base import FeedSource
from data.sources.synthetic import SyntheticFeedSource


def default_sources() -> list[FeedSource]:
    return [
        SyntheticFeedSource({"RELIANCE": 2900.0, "TCS": 3850.0}, rate_per_sec=3, name="feed-A", seed=1),
        SyntheticFeedSource({"INFY": 1500.0, "HDFCBANK": 1650.0}, rate_per_sec=2, name="feed-B", seed=2),
        SyntheticFeedSource({"ICICIBANK": 1100.0}, rate_per_sec=1.5, name="feed-C", seed=3),
    ]


def _fmt(t: Tick) -> str:
    return f"[{t.source:<7}] {t.time:%H:%M:%S} {t.symbol:<10} {t.price:>10.2f}  x{t.size}"


async def gather_ticks(sources, seconds: float = 1.0, max_total: Optional[int] = None) -> list[Tick]:
    """Consume sources concurrently into a list (no Redis). Used by tests and the
    --no-redis demo. Stops after `seconds` or once `max_total` ticks collected.
    """
    out: list[Tick] = []
    stop = asyncio.Event()

    async def consume(src: FeedSource) -> None:
        async for tick in src.stream():
            out.append(tick)
            if max_total is not None and len(out) >= max_total:
                stop.set()
            if stop.is_set():
                return

    consumers = [asyncio.create_task(consume(s)) for s in sources]
    waiter = asyncio.create_task(stop.wait())
    await asyncio.wait({waiter, *consumers}, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
    stop.set()
    for t in consumers:
        t.cancel()
    await asyncio.gather(*consumers, return_exceptions=True)
    waiter.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await waiter
    return out


async def run_no_redis(seconds: float, sources) -> None:
    print(f"running {len(sources)} sources for {seconds:.0f}s (no Redis) ...\n")
    ticks = await gather_ticks(sources, seconds=seconds)
    for t in ticks:
        print(_fmt(t))
    by_source: dict[str, int] = {}
    for t in ticks:
        by_source[t.source] = by_source.get(t.source, 0) + 1
    print(f"\n{len(ticks)} ticks total  |  per source: {by_source}")


async def _publisher(src: FeedSource, r) -> None:
    async for tick in src.stream():
        await publish_tick(r, tick)


async def _console_subscriber(r) -> None:            # subscriber #1
    async for tick in subscribe(r):
        print(_fmt(tick))


async def _db_writer(batch: int = 25) -> None:       # subscriber #2 (independent)
    from data.storage import insert_ticks

    r = get_redis()
    buf: list[Tick] = []
    try:
        async for tick in subscribe(r):
            buf.append(tick)
            if len(buf) >= batch:
                await asyncio.to_thread(insert_ticks, list(buf))
                buf.clear()
    finally:
        if buf:
            with contextlib.suppress(Exception):
                await asyncio.to_thread(insert_ticks, list(buf))
        await close_redis(r)


async def run_with_redis(seconds: float, sources, write_db: bool) -> None:
    pub_r, sub_r = get_redis(), get_redis()
    tasks = [asyncio.create_task(_publisher(s, pub_r)) for s in sources]
    tasks.append(asyncio.create_task(_console_subscriber(sub_r)))
    if write_db:
        tasks.append(asyncio.create_task(_db_writer()))
    n_subs = 2 if write_db else 1
    print(f"publishing {len(sources)} feeds -> Redis; {n_subs} independent subscriber(s) for {seconds:.0f}s ...\n")
    try:
        await asyncio.sleep(seconds)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_redis(pub_r)
        await close_redis(sub_r)


def main() -> None:
    p = argparse.ArgumentParser(description="AlphaForge concurrent feed demo")
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--no-redis", action="store_true", help="in-memory demo, no infra needed")
    p.add_argument("--no-db", action="store_true", help="publish to Redis but skip the TimescaleDB writer")
    args = p.parse_args()

    sources = default_sources()
    if args.no_redis:
        asyncio.run(run_no_redis(args.seconds, sources))
    else:
        asyncio.run(run_with_redis(args.seconds, sources, write_db=not args.no_db))


if __name__ == "__main__":
    main()
