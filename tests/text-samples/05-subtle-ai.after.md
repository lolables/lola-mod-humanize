# API Rate Limiting Strategy

Rate limiting protects backend services from excess load and keeps resource usage fair across API consumers. We use a sliding window counter backed by Redis.

Each API key belongs to a tier with its own limits: free keys get 100 req/min, paid keys get 1,000 req/min. Enterprise keys have custom thresholds set per contract.

Sliding windows are more accurate than fixed windows and avoid the burst problem at window boundaries. When a request comes in, we check the caller's sorted set in Redis, drop expired entries, and count what's left.

Clients that exceed their limit get a 429 with a `Retry-After` header. The response body includes the current limit, remaining requests, and reset timestamp, so clients can back off correctly.

Redis's built-in TTL handles cleanup of expired window data. In production this handles 50k+ req/s with negligible latency overhead.

We track rejection rates per tier in Prometheus. That data feeds into decisions about limit adjustments and flags clients who might need a tier upgrade.
