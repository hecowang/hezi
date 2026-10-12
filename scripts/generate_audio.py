"""Pre-generate Volcengine bidirectional TTS. Credentials stay in process env."""
import argparse
import asyncio
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'wss://openspeech.bytedance.com/api/v3/tts/bidirection'

def packet(event, payload=None, session_id=None):
    data = json.dumps(payload or {}, ensure_ascii=False).encode()
    result = b'\x11\x14\x10\x00' + struct.pack('>i', event)
    if session_id is not None:
        sid = session_id.encode()
        result += struct.pack('>I', len(sid)) + sid
    return result + struct.pack('>I', len(data)) + data

def parse_packet(data):
    if not isinstance(data, bytes) or len(data) < 4 or data[0] >> 4 != 1:
        raise ValueError('Invalid TTS frame')
    offset = (data[0] & 15) * 4
    if offset < 4 or offset > len(data):
        raise ValueError('Invalid header length')
    kind, flags = data[1] >> 4, data[1] & 15
    def integer():
        nonlocal offset
        if offset + 4 > len(data): raise ValueError('Truncated TTS frame')
        value = struct.unpack_from('>I', data, offset)[0]; offset += 4
        return value
    def blob():
        nonlocal offset
        size = integer()
        if offset + size > len(data): raise ValueError('Truncated TTS payload')
        value = data[offset:offset + size]; offset += size
        return value
    if kind == 15:
        code = integer(); payload = blob()
        raise RuntimeError(f'TTS error {code}: {payload.decode(errors="replace")}')
    if kind not in (9, 11) or not flags & 4:
        raise ValueError('Unsupported TTS frame')
    event = integer()
    # Connection responses carry a connection id; session events a session id.
    identifier = blob().decode()
    payload = blob()
    if offset != len(data): raise ValueError('Unexpected trailing data')
    compression = data[2] & 15
    if compression == 1: payload = gzip.decompress(payload)
    elif compression != 0: raise ValueError('Unsupported compression')
    return event, identifier, payload

async def receive(ws, expected=None, session_id=None):
    event, sid, payload = parse_packet(await ws.recv())
    if event in (51, 153, 151):
        raise RuntimeError(f'TTS event {event}: {payload.decode(errors="replace")}')
    if session_id is not None and sid != session_id:
        raise RuntimeError('TTS session id mismatch')
    if expected is not None and event != expected:
        raise RuntimeError(f'Expected event {expected}, got {event}')
    return event, payload

async def synthesize(ws, text, config):
    sid = str(uuid.uuid4())
    params = {'speaker': config['speaker'], 'text': '', 'audio_params': {
        'format': 'mp3', 'sample_rate': 24000, 'bit_rate': 64000,
        'speech_rate': config['speech_rate']}}
    base = {'user': {'uid': 'hezi-offline-builder'}, 'namespace': 'BidirectionalTTS', 'req_params': params}
    await ws.send(packet(100, dict(base, event=100), sid))
    await receive(ws, 150, sid)
    task = dict(base, event=200, req_params=dict(params, text=text))
    await ws.send(packet(200, task, sid))
    await ws.send(packet(102, {}, sid))
    chunks = []
    while True:
        event, payload = await receive(ws, session_id=sid)
        if event == 352: chunks.append(payload)
        elif event == 152:
            meta = json.loads(payload or b'{}')
            if meta.get('status_code', 20000000) != 20000000:
                raise RuntimeError('TTS session failed: ' + str(meta))
            break
    audio = b''.join(chunks)
    if not valid_audio(audio): raise RuntimeError('TTS returned empty or invalid MP3')
    return audio

def valid_audio(data):
    return len(data) > 32 and (data.startswith(b'ID3') or (data[0] == 255 and data[1] & 224 == 224))

def filename(text, config):
    identity = json.dumps({'text': text, 'config': config, 'format': 'mp3', 'sample_rate': 24000, 'bit_rate': 64000, 'protocol': 1}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(identity.encode()).hexdigest() + '.mp3'

def atomic_write(path, data):
    temp = path.with_suffix(path.suffix + '.tmp')
    try:
        temp.write_bytes(data)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)

def plan(catalog, config, output):
    entries = {text: filename(text, config) for text in catalog}
    missing = []
    for text, name in entries.items():
        path = output / name
        if not path.exists() or not valid_audio(path.read_bytes()): missing.append((text, name))
    return entries, missing

async def generate(catalog, config, output, api_key, timeout=60, allow_partial=False):
    output.mkdir(parents=True, exist_ok=True)
    entries, missing = plan(catalog, config, output)
    print(f'TTS: {len(entries)} clips; reuse {len(entries)-len(missing)}; generate {len(missing)}.', flush=True)
    deferred = []
    if missing and not api_key:
        if not allow_partial or len(missing) == len(entries):
            raise RuntimeError('Missing VOLC_TTS_API_KEY. Configure it to generate missing audio, or install the offline audio pack.')
        deferred = missing
        missing_names = {name for _, name in missing}
        entries = {text: name for text, name in entries.items() if name not in missing_names}
        print(f'TTS: offline mode; {len(deferred)} missing clips deferred. Existing audio remains available. Set VOLC_TTS_API_KEY to complete generation.', flush=True)
        missing = []
    if missing:
        from websockets.asyncio.client import connect
        headers = {'X-Api-Key': api_key, 'X-Api-Resource-Id': config['resource_id'], 'X-Api-Connect-Id': str(uuid.uuid4())}
        async with connect(ENDPOINT, additional_headers=headers, open_timeout=15, max_size=8*1024*1024) as ws:
            async with asyncio.timeout(timeout):
                await ws.send(packet(1)); await receive(ws, 50)
            for index, (text, name) in enumerate(missing, 1):
                async with asyncio.timeout(timeout): audio = await synthesize(ws, text, config)
                atomic_write(output / name, audio)
                print(f'TTS: generated {index}/{len(missing)}', flush=True)
            async with asyncio.timeout(timeout):
                await ws.send(packet(2)); await receive(ws, 52)
    manifest = {'version': 1, 'config': config, 'clips': {t: 'audio/' + n for t, n in entries.items()}, 'missing': [text for text, _ in deferred]}
    atomic_write(output / 'manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2).encode())
    return manifest

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Count missing clips without contacting TTS')
    parser.add_argument('--allow-partial', action='store_true', help='Without a key, serve available clips if at least one cached clip exists')
    args = parser.parse_args()
    config = {'speaker': os.getenv('VOLC_TTS_SPEAKER', 'zh_female_vv_uranus_bigtts'),
              'resource_id': os.getenv('VOLC_TTS_RESOURCE_ID', 'seed-tts-2.0'),
              'speech_rate': int(os.getenv('VOLC_TTS_SPEECH_RATE', '-15'))}
    if not -50 <= config['speech_rate'] <= 100: raise ValueError('speech_rate must be between -50 and 100')
    catalog = json.loads(subprocess.check_output(['node', str(ROOT / 'scripts/catalog.mjs')], text=True))
    output = ROOT / 'audio'
    # Lock works on macOS/Linux/Windows; a killed process may leave a lock (documented).
    lock = ROOT / '.audio-generation.lock'
    if args.dry_run:
        entries, missing = plan(catalog, config, output)
        print(f'TTS: {len(entries)} clips; reuse {len(entries)-len(missing)}; generate {len(missing)}.'); return
    try: fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError: raise RuntimeError('Audio generator already running, or stale .audio-generation.lock. Stop it before removing the lock.')
    os.close(fd)
    try: asyncio.run(generate(catalog, config, output, os.getenv('VOLC_TTS_API_KEY'), int(os.getenv('VOLC_TTS_TIMEOUT', '60')), allow_partial=args.allow_partial))
    finally: lock.unlink(missing_ok=True)

if __name__ == '__main__':
    try: main()
    except (Exception, KeyboardInterrupt) as exc:
        # Never expose auth headers or request objects in tracebacks.
        message = str(exc).replace(os.getenv('VOLC_TTS_API_KEY') or '\0', '[REDACTED]')
        print('Audio generation failed: ' + message, file=sys.stderr)
        sys.exit(1)
