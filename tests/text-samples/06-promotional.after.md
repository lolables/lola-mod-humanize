# CloudPulse

CloudPulse is a monitoring platform for infrastructure observability. It collects metrics, logs, and traces from your stack, then provides alerting and anomaly detection on top of that data.

## Features

- **Real-time alerting** with configurable thresholds and notification routing
- **Anomaly detection** using statistical baselines beyond static thresholds
- **Shared dashboards** for team-wide visibility into system health
- **Collaborative alert management**, so on-call engineers can annotate incidents and hand off context
- **Annotation system** for marking deployments, config changes, and other events on metric graphs

## Architecture

CloudPulse runs as a set of services: collectors ingest telemetry, a time-series store handles retention, and a query engine serves the dashboard and alert evaluation. It scales horizontally at each layer.

## Integrations

The platform plugs into existing workflows through standard protocols (OpenTelemetry, Prometheus remote write, StatsD) and has pre-built integrations for common infrastructure (AWS, GCP, Kubernetes).

Teams at various companies use it as their primary observability tool. The hosted version handles ingestion at roughly 2M data points per second per tenant.
