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
        if "TIMEOUT" in prompt:
            time.sleep(0.2)
            events = ["data: [DONE]\n\n"]
        elif "MALFORMED" in prompt:
            events = ["data: {broken}\n\n", "data: [DONE]\n\n"]
        elif "MISSING_USAGE" in prompt:
            events = ['data: {"choices":[{"delta":{"content":"one"}}]}\n\n', "data: [DONE]\n\n"]
        elif "REASONING_ONLY" in prompt:
            events = ['data: {"choices":[{"delta":{"reasoning_content":"secret"}}],"usage":{"completion_tokens":1}}\n\n', "data: [DONE]\n\n"]
        elif "INCOMPLETE" in prompt:
            events = ['data: {"choices":[{"delta":{"content":"one"}}],"usage":{"completion_tokens":1}}\n\n']
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
        try:
            for event in events:
                self.wfile.write(event.encode())
                self.wfile.flush()
                time.sleep(0.005)
        except (BrokenPipeError, ConnectionResetError):
            # Expected when the timeout fixture closes its client connection.
            pass

    def log_message(self, *_):
        pass


class LoadTestHTTPServer(ThreadingHTTPServer):
    # The stdlib default backlog is only 5, which can reject connections during
    # the intentional 24-request burst before worker threads accept them.
    request_queue_size = 64


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.server = LoadTestHTTPServer(("127.0.0.1", 0), StreamingHandler)
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

    def measurement(self, prompt, timeout=2):
        started = time.perf_counter()
        return stream_chat(
            endpoint=self.endpoint,
            model="fixture",
            prompt=prompt,
            max_tokens=3,
            timeout=timeout,
            no_think=False,
            request_id=0,
            intended_send=started,
            run_started=started,
        )

    def test_stream_failure_taxonomy(self):
        cases = {
            "MISSING_USAGE": "missing_usage",
            "REASONING_ONLY": "reasoning_leak",
            "INCOMPLETE": "incomplete_stream",
            "TIMEOUT": "timeout",
        }
        for prompt, expected in cases.items():
            with self.subTest(prompt=prompt):
                result = self.measurement(prompt, timeout=0.05 if prompt == "TIMEOUT" else 2)
                self.assertFalse(result.success)
                self.assertEqual(result.failure, expected)

    def test_concurrency_request_accounting_at_supported_levels(self):
        for concurrency in (2, 8, 24):
            with self.subTest(concurrency=concurrency):
                result = run_load_level(
                    endpoint=self.endpoint,
                    model="fixture",
                    prompt="stream",
                    max_tokens=3,
                    timeout=3,
                    no_think=False,
                    concurrency=concurrency,
                    request_count=concurrency,
                    request_rate=0,
                )
                self.assertEqual(result["success_count"], concurrency)
                self.assertEqual(len(result["rows"]), concurrency)
                self.assertEqual({row["request_id"] for row in result["rows"]}, set(range(concurrency)))


if __name__ == "__main__":
    unittest.main()
