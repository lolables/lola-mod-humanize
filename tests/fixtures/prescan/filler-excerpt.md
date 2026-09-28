# Build Cache Report

The build cache can store compiled objects for every branch. It cannot store the flags each object was built with.

The cache hit rate fell from 82% to 61% after the compiler upgrade. Each miss costs about forty seconds of CPU.

The upgrade note is short: it names the new version and nothing else.

Appendix A: the rollout, as one concrete fleet: 300 runners across two regions.

Set `cache.key: v2` and `cache.flags: on` in the runner config: the defaults ignore flags.

The cache is warm. It does not help on the first build after a cold restart of every runner in the fleet.

Every object in the cache was built before the flag audit began last spring.

## Findings

All timing figures are from the nightly run on commit 4f2a9c1 in March.

The fix is a flag digest in the cache key, and nothing more.

All timing figures are from the nightly run on commit 4f2a9c1 in March.
