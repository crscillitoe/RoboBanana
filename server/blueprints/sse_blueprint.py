import logging
from flask_sse import ServerSentEventsBlueprint
from quart import current_app, stream_with_context, request

LOG = logging.getLogger(__name__)


class SSEBlueprint(ServerSentEventsBlueprint):
    def stream(self):
        """
        A view function that streams server-sent events. Ignores any
        :mailheader:`Last-Event-ID` headers in the HTTP request.
        Use a "channel" query parameter to stream events from a different
        channel than the default channel (which is "sse").
        """
        LOG.debug("Stream triggered, setting nginx headers")
        channel = request.args.get("channel") or "sse"

        @stream_with_context
        def generator():
            for message in self.messages(channel=channel):
                yield str(message)

        return current_app.response_class(
            generator(),
            mimetype="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
            },
        )


sse = SSEBlueprint("sse", __name__)

"""
An instance of :class:`SSEBlueprint`
that hooks up the :meth:`~flask_sse.ServerSentEventsBlueprint.stream`
method as a view function at the root of the blueprint. If you don't
want to customize this blueprint at all, you can simply import and
use this instance in your application.
"""
sse.add_url_rule(rule="", endpoint="stream", view_func=sse.stream)
