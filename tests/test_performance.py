import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from workman_field_tests.core import Endpoint
from workman_field_tests.performance import run_load_level, stream_chat


class StreamingHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        prompt = request["messages"][-1]["content"]
        if "MALFORMED" in prompt:
            events = ["data: {broken}\n\n", "data: [DONE]\n\n"]
        else:
            events = [
                'data: {"choices":[{"delta":{"content":"one"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":" two"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":" three"}}]}\n\n',
                'data: {"choices":[],"usage":{"completion_tokens":3}}\n\n',
                "data: [DONE]\n\n",
            ]
        body = "".join(events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        for event in events:
            self.wfile.write(event.encode())
            self.wfile.flush()
            time.sleep(0.005)

    def log_message(self, *_):
        pass


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), StreamingHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = Endpoint(f"http://127.0.0.1:{self.server.server_port}/v1", "", "fixture")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_streaming_metrics_and_bounded_concurrency(self):
        result = run_load_level(
            endpoint=self.endpoint,
            model="fixture",
            prompt="stream",
            max_tokens=3,
            timeout=2,
            no_think=False,
            concurrency=2,
            request_count=4,
            request_rate=0,
        )
        self.assertEqual(result["success_count"], 4)
        self.assertEqual(len(result["rows"]), 4)
        self.assertGreater(result["aggregate_output_tokens_per_second"], 0)
        self.assertTrue(all(row["ttft_seconds"] is not None for row in result["rows"]))
        self.assertTrue(all(row["tpot_seconds"] is not None for row in result["rows"]))
        self.assertEqual({row["request_id"] for row in result["rows"]}, {0, 1, 2, 3})

    def test_malformed_sse_has_distinct_failure(self):
        started = time.perf_counter()
        result = stream_chat(
            endpoint=self.endpoint,
            model="fixture",
            prompt="MALFORMED",
            max_tokens=3,
            timeout=2,
            no_think=False,
            request_id=0,
            intended_send=started,
            run_started=started,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.failure, "malformed_sse")


if __name__ == "__main__":
    unittest.main()
