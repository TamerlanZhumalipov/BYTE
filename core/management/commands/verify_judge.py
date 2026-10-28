"""Real container acceptance tests; run on Linux before allowing contest users."""
import secrets
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from core.judge import run_submission


class Command(BaseCommand):
    help = 'Exercise real Python/C++ containers, host-file isolation, network isolation and timeout.'

    def handle(self, *args, **kwargs):
        if settings.JUDGE_BACKEND != 'docker':
            raise CommandError('This check requires the docker backend.')
        with tempfile.TemporaryDirectory(prefix='byte-host-secret-') as directory:
            canary=Path(directory)/'canary';canary.write_text(secrets.token_hex(32))
            python_code=f'''import pathlib, socket, os
assert os.getuid() == 65534
assert pathlib.Path("/sys/fs/cgroup/memory.max").read_text().strip() == str(512*1024*1024)
assert pathlib.Path("/sys/fs/cgroup/pids.max").read_text().strip() == "32"
assert not os.environ.get("DJANGO_SECRET_KEY")
try:
    pathlib.Path("/byte-must-stay-readonly").write_text("probe")
except OSError:
    pass
else:
    raise RuntimeError("Writable root filesystem")
assert not pathlib.Path({str(canary)!r}).exists()
assert not pathlib.Path('/var/run/docker.sock').exists()
s = socket.socket()
s.settimeout(.2)
try:
    s.connect(('1.1.1.1', 443))
except OSError:
    print('isolated')
else:
    raise RuntimeError('Network was accessible')
finally:
    s.close()
'''
            probes=[('python',python_code,[('','isolated')],2),
                    ('cpp','#include <iostream>\nint main(){ std::cout << 42; }',[('','42')],2),
                    ('python','while True: pass',[('','')],.2)]
            expected=['OK','OK','TLE']
            try:
                for probe,want in zip(probes,expected):
                    result=run_submission(probe[1],probe[0],probe[2],probe[3])
                    if result.verdict != want:
                        raise CommandError(f'Judge acceptance failed: {probe[0]} {result.verdict}; expected {want}. {result.message}')
            except (OSError,RuntimeError) as exc:
                raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS('Docker acceptance passed: Python, C++, host-file/network isolation, timeout.'))
