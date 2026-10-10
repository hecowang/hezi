"""Exercise actual startup with cached fixtures, never contact a paid API."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audio_builder', ROOT/'scripts/generate_audio.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class StartupTests(unittest.TestCase):
    def test_cached_startup_http_and_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'hezi'
            shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('audio','__pycache__','.audio-generation.lock','.env','.venv','node_modules'))
            catalog=json.loads(subprocess.check_output(['node',str(root/'scripts/catalog.mjs')],text=True))
            config={'speaker':'zh_female_vv_uranus_bigtts','resource_id':'seed-tts-2.0','speech_rate':-15}
            audio=root/'audio';audio.mkdir()
            for text in catalog:(audio/builder.filename(text,config)).write_bytes(b'ID3'+b'\0'*100)
            (root/'.env').write_text('PRIVATE_TEST_ONLY=secret-fixture')
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            env={k:v for k,v in os.environ.items() if not k.startswith('VOLC_TTS_')}
            env['PORT']=str(port)
            process=subprocess.Popen(['node','scripts/start.mjs'],cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            url=f'http://127.0.0.1:{port}'
            try:
                deadline=time.monotonic()+10
                while True:
                    try:
                        with urllib.request.urlopen(url,timeout=1) as response:self.assertEqual(response.status,200)
                        break
                    except (urllib.error.URLError,ConnectionError):
                        if process.poll() is not None or time.monotonic()>deadline:raise AssertionError('server failed to start')
                        time.sleep(.05)
                with urllib.request.urlopen(url+'/audio/manifest.json') as response:
                    manifest=json.load(response);self.assertEqual(len(manifest['clips']),501)
                name=next(iter(manifest['clips'].values()))
                request=urllib.request.Request(url+'/'+name,headers={'Range':'bytes=0-9'})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status,206);self.assertEqual(len(response.read()),10)
                for name in ['.env','.env.example','scripts/generate_audio.py','requirements.txt']:
                    with self.assertRaises(urllib.error.HTTPError) as result:urllib.request.urlopen(url+'/'+name)
                    self.assertEqual(result.exception.code,404)
            finally:
                process.terminate();output=process.communicate(timeout=5)[0]
            self.assertIn('reuse 501; generate 0',output)
