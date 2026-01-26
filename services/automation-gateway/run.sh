#!/usr/bin/env bash
set -euo pipefail

# Service identity (how it shows in Tempo)
export OTEL_SERVICE_NAME="${OTEL_SERVICE_NAME:-automation-gateway}"

# Export traces only
export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"
export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-none}"
export OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-none}"

# Send traces to Tempo (cross-namespace DNS)
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="${OTEL_EXPORTER_OTLP_TRACES_ENDPOINT:-http://tempo.monitoring:4318/v1/traces}"
export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}"

# Sampling
export OTEL_TRACES_SAMPLER="${OTEL_TRACES_SAMPLER:-parentbased_always_on}"

# Optional: log correlation
export OTEL_PYTHON_LOG_CORRELATION="${OTEL_PYTHON_LOG_CORRELATION:-true}"

exec opentelemetry-instrument uvicorn app.main:app --host 0.0.0.0 --port 8000
