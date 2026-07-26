import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


def setup_opentelemetry() -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.debug("OTEL_EXPORTER_OTLP_ENDPOINT not set, skipping OpenTelemetry setup")
        return

    try:
        from opentelemetry import trace  # noqa: I001
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # noqa: I001
        from opentelemetry.sdk.resources import Resource  # noqa: I001
        from opentelemetry.sdk.trace import TracerProvider  # noqa: I001
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: I001
    except ImportError:
        logger.warning(
            "OpenTelemetry packages not installed; install opentelemetry-api and "
            "opentelemetry-sdk to enable OTLP tracing"
        )
        return

    try:
        resource = Resource.create({"service.name": settings.app_name})

        provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(span_exporter))

        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry configured with endpoint %s", endpoint)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to configure OpenTelemetry: %s", exc)
