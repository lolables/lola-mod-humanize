# Clarity: Copy-Edit Defects

Defects that make prose read as unedited, whether or not a model wrote it.
The Pass 4 Tighten step uses this file. Any sentence a copy-editor would
reword goes in the Tighten inventory with its class from the table below,
even when nothing about it looks AI-generated.

Every example is invented. Match the shape, not the words.

Fixes keep the author's claim and stance and change only the wording. The
last class is the exception: report it, never fix it.

| Class | What it looks like (invented example) | Fix (invented rewrite) |
|---|---|---|
| Broken tense or aspect | "The migration has ran twice since Monday." | "The migration has run twice since Monday." |
| Broken tense or aspect | "By Friday we will been caching the manifest." | "By Friday we will be caching the manifest." |
| Broken tense or aspect | "The runner should of retried the upload." | "The runner should have retried the upload." |
| Private coinage or jargon compound | "Most of the lag comes from cold-shard drift." (never defined) | "Most of the lag comes from shards that sit idle long enough to fall out of the page cache." |
| Private coinage or jargon compound | "We fixed it with a pin sweep." | "We fixed it by pinning every lockfile entry to an exact version." |
| Vague or ambiguous referent | "The proxy retries the request and logs the timeout. This doubles the load." (the retry or the log?) | "The retry doubles the load on the upstream." |
| Vague or ambiguous referent | "The build reads the config and the manifest; if it is stale, it rebuilds everything." | "If the manifest is stale, the build rebuilds everything." |
| Vague or ambiguous referent | "We moved the index and dropped the old replica. All of that broke the nightly report." | Name the cause the author means: "Dropping the old replica broke the nightly report." If the text does not say which, report it. |
| Dangling trailing qualifier | "The cache hit rate rose to 90%, mostly." | "On most runners, the cache hit rate rose to 90%." |
| Dangling trailing qualifier | "The job finishes in four minutes, at least on the small runners." | "On the small runners, the job finishes in four minutes." |
| Mismatched correlative or parallel structure | "The flag either disables the cache or you can set the TTL to zero." | "Either disable the cache with the flag or set the TTL to zero." |
| Mismatched correlative or parallel structure | "The client is fast, reliable, and has clear error messages." | "The client is fast and reliable, and its error messages are clear." |
| Category mismatch in a contrast | "The bottleneck is the disk, not slow." (a noun against an adjective) | "The disk is the bottleneck; the network has headroom." |
| Category mismatch in a contrast | "This is a naming problem, not last week's outage." (a kind of problem against an event) | "This is a naming problem. It did not cause last week's outage." |
| Wrong conjunction | "The query uses the index and it still scans the whole table." (the clauses contrast) | "The query uses the index, but it still scans the whole table." |
| Wrong conjunction | "The deploy finished, but the health checks passed." (the clauses agree) | "The deploy finished and the health checks passed." |
| Truncated or garbled idiom | "We'll cross that bridge when it comes." | "We'll cross that bridge when we come to it." |
| Truncated or garbled idiom | "The flaky test is the tip of the problem." | "The flaky test is the tip of the iceberg." |
| Ambiguous gloss after a colon in a heading or label | `### Caching: The Hard Part` (caching as a whole, or one part of it?) | `### Cache Invalidation` (name the part) |
| Ambiguous gloss after a colon in a heading or label | `**Retries: no.**` (no to adding them, or no, they do not help?) | "Adding retries would not fix the timeout." |
| Hedge that contradicts the next sentence | "I'm not sure the index helps. It cuts query time from 900 ms to 40 ms." | Move the hedge to what is uncertain: "The index cuts query time from 900 ms to 40 ms in staging. I have not measured production." |
| Hedge that contradicts the next sentence | "This probably won't matter much. It breaks every client on protocol v2." | Report it; the author has to say which sentence holds. |
| Silent change to a number or scope stated elsewhere | The summary says the outage hit three regions; the timeline says four. | Report only: "Summary says three regions, timeline says four." Leave both as written. |
| Silent change to a number or scope stated elsewhere | The intro says every Linux runner is affected; the details say only arm64 runners. | Report only. Never pick one by guessing. |
| Silent change to a number or scope stated elsewhere | The paragraph above a table names four failing jobs; the table lists three. | Report only. Edit neither the prose nor the table. |
