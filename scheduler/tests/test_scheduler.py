"""无需 Condor 的行为验证；不能替代真实调度和认证验证。"""

import argparse
from contextlib import redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCHEDULER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCHEDULER / "scripts"))
from common import ROOT, RUNTIME, load_config, runtime_path
from deploy_cluster import check_existing_paths, prepare_paths, render, start_node
import deploy_cluster
import manage_data
import submit_job
from job_runner import execute, unpack
from submit_job import make_bundle, quote, submit_text


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        RUNTIME.mkdir(exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=RUNTIME)
        self.base = Path(self.tmp.name)
        self.config = load_config()

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, policy="summary", code=0):
        program = self.base / "task.py"
        program.write_text("#!/usr/bin/env python3\n"
                           "import json, sys\nfrom pathlib import Path\n"
                           "assert Path('inputs/input.txt').read_text() == 'hello'\n"
                           "Path('results/payload.bin').write_bytes(b'x' * 2097152)\n"
                           "Path('results/summary.json').write_text('{\"input_ok\": true}')\n"
                           "Path('results/oversize.txt').write_bytes(b'x' * 1048577)\n"
                           "print('log-line')\nprint('error-line', file=sys.stderr)\n"
                           f"sys.exit({code})\n")
        program.chmod(0o755)
        data = self.base / "input.txt"
        data.write_text("hello")
        return argparse.Namespace(executable=str(program), input=[str(data)], env=[], policy=policy,
                                  summary=["results/summary.json", "results/oversize.txt"], arguments=[],
                                  cpus=1, gpus=0, memory="128MB", disk="64MB", node=None, bundle_libs=False)

    def run_task(self, policy, code=0, job_id="a" * 32, suffix=""):
        args = self.args(policy, code)
        directory = self.base / (policy + suffix)
        directory.mkdir()
        make_bundle(args, self.config, job_id, directory)
        returned = directory / "return"
        actual = execute(directory / "payload.tar.gz", self.base / "data", returned)
        attempts = list((self.base / "data/jobs" / job_id).glob("attempt-*"))
        return actual, returned, attempts

    def config_file(self, config):
        text = "[cluster]\n" + "\n".join(f"{k} = {json.dumps(v)}" for k, v in config["cluster"].items())
        for node in config["nodes"]:
            text += "\n[[nodes]]\n" + "\n".join(f"{k} = {json.dumps(v)}" for k, v in node.items())
        path = self.base / "nodes.conf"
        path.write_text(text)
        return path

    def remote_python(self, node, source, *args):
        home = self.base / "remote-home"
        home.mkdir(exist_ok=True)
        return subprocess.run([sys.executable, "-c", source, *args], cwd=home,
                              env=dict(os.environ, HOME=str(home)), capture_output=True, check=True)

    def test_preston_resources_and_rendering(self):
        node = next(n for n in self.config["nodes"] if n["name"] == "preston")
        self.assertEqual(node["address"], "192.168.103.89")
        self.assertEqual(node["cpus"], 32)
        self.assertEqual(node["hardware_gpus"], 0)
        self.assertFalse(node["enable_gpus"])
        text = render(self.config, node)
        self.assertIn("NUM_CPUS = 32", text)
        self.assertIn("NUM_GPUS = 0", text)
        self.assertEqual(sum(n["cpus"] for n in self.config["nodes"]), 208)

    def test_load_custom_work_dirs(self):
        for value in ("/data1/baiyifan/condor-runtime", "/home/baiyifan/condor-runtime",
                      "~/condor-runtime", "custom runtime"):
            with self.subTest(value=value):
                config = copy.deepcopy(self.config)
                for node in config["nodes"]:
                    node["work_dir"] = value
                loaded = load_config(self.config_file(config))
                self.assertTrue(all(n["work_dir"] == value for n in loaded["nodes"]))

    def test_defaults_and_legacy_alias(self):
        config = copy.deepcopy(self.config)
        for node in config["nodes"]:
            node.pop("work_dir", None)
        loaded = load_config(self.config_file(config))
        self.assertEqual(runtime_path(loaded["nodes"][0]), str(RUNTIME))
        remote = loaded["nodes"][1]
        with patch("common.python_on", side_effect=self.remote_python) as python:
            expected = self.base / "remote-home/isla-runner/scheduler/runtime"
            self.assertEqual(runtime_path(remote), str(expected))
            self.assertEqual(python.call_args.args[2], "~/isla-runner/scheduler/runtime")
            remote["remote_runtime"] = "~/legacy-runtime"
            load_config(self.config_file(loaded))
            self.assertEqual(runtime_path(remote), str(self.base / "remote-home/legacy-runtime"))
            remote["work_dir"] = "~/new-runtime"
            load_config(self.config_file(loaded))
            self.assertEqual(runtime_path(remote), str(self.base / "remote-home/new-runtime"))

    def test_local_runtime_resolution(self):
        node = dict(self.config["nodes"][0])
        for value, expected in ((str(self.base / "absolute"), self.base / "absolute"),
                                ("custom/runtime", ROOT.parent / "custom/runtime"),
                                ("~/condor-runtime", Path.home() / "condor-runtime")):
            with self.subTest(value=value):
                node["work_dir"] = value
                self.assertEqual(runtime_path(node), str(expected.resolve()))

    def test_remote_runtime_resolution(self):
        node = dict(self.config["nodes"][1])
        for value, expected in ((str(self.base / "absolute"), self.base / "absolute"),
                                ("relative/runtime", self.base / "remote-home/relative/runtime"),
                                ("~/custom runtime", self.base / "remote-home/custom runtime")):
            with self.subTest(value=value), patch("common.python_on", side_effect=self.remote_python):
                node["work_dir"] = value
                self.assertEqual(runtime_path(node), str(expected))

    def test_invalid_work_dirs_rejected(self):
        for value in ("", " ", 123, False, [], "/", "//", "/etc", "/etc/condor", "/usr/local",
                      "/var", "/home", "~", "~/", "~/.", "~other/runtime", ".", "../runtime",
                      "/tmp/../etc", "bad\npath", "bad\x00path", "bad:path"):
            for index in (0, 1):
                with self.subTest(value=value, node=index):
                    config = copy.deepcopy(self.config)
                    config["nodes"][index]["work_dir"] = value
                    with self.assertRaises(ValueError):
                        load_config(self.config_file(config))

    def test_resolved_system_directory_rejected(self):
        link = self.base / "system-link"
        link.symlink_to("/etc", target_is_directory=True)
        for node in self.config["nodes"][:2]:
            with self.subTest(node=node["name"]), patch("common.python_on", side_effect=self.remote_python):
                with self.assertRaises(ValueError):
                    runtime_path(dict(node, work_dir=str(link)))

    def test_custom_paths_initialized_and_mounted(self):
        for index, node in enumerate(self.config["nodes"][:2]):
            with self.subTest(node=node["name"]):
                node = dict(node, work_dir=str(self.base / f"node-{index}"))
                with patch("common.python_on", side_effect=self.remote_python):
                    path = runtime_path(node)
                def run_python(target, argv):
                    return subprocess.run(argv[2:], capture_output=True, check=True)
                with patch("deploy_cluster.run", side_effect=run_python):
                    prepare_paths(self.config, node, path)
                for name in ("config", "auth", "condor/log", "condor/spool", "data", "submissions", "rendered", "retrieved"):
                    self.assertTrue((Path(path) / name).is_dir())
                for name in ("data", "submissions", "rendered", "retrieved"):
                    self.assertEqual((Path(path) / name).stat().st_uid, self.config["cluster"]["submit_uid"])
                with patch("deploy_cluster.inspect_container", return_value=None), \
                     patch("deploy_cluster.peaceful_stop"), patch("deploy_cluster.upload_root"), \
                     patch("deploy_cluster.docker") as docker:
                    start_node(self.config, node, path, "image-id", b"password", 1)
                argv = docker.call_args.args[2]
                for mount in (f"{path}/data:/srv/isla", f"{path}/submissions:/srv/submit",
                              f"{path}/condor:/var/lib/condor", f"{path}/config/condor.conf:/etc/condor/isla.conf:ro"):
                    self.assertIn(mount, argv)
                self.assertIn("preston:192.168.103.89", argv)

    def test_render_only_uses_manager_work_dir(self):
        config = copy.deepcopy(self.config)
        config["nodes"][0]["work_dir"] = str(self.base / "manager")
        path = self.config_file(config)
        with patch.object(sys, "argv", ["deploy_cluster.py", "--config", str(path), "--render-only"]), \
             patch("common.python_on") as remote, redirect_stdout(io.StringIO()):
            deploy_cluster.main()
        remote.assert_not_called()
        for node in config["nodes"]:
            self.assertEqual((self.base / "manager/rendered" / f'{node["name"]}.conf').read_text(),
                             render(config, node))

    def test_submit_uses_manager_work_dir(self):
        config = copy.deepcopy(self.config)
        config["nodes"][0]["work_dir"] = str(self.base / "manager")
        args = self.args()
        args.config, args.dry_run = str(self.config_file(config)), True
        output = io.StringIO()
        with patch("submit_job.parse_args", return_value=args), redirect_stdout(output):
            submit_job.main()
        record = json.loads(output.getvalue())
        directory = Path(record["directory"])
        self.assertEqual(directory.parent, self.base / "manager/submissions")
        self.assertTrue((directory / "payload.tar.gz").is_file())
        self.assertTrue((directory / "job_runner.py").is_file())
        self.assertIn(f'/srv/submit/{record["job_id"]}/payload.tar.gz', (directory / "job.sub").read_text())

    def test_manage_data_uses_node_work_dir(self):
        config = copy.deepcopy(self.config)
        for index in (0, 1):
            config["nodes"][index]["work_dir"] = str(self.base / f"node-{index}")
        path = self.config_file(config)
        for node in config["nodes"][:2]:
            with self.subTest(node=node["name"]), \
                 patch.object(sys, "argv", ["manage_data.py", "--backend", "condor", "--config", str(path), "--node", node["name"], "list"]), \
                 patch("common.python_on", side_effect=self.remote_python), \
                 patch("manage_data.docker", return_value=subprocess.CompletedProcess([], 0, b"[]")) as docker, \
                 redirect_stdout(io.StringIO()):
                manage_data.main()
            self.assertIn(f'{node["work_dir"]}/data:/srv/isla:ro', docker.call_args.args[2])

    def test_manage_fetch_uses_manager_work_dir(self):
        config = copy.deepcopy(self.config)
        config["nodes"][0]["work_dir"] = str(self.base / "manager")
        path = self.config_file(config)
        def download(argv, *, stdout, check):
            stdout.write(b"archive-content")
        output = io.StringIO()
        with patch.object(sys, "argv", ["manage_data.py", "--backend", "condor", "--config", str(path), "--node", "preston",
                                        "--job-id", "a" * 32, "fetch"]), \
             patch("common.python_on", return_value=subprocess.CompletedProcess([], 0, b"/home/remote/runtime\n")), \
             patch("manage_data.subprocess.run", side_effect=download), redirect_stdout(output):
            manage_data.main()
        target = Path(output.getvalue().strip())
        self.assertEqual(target.parent, self.base / "manager/retrieved/preston")
        self.assertEqual(target.read_bytes(), b"archive-content")

    def test_existing_paths_accept_alias_but_require_migration_on_change(self):
        previous = copy.deepcopy(self.config)
        previous["nodes"][0].pop("work_dir")
        for node in previous["nodes"][1:]:
            node["remote_runtime"] = node.pop("work_dir")
        with patch("common.python_on", side_effect=self.remote_python):
            check_existing_paths(previous, self.config)
            for index in (0, 1):
                with self.subTest(node=index):
                    changed = copy.deepcopy(self.config)
                    changed["nodes"][index]["work_dir"] = str(self.base / "changed")
                    with self.assertRaisesRegex(ValueError, "须单独迁移"):
                        check_existing_paths(previous, changed)

    def test_all_transfers_complete_work(self):
        code, returned, attempts = self.run_task("all")
        self.assertEqual(code, 0)
        with tarfile.open(returned / "full.tar.gz") as archive:
            self.assertEqual(archive.getmember("work/results/payload.bin").size, 2097152)
        self.assertTrue((attempts[0] / "work/results/payload.bin").exists())

    def test_summary_limits_and_retention(self):
        code, returned, attempts = self.run_task("summary")
        self.assertEqual(code, 0)
        self.assertFalse((returned / "full.tar.gz").exists())
        self.assertEqual((returned / "stdout.log").read_text(), "log-line\n")
        summary = json.loads((returned / "summary.json").read_text())
        self.assertEqual(summary["omitted_summaries"], ["results/oversize.txt"])
        self.assertEqual(json.loads((returned / "summaries/0/summary.json").read_text()), {"input_ok": True})
        self.assertTrue((attempts[0] / "work/results/payload.bin").exists())

    def test_none_returns_no_task_data(self):
        code, returned, attempts = self.run_task("none")
        self.assertEqual(code, 0)
        self.assertEqual(list(returned.iterdir()), [])
        self.assertEqual(json.loads((attempts[0] / "summary.json").read_text())["exit_code"], 0)
        text = submit_text(self.args("none"), self.config, "a" * 32)
        self.assertIn('transfer_output_files = ""', text)
        self.assertIn("output = /dev/null", text)

    def test_failure_preserves_exit_and_logs(self):
        code, returned, attempts = self.run_task("summary", 7)
        self.assertEqual(code, 7)
        self.assertEqual(json.loads((returned / "summary.json").read_text())["exit_code"], 7)
        self.assertIn("error-line", (returned / "stderr.log").read_text())

    def test_retry_keeps_separate_attempts(self):
        self.run_task("none")
        _, _, attempts = self.run_task("none", suffix="2")
        self.assertEqual(len(attempts), 2)

    def test_symlink_input_rejected(self):
        args = self.args()
        link = self.base / "link"
        link.symlink_to(self.base / "input.txt")
        args.input = [str(link)]
        with self.assertRaises(ValueError):
            make_bundle(args, self.config, "a" * 32, self.base)

    def test_archive_traversal_and_links_rejected(self):
        for name, kind in (("../outside", tarfile.REGTYPE), ("link", tarfile.SYMTYPE)):
            archive = self.base / "bad.tar.gz"
            with tarfile.open(archive, "w:gz") as stream:
                entry = tarfile.TarInfo(name)
                entry.type = kind
                if kind == tarfile.REGTYPE:
                    entry.size = 1
                    stream.addfile(entry, io.BytesIO(b"x"))
                else:
                    entry.linkname = "/tmp/outside"
                    stream.addfile(entry)
            with self.assertRaises(ValueError):
                unpack(archive, self.base / "extract")
            self.assertFalse((self.base / "outside").exists())

    def test_configs_and_requirements(self):
        for node in self.config["nodes"]:
            text = render(self.config, node)
            for name in ("@NAME@", "@MANAGER_ADDRESS@", "@SUBMIT_USER@", "@GPU_CONFIG@"):
                self.assertNotIn(name, text)
            self.assertIn(f'NUM_CPUS = {node["cpus"]}', text)
        args = self.args()
        args.node = "public-4090server"
        self.assertIn('TARGET.IslaNode == "public-4090server"', submit_text(args, self.config, "a" * 32))
        with self.assertRaises(ValueError):
            quote("$(injected)")

    def test_elf_dependency_bundle_executes(self):
        args = self.args("summary")
        args.executable = "/usr/bin/getconf"
        args.bundle_libs = True
        args.arguments = ["GNU_LIBC_VERSION"]
        args.summary = []
        directory = self.base / "elf"
        directory.mkdir()
        make_bundle(args, self.config, "b" * 32, directory)
        code = execute(directory / "payload.tar.gz", self.base / "data", directory / "return")
        self.assertEqual(code, 0)
        self.assertEqual((directory / "return/stdout.log").read_text().strip(), os.confstr("CS_GNU_LIBC_VERSION"))


if __name__ == "__main__":
    unittest.main()
