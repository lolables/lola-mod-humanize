# API Rate Limiting Strategy

Rate limiting is an essential component of any production API. It protects backend services from excessive load and ensures fair resource allocation across all consumers. Our implementation uses a sliding window approach built on Redis.

Each API key is assigned a tier that determines its rate limits. Free-tier keys are limited to 100 requests per minute, while paid-tier keys receive 1,000 requests per minute. Enterprise keys can be configured with custom thresholds based on their specific contractual agreements.

The sliding window algorithm provides a more accurate measurement than fixed windows. Furthermore, it avoids the burst problem that occurs at window boundaries. When a request arrives, we check the sorted set in Redis for the caller's key, remove expired entries, and count the remaining ones.

When a client exceeds their limit, the API returns a 429 status code with a `Retry-After` header. The response body includes the current limit, remaining requests, and the reset timestamp. This enables clients to implement proper backoff strategies and maintain optimal throughput.

We leverage Redis's built-in TTL mechanism to automatically clean up expired window data, ensuring efficient memory utilization. The approach has proven to be robust across our deployment, handling over 50,000 requests per second with minimal latency overhead.

Monitoring is handled through Prometheus metrics that track rejection rates per tier. This data helps inform decisions about adjusting limits and identifying clients that may need to upgrade their tier to better accommodate their usage patterns.
