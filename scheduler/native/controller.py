#!/usr/bin/env python3
"""每次 Make 一个主控；文件队列供 proxy 通信，SQLite 保存任务状态。"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scheduler.native.cache import Cache
from scheduler.native.common import ENVIRONMENT, atomic_json, load_config
from scheduler.native.inputs import describe, runtime_files, sniff
from scheduler.native.qos import QoS
from scheduler.native import transport


class Controller:
    def __init__(self, run, config, workspace):
        self.run = Path(run)
        self.config = config
        self.workspace = Path(workspace).resolve()
        self.workspace_id = hashlib.sha256(str(self.workspace).encode()).hexdigest()[:24]
        self.cache = None
        self.qos = QoS(config['nodes'])
        self.lock = threading.RLock()
        self.changed = threading.Event()
        self.jobs = {}
        self.owners = []
        self.threads = []
        self.frozen = {}
        self.stopping = False
        self.db = sqlite3.connect(self.run / 'state.sqlite', check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, state TEXT, record TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events(id TEXT, state TEXT, timestamp REAL)')
        self.db.commit()
        for name in ('requests', 'jobs', 'cancel'):
            (self.run / name).mkdir(exist_ok=True)

    def state(self, job, state, **fields):
        with self.lock:
            job.update(fields, state=state)
            self.db.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?)',
                            (job['job_id'], state, json.dumps(job)))
            self.db.execute('INSERT INTO events VALUES(?,?,?)', (job['job_id'], state, time.time()))
            self.db.commit()
            atomic_json(self.run / 'jobs' / job['job_id'] / 'state.json', job)

    def finish(self, job, result, release=True):
        with self.lock:
            if release:
                self.qos.release(job['job_id'])
            state = 'UNKNOWN' if not release else 'CANCELLED' if result.get('cancelled') else (
                'SUCCEEDED' if result['return_code'] == 0 else 'FAILED')
            self.state(job, state, return_code=result['return_code'])
            atomic_json(self.run / 'jobs' / job['job_id'] / 'result.json', result)
            self.changed.set()

    def preflight(self, node):
        child = transport.start(node, {'action': 'owner'})
        try:
            with selectors.DefaultSelector() as ready:
                ready.register(child.stdout, selectors.EVENT_READ)
                if not ready.select(20):
                    raise TimeoutError('节点预检超时')
            report = transport.response(child)
            if report['machine'] != os.uname().machine:
                raise RuntimeError('节点 CPU 架构与主控不同')
            with self.lock:
                self.qos.nodes[node['name']]['cpus'] = min(node['cpus'], report['cpus'])
                self.owners.append((node['name'], child))
            return node['name'], report
        except Exception as error:
            child.kill()
            child.communicate()
            self.qos.nodes[node['name']]['online'] = False
            return node['name'], {'error': str(error)}

    def cancelled(self, job):
        return self.stopping or (self.run / 'cancel' / job['job_id']).exists()

    def prepare(self, request):
        manifest = describe(request['argv'], request['cwd'])
        Path(manifest['cwd']).relative_to(self.workspace)
        manifest['environment'] = {k: v for k, v in request.get('environment', {}).items() if k in ENVIRONMENT}
        for key in ('log_path', 'proxy_pid', 'proxy_start'):
            if key in request:
                manifest[key] = request[key]
        return manifest

    def prepare_remote(self, description):
        request = dict(argv=description['original_argv'], cwd=description['cwd'],
                       environment=description['environment'], log_path=description.get('log_path'))
        manifest = sniff(request['argv'], request['cwd'], self.workspace, request.get('log_path'))
        environment = {k: v for k, v in request.get('environment', {}).items()
                       if k in ENVIRONMENT}
        manifest['environment'] = environment
        binary = (Path(request['cwd']) / request['argv'][manifest['binary_index']]).resolve()
        with self.lock:
            if self.cache is None:
                self.cache = Cache(self.run.parent.parent / 'cache' / self.workspace_id)
            runtime_key = str(binary)
            if not hasattr(self, 'runtimes'):
                self.runtimes = {}
            if runtime_key not in self.runtimes:
                self.runtimes[runtime_key] = runtime_files(binary)
            libraries, loader = self.runtimes[runtime_key]
            files = dict(manifest.pop('files'))
            files.update({'_runtime/' + name: source for name, source in libraries.items()})
            entries = {}
            for logical, source in files.items():
                # 本轮第一次发现时冻结；已经排队的任务不受源文件后续编辑影响。
                if source not in self.frozen:
                    self.frozen[source] = self.cache.freeze(source)
                entries[logical] = self.frozen[source]
        manifest['entries'] = entries
        manifest['loader'] = loader
        manifest['generation'] = hashlib.sha256(json.dumps(
            {k: v['digest'] for k, v in sorted(entries.items())}, sort_keys=True).encode()).hexdigest()
        return manifest

    def perform_local(self, job):
        directory = self.run / 'jobs' / job['job_id']
        self.state(job, 'STARTING', local=True, transferred_bytes=0)
        # proxy 持有原 recipe 的 stdout/stderr 与完整环境；让它直接启动原命令。
        atomic_json(directory / 'local.json', dict(manifest=job['manifest'], node=job['node'],
                                                  job_id=job['job_id'], attempt_id=job['attempt_id']))
        running = False
        while not (directory / 'local-result.json').exists():
            if self.cancelled(job):
                (self.run / 'cancel' / job['job_id']).touch()
            if not running and (directory / 'local-running.json').exists():
                self.state(job, 'RUNNING', **json.loads((directory / 'local-running.json').read_text()))
                running = True
            manifest = job['manifest']
            try:
                pid = manifest['proxy_pid']
                identity = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()[19]
                alive = identity == manifest['proxy_start']
            except (KeyError, FileNotFoundError, ProcessLookupError):
                alive = False
            if not alive:
                self.qos.nodes[job['node']]['online'] = False
                self.finish(job, dict(return_code=125, local=True, job_id=job['job_id'],
                            infrastructure_error='本地 proxy 已退出，监督器状态须核对'), release=False)
                return
            time.sleep(.05)
        result = json.loads((directory / 'local-result.json').read_text())
        self.state(job, 'COLLECTING')
        confirmed = result.get('execution_confirmed', False)
        if not confirmed:
            self.qos.nodes[job['node']]['online'] = False
        self.finish(job, result, release=confirmed)

    def perform(self, job):
        node = self.qos.nodes[job['node']]
        if node.get('local'):
            self.perform_local(job)
            return
        try:
            manifest = self.prepare_remote(job['manifest'])
            self.state(job, 'RESERVED', remote_manifest=manifest)
        except Exception as error:
            self.finish(job, dict(return_code=125, job_id=job['job_id'], infrastructure_error=str(error)))
            return
        started = False
        try:
            self.state(job, 'STAGING')
            sync = transport.stage(node, self.workspace_id, manifest['generation'], manifest['entries'])
            self.state(job, 'STARTING', transferred_bytes=sync['transferred_bytes'])
            if self.cancelled(job):
                self.finish(job, {'return_code': 130, 'cancelled': True, 'job_id': job['job_id']})
                return
            directory = self.run / 'jobs' / job['job_id']
            # STARTING 起的传输失败不能证明远端未运行；保留预约并标 UNKNOWN。
            started = True
            def event(message):
                if message.get('state') == 'RUNNING':
                    self.state(job, 'RUNNING', attempt=message['attempt'])
                if 'log' in message:
                    with (directory / 'stream.log').open('ab') as stream:
                        stream.write(base64.b64decode(message['log']))
            result = transport.execute(node, dict(job_id=job['job_id'], attempt_id=job['attempt_id'],
                                       workspace=self.workspace_id, generation=manifest['generation'],
                                       manifest=manifest, node=node['name'],
                                       lease_seconds=self.config.get('native', {}).get('lease_seconds', 60)),
                                       lambda: self.cancelled(job), event)
            self.state(job, 'COLLECTING')
            (directory / 'tail.log').write_bytes(base64.b64decode(result.pop('tail', '')))
            confirmed = result.get('execution_confirmed', False)
            if not confirmed:
                node['online'] = False
            self.finish(job, result, release=confirmed)
        except Exception as error:
            node['online'] = False
            if not started and not self.cancelled(job):
                # staging 尚未启动监督器，可安全溢出到其他健康节点。
                with self.lock:
                    self.qos.release(job['job_id'])
                    self.state(job, 'WAITING', staging_error=str(error))
                    self.changed.set()
                return
            if started:
                for retry in range(3):
                    try:
                        result = transport.inspect(node, job['job_id'], job['attempt_id'])
                        if result is not None:
                            directory = self.run / 'jobs' / job['job_id']
                            (directory / 'tail.log').write_bytes(base64.b64decode(result.pop('tail', '')))
                            self.finish(job, result, release=result.get('execution_confirmed', False))
                            return
                    except Exception:
                        break
                    time.sleep(1)
            self.finish(job, {'return_code': 125, 'job_id': job['job_id'],
                              'infrastructure_error': str(error), 'remote_state': 'unknown' if started else 'not_started',
                              'node': node['name'], 'attempt_id': job['attempt_id']}, release=not started)

    def ingest(self):
        for path in sorted((self.run / 'requests').glob('*.json')):
            job_id = path.stem
            if job_id in self.jobs:
                continue
            request = json.loads(path.read_text())
            job = {'job_id': job_id, 'attempt_id': uuid.uuid4().hex, 'submitted': time.time()}
            self.jobs[job_id] = job
            self.state(job, 'PREPARING')
            try:
                manifest = self.prepare(request)
                job['manifest'] = manifest
                if not self.qos.possible(manifest['cores']):
                    raise ValueError(f"UNSCHEDULABLE：{manifest['cores']} 核超过所有节点容量")
                self.state(job, 'WAITING')
            except Exception as error:
                self.finish(job, {'return_code': 125, 'job_id': job_id, 'infrastructure_error': str(error)})

    def schedule(self):
        with self.lock:
            for name, owner in self.owners:
                if owner.poll() is not None:
                    self.qos.nodes[name]['online'] = False
            for job in self.jobs.values():
                if job['state'] != 'WAITING':
                    continue
                if self.cancelled(job):
                    self.finish(job, {'return_code': 130, 'cancelled': True, 'job_id': job['job_id']})
                    continue
                name = self.qos.reserve(job['job_id'], job['manifest']['cores'])
                if name is not None:
                    self.state(job, 'RESERVED', node=name)
                    thread = threading.Thread(target=self.perform, args=(job,), daemon=True)
                    self.threads.append(thread)
                    thread.start()
                elif not any(n['online'] and n['cpus'] >= job['manifest']['cores'] for n in self.qos.nodes.values()):
                    self.finish(job, {'return_code': 125, 'infrastructure_error': '能承接该任务的节点均离线或状态未知'})
            atomic_json(self.run / 'status.json', {
                'counts': {state: sum(j['state'] == state for j in self.jobs.values())
                           for state in sorted({j['state'] for j in self.jobs.values()})},
                'nodes': list(self.qos.nodes.values())})

    def serve(self):
        with ThreadPoolExecutor(max_workers=len(self.config['nodes'])) as pool:
            reports = dict(pool.map(self.preflight, self.config['nodes']))
        atomic_json(self.run / 'preflight.json', reports)
        if not any(n['online'] for n in self.qos.nodes.values()):
            atomic_json(self.run / 'ready.json', {'error': '所有节点预检失败', 'reports': reports})
            return 125
        atomic_json(self.run / 'ready.json', {'pid': os.getpid()})
        while True:
            self.ingest()
            if (self.run / 'stop').exists():
                self.stopping = True
            self.schedule()
            active = any(t.is_alive() for t in self.threads)
            waiting = any(j['state'] in ('PREPARING', 'WAITING', 'RESERVED') for j in self.jobs.values())
            if self.stopping and not active and not waiting:
                break
            self.changed.wait(.05)
            self.changed.clear()
        return 0

    def close(self):
        for name, child in self.owners:
            try:
                child.stdin.write(b'{"close":true}\n')
                child.stdin.flush()
                child.stdin.close()
                child.wait(timeout=80)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                child.kill()
                child.wait()
            finally:
                child.stdout.close()
                child.stderr.close()
        self.db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--workspace', required=True)
    args = parser.parse_args()
    controller = Controller(args.run, load_config(args.config), args.workspace)
    def stop(number, frame):
        controller.stopping = True
        controller.changed.set()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        return controller.serve()
    finally:
        controller.close()


if __name__ == '__main__':
    raise SystemExit(main())
