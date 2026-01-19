#!/bin/bash

# OpenTelemetry Configuration via Environment Variables
export OTEL_SERVICE_NAME="fastapi-app"
export OTEL_TRACES_EXPORTER="otlp"
export OTEL_METRICS_EXPORTER="none"  # Using Prometheus instead
export OTEL_LOGS_EXPORTER="none"     # Logs go to stdout, collected by Loki
export OTEL_EXPORTER_OTLP_ENDPOINT="http://tempo:4317"
export OTEL_EXPORTER_OTLP_PROTOCOL="grpc"

# Enable trace context injection into logs
export OTEL_PYTHON_LOG_CORRELATION="true"

# Optional: Set sampling (1.0 = 100% of traces)
export OTEL_TRACES_SAMPLER="parentbased_always_on"

# Run with auto-instrumentation
exec opentelemetry-instrument uvicorn main:app --host 0.0.0.0 --port 8000
