import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))
from rails_to_rust.common import Error, BEGIN, END, generated_path, write
from rails_to_rust.inventory import inspect
from rails_to_rust.project import initialize
from rails_to_rust.oracle import capture
from rails_to_rust.generate import records, routes, contract_test
from rails_to_rust.parity import compare, mutation_diff
from rails_to_rust.checks import doctor
from rails_to_rust.benchmark import benchmark


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()


@contextlib.contextmanager
def server(body=b"hello", status=200, location=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            if location:
                self.send_header("Location", location)
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    instance = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=instance.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{instance.server_port}"
    finally:
        instance.shutdown()
        instance.server_close()
        worker.join()


class ToolkitTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / "rails"
        (self.source / "config").mkdir(parents=True)
        (self.source / "app/models").mkdir(parents=True)
        (self.source / "app/controllers").mkdir(parents=True)
        (self.source / "app/views/pages").mkdir(parents=True)
        (self.source / "config/routes.rb").write_text("# fixture routes\n")
        (self.source / "config/database.yml").write_text("development:\n  adapter: mysql2\n  encoding: latin1\n")
        (self.source / "app/models/page.rb").write_text("class Page\n after_commit :index\nend\n")
        (self.source / "app/controllers/pages_controller.rb").write_text("class PagesController\n before_filter :auth\nend\n")
        (self.source / "app/views/pages/show.html.erb").write_text("<h1><%= @page.title %></h1>\n")
        (self.source / "app/views/pages/edit.rjs").write_text("page.replace_html 'title'\n")
        (self.source / ".ruby-version").write_text("2.5.9\n")
        (self.source / "Gemfile.lock").write_text("GEM\n  specs:\n    rails (2.3.18.99)\n")
        git(self.source, "init", "-b", "main")
        git(self.source, "add", ".")
        git(self.source, "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-m", "fixture")
        self.sha = git(self.source, "rev-parse", "HEAD")
        self.port = self.base / "port"
        self.port.mkdir()
        (self.port / "migration.toml").write_text(f'''version = 1
[project]
name = "fixture"
reference_sha = "{self.sha}"
[oracle]
command = []
working_directory = "reference"
[parity]
reference_url = "http://127.0.0.1:1"
candidate_url = "http://127.0.0.1:2"
cases = "parity/cases.json"
reset_command = []
[checks]
rollback = []
''')
        (self.port / "reference").symlink_to(self.source, target_is_directory=True)

    def envelope(self, kind, data):
        path = self.port / "vectors" / (kind + ".json")
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"version": 1, "kind": kind, "reference_sha": self.sha,
                                    "runtime": {"ruby_version": "2.5.9", "rails_version": "2.3.18.99"}, "data": data}))
        return path

    def cases(self, cases, left, right):
        path = self.port / "parity/cases.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({"version": 1, "cases": cases}))
        p = self.port / "migration.toml"
        text = re.sub(r'^reference_url = .*', "reference_url = " + json.dumps(left), p.read_text(), flags=re.M)
        text = re.sub(r'^candidate_url = .*', "candidate_url = " + json.dumps(right), text, flags=re.M)
        p.write_text(text)

    def test_inventory_detects_legacy_formats_and_encoding_without_modification(self):
        before = git(self.source, "status", "--porcelain")
        result = inspect(self.source)
        self.assertEqual(result["rails_version"], "2.3.18.99")
        self.assertEqual(result["database_adapters"], ["mysql2"])
        self.assertEqual(result["database_encodings"], ["latin1"])
        self.assertEqual(result["view_formats"], {".erb": 1, ".rjs": 1})
        self.assertEqual({hint["kind"] for hint in result["review_hints"]}, {"callbacks", "controller_filters"})
        self.assertEqual(before, git(self.source, "status", "--porcelain"))

    def test_init_pins_reference_and_installs_self_contained_tools_and_skills(self):
        destination = self.base / "sample-app-rust"
        result = initialize(self.source, destination)
        self.assertEqual(result["name"], "sample_app")
        self.assertEqual(git(destination / "reference", "rev-parse", "HEAD"), self.sha)
        self.assertEqual(git(self.source, "status", "--porcelain"), "")
        self.assertTrue((destination / ".agents/skills/rails-oracle/SKILL.md").exists())
        self.assertTrue((destination / "reference-tools/export.rb").exists())
        version = subprocess.check_output([sys.executable, str(destination / "bin/rails-to-rust"), "--version"], cwd=destination)
        self.assertEqual(version.strip(), b"0.1.0")
        status = subprocess.run([sys.executable, str(destination / "bin/rails-to-rust"), "doctor"], cwd=destination, capture_output=True)
        self.assertEqual(status.returncode, 1)
        self.assertFalse(json.loads(status.stdout)["ready"])
        with self.assertRaises(Error):
            initialize(self.source, destination)

    def test_generators_cannot_escape_project_or_write_reference(self):
        for path in ["../outside.rs", "reference/owned.rs"]:
            with self.assertRaises(Error):
                generated_path(self.port, path)
        (self.port / "escape").symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(Error):
            generated_path(self.port, "escape/owned.rs")

    def test_outputs_refuse_overwrite_and_are_idempotent(self):
        path = self.port / "test"
        write(path, "one")
        write(path, "one")
        with self.assertRaises(Error):
            write(path, "two")
        self.assertEqual(path.read_text(), "one")
        write(path, "two", force=True)
        self.assertEqual(path.read_text(), "two")

    def test_record_generator_preserves_keys_nullability_unsigned_and_rejects_unknown_types(self):
        self.envelope("schema", [{"name": "people", "primary_key": "uuid", "columns": [
            {"name": "uuid", "type": "uuid", "null": False},
            {"name": "type", "type": "integer", "null": True, "unsigned": True},
            {"name": "balance", "type": "decimal", "null": False}]}])
        result = records(self.port)
        text = Path(result["output"]).read_text()
        self.assertIn("pub uuid: String", text)
        self.assertIn("pub r#type: Option<u64>", text)
        self.assertIn("pub balance: Decimal", text)
        self.assertIn('PRIMARY_KEY: &\'static [&\'static str] = &["uuid"]', text)
        self.envelope("schema", [{"name": "people", "primary_key": None,
                                  "columns": [{"name": "value", "type": "hstore", "null": True}]}])
        with self.assertRaisesRegex(Error, "unsupported type"):
            records(self.port, force=True)
        self.assertEqual(Path(result["output"]).read_text(), text)

    def test_stale_vectors_are_rejected(self):
        path = self.envelope("routes", [{"ordinal": 0, "path": "/"}])
        value = json.loads(path.read_text()); value["reference_sha"] = "old"
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(Error, "SHA"):
            routes(self.port)

    def test_route_order_constraints_and_unicode_are_preserved(self):
        data = [{"ordinal": 0, "name": None, "path": "/:id", "requirements": {"id": {"regexp": "[^/.?]+", "options": 1}}},
                {"ordinal": 1, "name": "cafe", "path": "/café\n", "verb": {"regexp": "GET|HEAD", "options": 0}}]
        self.envelope("routes", data)
        result = routes(self.port)
        self.assertEqual(result["routes"], 2)
        text = Path(result["output"]).read_text()
        self.assertLess(text.index("ordinal: 0, name"), text.index("ordinal: 1, name"))
        self.assertIn("café", text)
        self.assertIn('\\\\"options\\\\":1'.replace('\\\\', '\\'), text)
        data[0]["ordinal"] = 1
        self.envelope("routes", data)
        with self.assertRaisesRegex(Error, "ordinals"):
            routes(self.port, force=True)

    def test_contract_test_requires_expected_values_and_is_not_ignored(self):
        self.envelope("sample", [{"input": 1, "expected": 2}])
        result = contract_test(self.port, "sample", "vectors/sample.json", "crates/compat/tests/sample.rs")
        text = Path(result["output"]).read_text()
        self.assertIn("todo!", text)
        self.assertNotIn("#[ignore", text)
        self.envelope("sample", [{"input": 1}])
        with self.assertRaisesRegex(Error, "expected"):
            contract_test(self.port, "sample", "vectors/sample.json", "bad.rs")

    def test_oracle_accepts_framing_but_rejects_stale_provenance_and_dirty_reference(self):
        payload = {"version": 1, "kind": "runtime", "reference_sha": self.sha,
                   "runtime": {"ruby_version": "2.5.9", "rails_version": "2.3.18.99"}, "data": {"ok": True}}
        script = self.port / "reference-tools/export.rb"; script.parent.mkdir(); script.write_text("# fixture")
        code = 'print(' + repr(BEGIN + '\n' + json.dumps(payload) + '\n' + END) + ')'
        config = self.port / "migration.toml"
        config.write_text(config.read_text().replace("command = []", "command = " + json.dumps([sys.executable, "-c", code]), 1))
        result = capture(self.port, "runtime")
        self.assertEqual(result["reference_sha"], self.sha)
        (self.source / "config/routes.rb").write_text("changed\n")
        with self.assertRaisesRegex(Error, "dirty"):
            capture(self.port, "runtime", force=True)

    def test_empty_http_inventory_fails(self):
        self.cases([], "http://127.0.0.1:1", "http://127.0.0.1:2")
        with self.assertRaisesRegex(Error, "nonempty"):
            compare(self.port)

    def test_matching_error_pages_do_not_pass_expected_success(self):
        with server(status=404) as left, server(status=404) as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            result = compare(self.port)
            self.assertFalse(result["passed"])
            self.assertEqual(len(result["cases"][0]["problems"]), 2)

    def test_matching_success_passes_and_body_mismatch_fails(self):
        with server() as left, server() as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            self.assertTrue(compare(self.port)["passed"])
        with server(body=b"one") as left, server(body=b"two") as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            self.assertFalse(compare(self.port, force=True)["passed"])

    def test_redirects_are_compared_without_following(self):
        with server(status=302, location="/login") as left, server(status=302, location="/login") as right:
            self.cases([{"id": "redirect", "path": "/", "expected_status": 302}], left, right)
            self.assertTrue(compare(self.port)["passed"])

    def test_json_ignores_object_order_but_not_record_identity(self):
        with server(body=b'{"a":1,"id":5}') as left, server(body=b'{"id":6,"a":1}') as right:
            self.cases([{"id": "record", "path": "/", "expected_status": 200, "comparison": "json"}], left, right)
            self.assertFalse(compare(self.port)["passed"])

    def test_mutations_require_reset_before_any_request(self):
        self.cases([{"id": "write", "path": "/", "method": "POST", "expected_status": 200}],
                   "http://127.0.0.1:1", "http://127.0.0.1:2")
        with self.assertRaisesRegex(Error, "command array"):
            compare(self.port)

    def test_mutation_diff_compares_equal_baselines_and_changed_state(self):
        state = self.port / "state.json"
        reset = [sys.executable, "-c", f"from pathlib import Path; Path({str(state)!r}).write_text('{{\"rows\":[]}}')"]
        snapshot = [sys.executable, "-c", f"from pathlib import Path; print(Path({str(state)!r}).read_text())"]
        action = [sys.executable, "-c", f"from pathlib import Path; Path({str(state)!r}).write_text('{{\"rows\":[1]}}')"]
        config = self.port / "migration.toml"
        config.write_text(config.read_text() + "\n[mutations]\n" + '\n'.join(
            key + " = " + json.dumps(value) for key, value in [("reset_command", reset), ("snapshot_command", snapshot),
                                                               ("reference_command", action), ("candidate_command", action)]))
        self.assertTrue(mutation_diff(self.port)["passed"])

    def test_benchmark_balances_order_and_rejects_different_output(self):
        argv = [sys.executable, "-c", "print('same')"]
        result = benchmark(self.port, argv, argv, rounds=2, compare_output=True)
        self.assertEqual([row["order"][0] for row in result["rounds"]["before"]], ["after", "before"])
        self.assertEqual(len(result["rounds"]["before"]), 2)
        with self.assertRaisesRegex(Error, "stdout differs"):
            benchmark(self.port, argv, [sys.executable, "-c", "print('different')"], rounds=2, compare_output=True,
                      output="bench/results/invalid.json")
        self.assertFalse((self.port / "bench/results/invalid.json").exists())

    def test_record_table_selection_is_explicit_and_unknown_selection_fails(self):
        self.envelope("schema", [
            {"name": "users", "primary_key": "id", "columns": [{"name": "id", "type": "integer", "null": False}]},
            {"name": "search_internal", "primary_key": None, "columns": [{"name": "value", "type": "custom", "null": True}]}])
        result = records(self.port, tables=["users"])
        self.assertEqual(result["records"], 1)
        self.assertNotIn("search_internal", Path(result["output"]).read_text())
        with self.assertRaisesRegex(Error, "unknown selected"):
            records(self.port, tables=["invented"], force=True)

    def test_normalizations_need_reasons_and_cannot_implicitly_change_bytes(self):
        self.cases([{"id": "masked", "path": "/", "expected_status": 200,
                     "normalizations": [{"pattern": "token", "replacement": "fixed", "reason": "random token"}]}],
                   "http://127.0.0.1:1", "http://127.0.0.1:2")
        with self.assertRaisesRegex(Error, "explicit text"):
            compare(self.port)

    def test_response_size_cap_fails_instead_of_comparing_truncated_bodies(self):
        with server(body=b"too long") as left, server(body=b"too long") as right:
            self.cases([{"id": "large", "path": "/", "expected_status": 200, "max_body_bytes": 2}], left, right)
            with self.assertRaisesRegex(Error, "exceeds max_body_bytes"):
                compare(self.port)

    def test_json_object_order_can_match(self):
        with server(body=b'{"a":1,"b":2}') as left, server(body=b'{"b":2,"a":1}') as right:
            self.cases([{"id": "object", "path": "/", "expected_status": 200, "comparison": "json"}], left, right)
            self.assertTrue(compare(self.port)["passed"])

    def test_empty_mutation_snapshots_fail_before_action(self):
        marker = self.port / "action-ran"
        reset = [sys.executable, "-c", "pass"]
        snapshot = [sys.executable, "-c", "print('{}')"]
        action = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"]
        config = self.port / "migration.toml"
        config.write_text(config.read_text() + "\n[mutations]\n" + '\n'.join(
            key + " = " + json.dumps(value) for key, value in [("reset_command", reset), ("snapshot_command", snapshot),
                                                               ("reference_command", action), ("candidate_command", action)]))
        with self.assertRaisesRegex(Error, "nonempty JSON"):
            mutation_diff(self.port)
        self.assertFalse(marker.exists())

    def test_failing_benchmark_command_never_produces_a_speedup_artifact(self):
        with self.assertRaisesRegex(Error, "status 3"):
            benchmark(self.port, [sys.executable, "-c", "print('ok')"], [sys.executable, "-c", "raise SystemExit(3)"],
                      rounds=2, output="bench/results/failed.json")
        self.assertFalse((self.port / "bench/results/failed.json").exists())

    def test_oracle_that_changes_reference_cannot_write_evidence(self):
        payload = {"version": 1, "kind": "runtime", "reference_sha": self.sha,
                   "runtime": {"ruby_version": "2.5.9", "rails_version": "2.3.18"}, "data": {"ok": True}}
        script = self.port / "reference-tools/export.rb"; script.parent.mkdir(); script.write_text("# fixture")
        code = f"from pathlib import Path; Path({str(self.source / 'config/routes.rb')!r}).write_text('changed')\n"
        code += "print(" + repr(BEGIN + '\n' + json.dumps(payload) + '\n' + END) + ")"
        config = self.port / "migration.toml"
        config.write_text(config.read_text().replace("command = []", "command = " + json.dumps([sys.executable, "-c", code]), 1))
        with self.assertRaisesRegex(Error, "dirty"):
            capture(self.port, "runtime")
        self.assertFalse((self.port / "vectors/runtime.json").exists())


if __name__ == "__main__":
    unittest.main()
