"""Async fetching of AsciiDoc content from GitHub."""

from __future__ import annotations

import asyncio

import httpx

from skillgen.config import MAX_CONCURRENT
from skillgen.discovery.topics import DiscoveredTopic


async def fetch_all(topics: list[DiscoveredTopic]) -> dict[str, str]:
    """Fetch all topic adoc files concurrently. Returns {adoc_path: content}."""
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results: dict[str, str] = {}

    async def fetch_one(client: httpx.AsyncClient, topic: DiscoveredTopic) -> None:
        async with sem:
            try:
                resp = await client.get(topic.raw_url)
                if resp.status_code == 200:
                    results[topic.adoc_path] = resp.text
                else:
                    print(f"    {topic.adoc_path}... HTTP {resp.status_code}", flush=True)
            except httpx.HTTPError as e:
                print(f"    {topic.adoc_path}... error: {e}", flush=True)

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        await asyncio.gather(*(fetch_one(client, t) for t in topics))

    return results
