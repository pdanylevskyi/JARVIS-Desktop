"""Thin SSH transport. No local agent, document reader, or model imports."""
import json
import sys
from pathlib import Path
import subprocess
import threading

COMMAND = 'cd ~/gemma && exec .desktop-server-venv/bin/python -u -m desktop.worker'


def request(settings, payload, emit, cancelled=None):
    host = settings['host']
    if host.startswith('-') or '@' not in host or any(c.isspace() for c in host):
        raise ValueError('Некоректна SSH-адреса.')
    command = ['ssh', '-T', '-i', str(Path(settings['key']).expanduser()), '-o', 'IdentitiesOnly=yes',
               '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
               '-o', 'ServerAliveInterval=20', host, COMMAND]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    errors = []
    def drain_errors():
        for line in process.stderr:
            errors.append(line.decode('utf-8', errors='replace'))
            del errors[:-30]
    error_thread=threading.Thread(target=drain_errors, daemon=True)
    error_thread.start()
    done = threading.Event()
    def stop():
        while not done.wait(.1):
            if cancelled is not None and cancelled.is_set():
                process.terminate()
                return
    threading.Thread(target=stop, daemon=True).start()
    received_done = False
    try:
        process.stdin.write(json.dumps(payload, ensure_ascii=False).encode('utf-8') + b'\n')
        process.stdin.flush()
        for line in process.stdout:
            event = json.loads(line)
            if event['type'] == 'done': received_done = True
            decision=emit(event['type'], event.get('value', ''))
            if event['type']=='confirm':
                process.stdin.write(json.dumps({'approved':decision is True}).encode()+b'\n')
                process.stdin.flush()
        code = process.wait(timeout=5)
        error_thread.join(timeout=2)
        if cancelled is not None and cancelled.is_set():
            raise RuntimeError('Зупинено.')
        if code or not received_done:
            detail=''.join(errors)[-1500:] or 'SSH-сеанс перервано.'
            if sys.platform=='darwin' and 'No route to host' in detail:
                detail+='\nПеревірте: Налаштування macOS → Конфіденційність і безпека → Локальна мережа → JARVIS. Дозвольте доступ і перезапустіть програму. Також перевірте, що Mac та Ubuntu у вашій локальній мережі.'
            raise RuntimeError(detail)
    finally:
        done.set()
        try:process.stdin.close()
        except BrokenPipeError:pass
        if process.poll() is None:
            process.terminate()
        process.stdout.close(); process.stderr.close()
