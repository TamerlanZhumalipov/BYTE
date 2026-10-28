"""Docker execution boundary. Never mount the project, database, secrets or socket."""
import os
import shutil
import subprocess
import tempfile
import uuid
import time

from django.conf import settings

MAX_CAPTURE = 1_000_000


def run(cmd, workdir, *, stdin=b'', timeout=3, writable=False):
    docker = shutil.which('docker')
    if not docker:
        raise RuntimeError('Docker is required for the programming judge; no host fallback is allowed.')
    name = 'byte-job-' + uuid.uuid4().hex
    client_env = {'PATH': os.defpath, 'LANG': 'C.UTF-8'}
    for key in ('HOME','XDG_RUNTIME_DIR','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH'):
        if key in os.environ:
            client_env[key] = os.environ[key]
    mount = f'type=bind,src={workdir},dst=/work' + ('' if writable else ',readonly')
    args = [docker, 'run', '--rm', '--pull=never', '--name', name,
            '--network=none', '--read-only', '--cap-drop=ALL',
            '--security-opt=no-new-privileges', '--user=65534:65534',
            '--pids-limit=32', '--memory=512m', '--memory-swap=512m', '--cpus=1',
            '--ulimit=fsize=16777216:16777216', '--ulimit=nofile=64:64',
            '--log-driver=none', '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=67108864',
            '--mount', mount, '--workdir=/work', '-i', settings.JUDGE_DOCKER_IMAGE, *cmd]
    # Capture outside the bind mount: malicious compiler-created symlinks cannot
    # redirect the web process's output files to host paths.
    with tempfile.TemporaryDirectory(prefix='byte-capture-') as capture:
        outpath, errpath = os.path.join(capture, 'out'), os.path.join(capture, 'err')
        try:
            with open(outpath, 'wb') as out, open(errpath, 'wb') as err:
                process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                           env=client_env)
                deadline = time.monotonic() + timeout
                first = True
                try:
                    while True:
                        try:
                            process.communicate(input=stdin if first else None, timeout=min(.05, max(.001, deadline-time.monotonic())))
                            break
                        except subprocess.TimeoutExpired:
                            first = False
                            if os.path.getsize(outpath) > MAX_CAPTURE or os.path.getsize(errpath) > 4000:
                                process.kill()
                                process.communicate()
                                return subprocess.CompletedProcess(args, 1, b'', b'Output limit exceeded.')
                            if time.monotonic() >= deadline:
                                raise
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    raise
            with open(outpath, 'rb') as out, open(errpath, 'rb') as err:
                stdout, stderr = out.read(MAX_CAPTURE+1), err.read(4001)
            if len(stdout) > MAX_CAPTURE or len(stderr) > 4000:
                return subprocess.CompletedProcess(args, 1, b'', b'Output limit exceeded.')
            return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
        except FileNotFoundError as exc:
            raise RuntimeError('Docker is required for the programming judge; no host fallback is allowed.') from exc
        finally:
            # Killing docker's client alone does not stop the container and its
            # descendants. Always reap by an unguessable server-generated name.
            try:
                subprocess.run([docker,'rm','-f',name], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=5,
                               env=client_env)
            except (OSError, subprocess.TimeoutExpired):
                pass
