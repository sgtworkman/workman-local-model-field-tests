import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from workman_field_tests.core import Endpoint, run_battery


class Handler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        self.__class__.requests.append(request)
        prompt = request["messages"][-1]["content"]
        output = "FIELD_TEST_OK" if "FIELD_TEST_OK" in prompt else "ok"
        body = json.dumps({
            "model": request["model"],
            "choices": [{"message": {"content": output}}],
            "usage": {"completion_tokens": 3},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class IntegrationTests(unittest.TestCase):
    def test_run_battery(self):
        Handler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = run_battery(
                endpoint=Endpoint(f"http://127.0.0.1:{server.server_port}/v1", "", "test"),
                model="fixture",
                scenarios=[{"id": "exact", "prompt": "Return FIELD_TEST_OK", "rule": {"type": "exact", "value": "FIELD_TEST_OK"}}],
                repeats=2,
                timeout=2,
                max_tokens=10,
                hardware="fixture",
                runtime="fixture",
                quantization="fixture",
                no_think=True,
            )
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(result["summary"]["passed"], 2)
        self.assertEqual(result["summary"]["total"], 2)
        self.assertIn("aggregate_request_tokens_per_second", result["summary"])
        self.assertNotIn("base_url", result)

    def test_no_think_controls_are_explicit(self):
        Handler.requests = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            run_battery(
                endpoint=Endpoint(f"http://127.0.0.1:{server.server_port}/v1", "", "test"),
                model="fixture",
                scenarios=[{"id": "exact", "prompt": "Return FIELD_TEST_OK", "rule": {"type": "exact", "value": "FIELD_TEST_OK"}}],
                repeats=1,
                timeout=2,
                max_tokens=10,
                hardware="fixture",
                runtime="fixture",
                quantization="fixture",
                no_think=False,
            )
        finally:
            server.shutdown()
            server.server_close()
        request = Handler.requests[-1]
        self.assertNotIn("reasoning_effort", request)
        self.assertNotIn("include_reasoning", request)
        self.assertNotIn("chat_template_kwargs", request)


if __name__ == "__main__":
    unittest.main()
