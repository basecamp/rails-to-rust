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
from rails_to_rust.checks import doctor, verify
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

    def test_ruby_exporter_bypasses_string_subclass_json_and_records_patchlevel(self):
        # Exercise the real Ruby exporter, including its final JSON framing. The
        # subclass models Rails SafeBuffer's to_json override rather than copying
        # the exporter implementation into a Python assertion.
        ruby = os.environ.get("RAILS_TO_RUST_TEST_RUBY", "ruby")
        program = r"""# encoding: UTF-8
require 'json'
class UnsafeJsonString < String
  def to_json(*args); '"corrupted"'; end
end
module Rails
  module VERSION; STRING = '2.3.fixture'; end
end
module ActiveRecord
  class Base
    def self.connection; self; end
    def self.adapter_name; 'Fixture'; end
  end
end
# Gem metadata is part of the export and must preserve the original bytes.
spec = Struct.new(:version, :full_gem_path).new('1', UnsafeJsonString.new("/private/home/bundle/café 日本 🍣-deadbeef"))
Gem.loaded_specs['fixture'] = spec
"""
        script = self.base / "exporter-test.rb"
        script.write_text(program + (ROOT / "templates/reference-tools/export.rb").read_text())
        env = dict(os.environ, RAILS_TO_RUST_EXPORT="runtime", RAILS_TO_RUST_REFERENCE_SHA=self.sha)
        result = subprocess.run([ruby, str(script)], env=env, capture_output=True, check=True)
        output = result.stdout.decode()
        payload = json.loads(output.split(BEGIN, 1)[1].split(END, 1)[0])
        self.assertEqual(payload["data"]["gems"]["fixture"]["source"], "café 日本 🍣-deadbeef")
        self.assertEqual(payload["runtime"]["gems"]["fixture"]["source"], "café 日本 🍣-deadbeef")
        self.assertNotIn("/private/home", output)
        self.assertIsInstance(payload["runtime"]["ruby_patchlevel"], int)
        self.assertEqual(payload["reference_sha"], self.sha)

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
        self.configure_mutations()
        self.assertTrue(mutation_diff(self.port)["passed"])
        for side in ["reference", "candidate"]:
            self.assertEqual(json.loads((self.port / (side + ".json")).read_text()), {"rows": [1]})

    def test_mutation_diff_rejects_matching_noop_runners(self):
        self.configure_mutations()
        path = self.port / "migration.toml"
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            if line.startswith(("reference_command =", "candidate_command =")):
                name = line.split(" =", 1)[0]
                lines[index] = name + " = " + json.dumps([sys.executable, "-c", "pass"])
        path.write_text("\n".join(lines) + "\n")
        result = mutation_diff(self.port)
        self.assertFalse(result["passed"])
        self.assertEqual(result["changed"], {"reference": False, "candidate": False})
        self.assertEqual(len(result["problems"]), 2)
        path.write_text(path.read_text() + "expect_change = false\n")
        self.assertTrue(mutation_diff(self.port, force=True)["passed"])

    def configure_mutations(self, *, unequal_baseline=False, unequal_result=False):
        reset_code = "from pathlib import Path; import json,sys; "
        reset_code += "rows = [9] if sys.argv[1] == 'candidate' else []; " if unequal_baseline else "rows = []; "
        reset_code += "Path(sys.argv[1] + '.json').write_text(json.dumps({'rows': rows}))"
        snapshot_code = "from pathlib import Path; import sys; print(Path(sys.argv[1] + '.json').read_text())"
        action_code = "from pathlib import Path; import json,sys; Path(sys.argv[1] + '.ran').touch(); "
        action_code += "rows = [2] if sys.argv[1] == 'candidate' else [1]; " if unequal_result else "rows = [1]; "
        action_code += "Path(sys.argv[1] + '.json').write_text(json.dumps({'rows': rows}))"
        commands = {"reset_command": [sys.executable, "-c", reset_code, "{side}"],
                    "snapshot_command": [sys.executable, "-c", snapshot_code, "{side}"],
                    "reference_command": [sys.executable, "-c", action_code, "reference"],
                    "candidate_command": [sys.executable, "-c", action_code, "candidate"]}
        path = self.port / "migration.toml"
        path.write_text(path.read_text() + "\n[mutations]\n" + "\n".join(
            name + " = " + json.dumps(argv) for name, argv in commands.items()))

    def configure_verification(self, *, status="pending", mutations="not-applicable"):
        path = self.port / "migration.toml"
        text = path.read_text().replace("command = []", "command = " + json.dumps([sys.executable]), 1)
        gates = []
        for name in ["format", "lint", "test"]:
            code = "from pathlib import Path; Path(" + repr(name + ".ran") + ").touch()"
            gates.append(name + " = " + json.dumps([sys.executable, "-c", code]))
        path.write_text(text + "\n" + "\n".join(gates) + "\n")
        ledger = {"version": 1, "reference_sha": self.sha, "contracts": [
            {"id": "data", "status": status, "evidence": ["parity/results/evidence.json"]},
            {"id": "mutations", "status": mutations, "reason": "fixture is read-only",
             "evidence": ["parity/results/evidence.json"]}]}
        write(self.port / "plans/contracts.json", json.dumps(ledger))
        write(self.port / "parity/results/evidence.json", json.dumps({"reference_sha": self.sha, "passed": True}))

    def test_unequal_mutation_baselines_run_neither_action(self):
        self.configure_mutations(unequal_baseline=True)
        with self.assertRaisesRegex(Error, "neither action"):
            mutation_diff(self.port)
        self.assertFalse((self.port / "reference.ran").exists())
        self.assertFalse((self.port / "candidate.ran").exists())
        self.assertFalse((self.port / "parity/results/mutation.json").exists())

    def test_partial_verify_runs_gates_while_complete_verify_refuses_pending_contracts(self):
        self.configure_verification()
        with server() as left, server() as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            with self.assertRaisesRegex(Error, "not verified"):
                verify(self.port)
            self.assertFalse((self.port / "test.ran").exists())
            result = verify(self.port, partial=True)
        self.assertTrue(result["passed"])
        self.assertEqual(result["scope"], "partial")
        self.assertEqual([row["check"] for row in result["checks"]], ["format", "lint", "test", "http-parity"])
        self.assertTrue(all((self.port / (name + ".ran")).exists() for name in ["format", "lint", "test"]))

    def test_verify_identifies_failed_gate_without_exposing_captured_output(self):
        self.configure_verification()
        path = self.port / "migration.toml"
        text = path.read_text()
        text = re.sub(r'^format = .*', "format = " + json.dumps(
            [sys.executable, "-c", "print('private-boot-log'); raise SystemExit(7)"]), text, flags=re.M)
        path.write_text(text)
        self.cases([{"id": "home", "path": "/", "expected_status": 200}],
                   "http://127.0.0.1:1", "http://127.0.0.1:2")
        with self.assertRaisesRegex(Error, "format gate failed: .* exited with status 7") as error:
            verify(self.port, partial=True)
        self.assertNotIn("private-boot-log", str(error.exception))
        self.assertFalse((self.port / "test.ran").exists())

    def test_verified_evidence_rejects_failed_stale_and_invalid_json(self):
        self.configure_verification(status="verified")
        path = self.port / "parity/results/evidence.json"
        with server() as left, server() as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            for value in [{"reference_sha": self.sha, "passed": False},
                          {"reference_sha": "old", "passed": True},
                          {"reference_sha": self.sha, "ready": False},
                          {"reference_sha": self.sha, "passed": "true"}, []]:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value))
                    with self.assertRaisesRegex(Error, "evidence"):
                        verify(self.port, partial=True)
                    self.assertFalse((self.port / "test.ran").exists())
            path.write_text("not JSON")
            with self.assertRaisesRegex(Error, "invalid JSON"):
                verify(self.port, partial=True)
            path.write_text(json.dumps({"reference_sha": self.sha, "passed": True}))
            self.assertTrue(verify(self.port, partial=True)["passed"])

    def test_complete_verify_runs_mutations_and_propagates_state_mismatch(self):
        self.configure_verification(status="verified", mutations="verified")
        self.configure_mutations(unequal_result=True)
        path = self.port / "migration.toml"
        path.write_text(path.read_text().replace("rollback = []", "rollback = " + json.dumps(
            [sys.executable, "-c", "from pathlib import Path; Path('rollback.ran').touch()"])))
        with server() as left, server() as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            result = verify(self.port)
        self.assertFalse(result["passed"])
        self.assertEqual(result["scope"], "complete")
        self.assertFalse(result["checks"][-1]["passed"])
        self.assertEqual(result["checks"][-1]["check"], "mutation-parity")
        self.assertTrue((self.port / "rollback.ran").exists())
        self.assertFalse(json.loads((self.port / "parity/results/verification-mutation.json").read_text())["passed"])

    def test_partial_verify_requires_mutation_adapters_for_implemented_writes(self):
        self.configure_verification(mutations="implemented")
        with server() as left, server() as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            with self.assertRaisesRegex(Error, "command array"):
                verify(self.port, partial=True)
            self.assertFalse((self.port / "test.ran").exists())

    def test_complete_readonly_verify_requires_rollback_and_can_pass(self):
        self.configure_verification(status="verified")
        with server() as left, server() as right:
            self.cases([{"id": "home", "path": "/", "expected_status": 200}], left, right)
            with self.assertRaisesRegex(Error, "command array"):
                verify(self.port)
            path = self.port / "migration.toml"
            path.write_text(path.read_text().replace("rollback = []", "rollback = " + json.dumps(
                [sys.executable, "-c", "from pathlib import Path; Path('rollback.ran').touch()"])))
            result = verify(self.port)
        self.assertTrue(result["passed"])
        self.assertEqual(result["scope"], "complete")
        self.assertTrue((self.port / "rollback.ran").exists())
        self.assertNotIn("mutation-parity", [row["check"] for row in result["checks"]])

    def test_partial_write_inventory_requires_state_comparison_even_if_ledger_says_readonly(self):
        self.configure_verification()
        self.cases([{"id": "write", "path": "/", "method": "POST", "expected_status": 200}],
                   "http://127.0.0.1:1", "http://127.0.0.1:2")
        with self.assertRaisesRegex(Error, "command array"):
            verify(self.port, partial=True)
        self.assertFalse((self.port / "test.ran").exists())

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
