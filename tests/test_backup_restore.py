#!/usr/bin/env python3
"""Backup and restore contract of the module, with a fake podman.

Scripts and the include list are real; podman records its calls and writes
the dump the test asks for. This proves the control flow (what is published,
what fails, what is removed), not a real PostgreSQL restore.
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGEROOT = ROOT / "imageroot"
sys.dont_write_bytecode = True

FAKE_PODMAN = """#!/bin/bash
echo "$@" >> "$FAKE_LOG"
case "$1" in
  exec) [[ -n "${FAKE_DUMP_FAIL:-}" ]] && exit 3; printf '%s' "${FAKE_DUMP_BODY-PGDMP}" ;;
  run) [[ -n "${FAKE_RESTORE_FAIL:-}" && "$*" == *docker-entrypoint-initdb.d* ]] && exit 4; cat >/dev/null 2>&1 || true ;;
esac
exit 0
"""


class Env:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "state"
        self.home.mkdir()
        bindir = Path(self.tmp.name) / "bin"
        bindir.mkdir()
        podman = bindir / "podman"
        podman.write_text(FAKE_PODMAN)
        podman.chmod(0o755)
        self.log = Path(self.tmp.name) / "podman.log"
        self.log.touch()
        self.env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}",
                        FAKE_LOG=str(self.log), POSTGRES_IMAGE="docker.io/library/postgres:test")

    def run(self, script, **extra):
        env = dict(self.env, **extra)
        return subprocess.run(["bash", str(script)], cwd=self.home, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def calls(self):
        return self.log.read_text().splitlines()


class DumpAndCleanup(unittest.TestCase):
    def setUp(self):
        self.e = Env()

    def tearDown(self):
        self.e.tmp.cleanup()

    def dump(self, **extra):
        return self.e.run(IMAGEROOT / "bin/module-dump-state", IDP_HOSTNAME="sso.example.org", **extra)

    def test_dump_is_published_private(self):
        result = self.dump()
        self.assertEqual(result.returncode, 0, result.stderr)
        dump = self.e.home / "idp.pg_dump"
        self.assertEqual(dump.read_text(), "PGDMP")
        self.assertEqual(stat.S_IMODE(dump.stat().st_mode), 0o600)
        self.assertIn("exec postgres", self.e.calls()[0])
        self.assertFalse((self.e.home / "idp.pg_dump.tmp").exists())

    def test_failed_dump_fails_and_removes_the_old_dump(self):
        (self.e.home / "idp.pg_dump").write_text("OLD")
        result = self.dump(FAKE_DUMP_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.e.home / "idp.pg_dump").exists(), "stale dump would pass as fresh")
        self.assertFalse((self.e.home / "idp.pg_dump.tmp").exists())

    def test_empty_dump_is_refused(self):
        result = self.dump(FAKE_DUMP_BODY="")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.e.home / "idp.pg_dump").exists())

    def test_unconfigured_module_skips_without_calling_podman(self):
        (self.e.home / "idp.pg_dump").write_text("OLD")
        result = self.e.run(IMAGEROOT / "bin/module-dump-state")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.e.calls(), [])
        self.assertFalse((self.e.home / "idp.pg_dump").exists())

    def test_cleanup_removes_what_dump_creates(self):
        self.assertEqual(self.dump().returncode, 0)
        (self.e.home / "idp.pg_dump.tmp").write_text("x")
        self.assertEqual(self.e.run(IMAGEROOT / "bin/module-cleanup-state").returncode, 0)
        self.assertEqual(sorted(p.name for p in self.e.home.iterdir()), [])
        # repeatable
        self.assertEqual(self.e.run(IMAGEROOT / "bin/module-cleanup-state").returncode, 0)


class IncludeFile(unittest.TestCase):
    def test_include_contract(self):
        lines = [l.strip() for l in (IMAGEROOT / "etc/state-include.conf").read_text().splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
        self.assertEqual(sorted(lines), ["state/idp.pg_dump", "state/passwords.env"])

    def test_dump_name_matches_include_and_restore(self):
        for name in ("bin/module-dump-state", "bin/module-cleanup-state", "actions/restore-module/40restore_database"):
            self.assertIn("idp.pg_dump", (IMAGEROOT / name).read_text(), name)

    def test_hooks_are_executable(self):
        for p in list((IMAGEROOT / "bin").iterdir()) + list((IMAGEROOT / "actions/restore-module").iterdir()):
            self.assertTrue(p.stat().st_mode & stat.S_IXUSR, f"{p} is not executable")


class RestoreDatabase(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        (self.e.home / "passwords.env").write_text("POSTGRES_PASSWORD=x\nKC_DB_PASSWORD=x\n")
        (self.e.home / "idp.pg_dump").write_text("PGDMP")

    def tearDown(self):
        self.e.tmp.cleanup()

    def restore(self, **extra):
        return self.e.run(IMAGEROOT / "actions/restore-module/40restore_database",
                          IDP_HOSTNAME="sso.example.org", **extra)

    def test_restore_validates_then_recreates_the_volume_then_loads(self):
        result = self.restore()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.e.calls()
        self.assertIn("pg_restore --list", calls[0])
        self.assertEqual(calls[1], "volume rm --force pgdata")
        self.assertIn("docker-entrypoint-initdb.d", calls[2])
        self.assertIn("--volume=pgdata:/var/lib/postgresql", calls[2])
        self.assertIn("--network=none", calls[2])
        self.assertFalse((self.e.home / "idp.pg_dump").exists())
        self.assertFalse((self.e.home / "restore").exists())

    def test_missing_dump_fails_before_touching_the_volume(self):
        (self.e.home / "idp.pg_dump").unlink()
        result = self.restore()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.e.calls(), [])

    def test_missing_passwords_fails_before_touching_the_volume(self):
        (self.e.home / "passwords.env").unlink()
        self.assertNotEqual(self.restore().returncode, 0)
        self.assertEqual(self.e.calls(), [])

    def test_failed_load_fails_the_action_and_keeps_the_dump(self):
        result = self.restore(FAKE_RESTORE_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.e.home / "idp.pg_dump").exists())

    def test_unconfigured_source_restores_nothing(self):
        result = self.e.run(IMAGEROOT / "actions/restore-module/40restore_database")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.e.calls(), [])


def run_python_action(script, request, tasks_result=0):
    """Run a restore-module python step with a fake agent module."""
    fake = f"""
import sys, types, json
calls = {{"env": {{}}, "tasks": []}}
agent = types.ModuleType("agent")
agent.set_env = lambda k, v: calls["env"].__setitem__(k, v)
agent.dump_env = lambda: None
def assert_exp(cond, msg):
    if not cond:
        print(msg, file=sys.stderr); sys.exit(1)
agent.assert_exp = assert_exp
tasks = types.ModuleType("agent.tasks")
tasks.run = lambda **kw: (calls["tasks"].append(kw), {{"exit_code": {tasks_result}}})[1]
agent.tasks = tasks
sys.modules["agent"] = agent
sys.modules["agent.tasks"] = tasks
sys.path.insert(0, {str(IMAGEROOT / "pypkg")!r})
import os
os.environ["AGENT_ID"] = "module/idp1"
sys.stdin = open({str(request)!r})
try:
    exec(compile(open({str(script)!r}).read(), "step", "exec"), {{"__name__": "__main__"}})
except SystemExit as e:
    code = e.code or 0
else:
    code = 0
print(json.dumps({{"calls": calls, "code": code}}))
"""
    out = subprocess.run([sys.executable, "-B", "-c", fake], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return json.loads(out.stdout.strip().splitlines()[-1]), out


class RestorePythonSteps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.req = Path(self.tmp.name) / "req.json"

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, environment):
        self.req.write_text(json.dumps({"environment": environment}))

    def test_copyenv_restores_only_the_known_settings(self):
        self.write({"IDP_HOSTNAME": "sso.example.org", "IDP_LETS_ENCRYPT": "1", "IDP_RESTRICT_ADMIN_CONSOLE": "0",
                    "TCP_PORT": "20001", "REDIS_PASSWORD": "secret"})
        res, _ = run_python_action(IMAGEROOT / "actions/restore-module/06copyenv", self.req)
        self.assertEqual(res["calls"]["env"], {"IDP_HOSTNAME": "sso.example.org", "IDP_LETS_ENCRYPT": "1",
                                               "IDP_RESTRICT_ADMIN_CONSOLE": "0"})

    def test_configure_receives_the_restored_policy(self):
        self.write({"IDP_HOSTNAME": "sso.example.org", "IDP_LETS_ENCRYPT": "1", "IDP_STRICT_CLIENT_URIS": "0"})
        res, _ = run_python_action(IMAGEROOT / "actions/restore-module/50configure", self.req)
        task = res["calls"]["tasks"][0]
        self.assertEqual(task["action"], "configure-module")
        self.assertEqual(task["data"], {"host": "sso.example.org", "lets_encrypt": True, "strict_client_uris": False})

    def test_old_backup_without_lets_encrypt_flag_restores_without_it(self):
        self.write({"IDP_HOSTNAME": "sso.example.org"})
        res, _ = run_python_action(IMAGEROOT / "actions/restore-module/50configure", self.req)
        self.assertIs(res["calls"]["tasks"][0]["data"]["lets_encrypt"], False)

    def test_failed_configure_fails_the_restore(self):
        self.write({"IDP_HOSTNAME": "sso.example.org"})
        res, _ = run_python_action(IMAGEROOT / "actions/restore-module/50configure", self.req, tasks_result=1)
        self.assertEqual(res["code"], 1)

    def test_unconfigured_source_does_not_configure(self):
        self.write({})
        res, _ = run_python_action(IMAGEROOT / "actions/restore-module/50configure", self.req)
        self.assertEqual(res["calls"]["tasks"], [])


if __name__ == "__main__":
    unittest.main()
