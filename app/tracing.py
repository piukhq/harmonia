import contextlib

import opentracing
from opentracing.ext import tags as ot_tags


class TraceManager:
    def __init__(self, tracer: opentracing.Tracer, component: str):
        self._tracer = tracer
        self.component = component

    @contextlib.contextmanager
    def start_scope_from_text_map(self, operation_name: str, headers: dict[str, str]):
        # Extract any trace ids from headers exported with TEXT_MAP
        try:
            span_ctx = self._tracer.extract(opentracing.Format.HTTP_HEADERS, headers)
            scope = self._tracer.start_active_span(operation_name, child_of=span_ctx)
        except (opentracing.InvalidCarrierException, opentracing.SpanContextCorruptedException):
            scope = self._tracer.start_active_span(operation_name)

        scope.span.set_tag(ot_tags.COMPONENT, self.component)

        try:
            yield scope
        except Exception as err:
            scope.span.set_tag(ot_tags.ERROR, str(err))
            raise  # Reraise else the context manager will eat the exception
        finally:
            scope.close()
