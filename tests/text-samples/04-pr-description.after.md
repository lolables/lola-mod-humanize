# Migrate caching layer to Redis Cluster

## What

Replaced single-node Redis with a 3-node Redis Cluster for the application cache.

## Why

The single-node setup was a scaling bottleneck and a single point of failure. We hit memory limits in production twice last quarter.

## Changes

- Swap `redis-py` client for `redis-py-cluster`
- Add consistent hashing for key distribution
- Configure automatic failover with Sentinel
- Set up LRU eviction policy (previously no eviction, which caused OOM crashes)
- Update connection pooling config

## Benchmarks

| Metric | Before | After |
|--------|--------|-------|
| p99 Latency | 45ms | 12ms |
| Cache Hit Rate | 78% | 94% |
| Memory Efficiency | 62% | 89% |

Benchmarked against production traffic replay (24h sample from March 14).

## Tests

- Unit tests for cluster client wrapper
- Integration tests against a local 3-node cluster (docker-compose in `test/`)
- Failover simulation: kill a node, verify recovery under load
