import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('generate_audio',Path(__file__).parents[1]/'scripts/generate_audio.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
CONFIG={'speaker':'test','resource_id':'seed-tts-2.0','speech_rate':-15}
MP3=b'ID3'+b'\0'*100

def frame(event, identifier, payload, kind=9):
    sid=identifier.encode()
    return bytes([0x11,(kind<<4)|4,0x10 if kind==9 else 0,0])+struct.pack('>II',event,len(sid))+sid+struct.pack('>I',len(payload))+payload

class FakeSocket:
    def __init__(self): self.frames=[]; self.sent=[]
    async def send(self, data):
        self.sent.append(data)
        event=struct.unpack_from('>I',data,4)[0]
        length=struct.unpack_from('>I',data,8)[0]
        sid=data[12:12+length].decode()
        if event==100:self.frames.append(frame(150,sid,b'{}'))
        if event==102:self.frames.extend([frame(350,sid,b'{}'),frame(352,sid,MP3,11),frame(152,sid,b'{"status_code":20000000}')])
    async def recv(self): return self.frames.pop(0)

class AudioTests(unittest.TestCase):
    def test_protocol(self):
        self.assertEqual(module.parse_packet(frame(50,'connection',b'{}')),(50,'connection',b'{}'))
        with self.assertRaises(ValueError): module.parse_packet(frame(352,'sid',MP3,11)[:-2])
        error=b'\x11\xf0\x10\x00'+struct.pack('>II',123,3)+b'bad'
        with self.assertRaisesRegex(RuntimeError,'123'): module.parse_packet(error)
    def test_synthesis_lifecycle(self):
        ws=FakeSocket()
        result=asyncio.run(module.synthesize(ws,'米',CONFIG))
        self.assertEqual(result,MP3)
        self.assertEqual([struct.unpack_from('>I',p,4)[0] for p in ws.sent],[100,200,102])
    def test_cache_missing_corrupt_and_config_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            entries,missing=module.plan(['米','水'],CONFIG,root);self.assertEqual(len(missing),2)
            module.atomic_write(root/entries['米'],MP3)
            self.assertEqual(len(module.plan(['米','水'],CONFIG,root)[1]),1)
            (root/entries['水']).write_bytes(b'')
            self.assertEqual(len(module.plan(['米','水'],CONFIG,root)[1]),1)
            self.assertNotEqual(module.filename('米',CONFIG),module.filename('米',dict(CONFIG,speech_rate=-20)))
            self.assertNotEqual(module.filename('米',CONFIG),module.filename('大米',CONFIG))
            self.assertFalse(list(root.glob('*.tmp')))
    def test_full_cache_needs_no_key_or_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/module.filename('米',CONFIG)).write_bytes(MP3)
            result=asyncio.run(module.generate(['米'],CONFIG,root,None))
            self.assertEqual(len(result['clips']),1)
            self.assertTrue((root/'manifest.json').exists())
    def test_missing_without_key_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError,'Missing VOLC_TTS_API_KEY'):
                asyncio.run(module.generate(['米'],CONFIG,Path(folder),None))
            self.assertFalse((Path(folder)/'manifest.json').exists())

    def test_partial_cache_without_key_only_lists_valid_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/module.filename('米',CONFIG)).write_bytes(MP3)
            (root/module.filename('水',CONFIG)).write_bytes(b'')
            result=asyncio.run(module.generate(['米','水','说明'],CONFIG,root,None,allow_partial=True))
            self.assertEqual(set(result['clips']),{'米'})
            self.assertEqual(result['missing'],['水','说明'])
            self.assertEqual(json.loads((root/'manifest.json').read_text())['clips'],result['clips'])
            self.assertEqual((root/module.filename('米',CONFIG)).read_bytes(),MP3)

    def test_no_audio_still_requires_key_even_in_partial_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError,'Missing VOLC_TTS_API_KEY'):
                asyncio.run(module.generate(['米'],CONFIG,Path(folder),None,allow_partial=True))

    def test_dotenv_quotes_comments_bom_and_environment_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env'
            path.write_text("\ufeff# settings\nVOLC_TTS_API_KEY=\"example-token\" # comment\nexport VOLC_TTS_SPEAKER='voice'\nVOLC_TTS_SPEECH_RATE=-15 # slower\nVALUE=contains#hash\n",encoding='utf-8')
            env={'VOLC_TTS_SPEAKER':'terminal-voice'}
            module.load_dotenv(path,env)
            self.assertEqual(env['VOLC_TTS_API_KEY'],'example-token')
            self.assertEqual(env['VOLC_TTS_SPEAKER'],'terminal-voice')
            self.assertEqual(env['VOLC_TTS_SPEECH_RATE'],'-15')
            self.assertEqual(env['VALUE'],'contains#hash')

    def test_missing_dotenv_and_invalid_line_dont_expose_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'.env';env={}
            module.load_dotenv(path,env);self.assertEqual(env,{})
            path.write_text('VOLC_TTS_API_KEY=example-token\nBAD=\"unclosed-sensitive-value\n')
            with self.assertRaises(ValueError) as error:module.load_dotenv(path,env)
            self.assertIn('line 2',str(error.exception))
            self.assertNotIn('sensitive',str(error.exception))
            self.assertEqual(env,{})

    def test_cli_loads_repository_dotenv_from_another_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'project';(root/'scripts').mkdir(parents=True);(root/'audio').mkdir()
            shutil.copyfile(module.__file__,root/'scripts/generate_audio.py')
            (root/'scripts/catalog.mjs').write_text('console.log(JSON.stringify(["米"]));')
            (root/'.env').write_text('VOLC_TTS_API_KEY=example-token\nVOLC_TTS_SPEAKER=dotenv-voice\nVOLC_TTS_RESOURCE_ID=seed-tts-2.0\nVOLC_TTS_SPEECH_RATE=-20\n')
            config={'speaker':'dotenv-voice','resource_id':'seed-tts-2.0','speech_rate':-20}
            (root/'audio'/module.filename('米',config)).write_bytes(MP3)
            env={k:v for k,v in os.environ.items() if not k.startswith('VOLC_TTS_')}
            command=[__import__('sys').executable,str(root/'scripts/generate_audio.py'),'--dry-run']
            output=subprocess.check_output(command,cwd=folder,env=env,text=True)
            self.assertIn('reuse 1; generate 0',output)
            self.assertNotIn('example-token',output)
            env['VOLC_TTS_SPEECH_RATE']='-15'
            output=subprocess.check_output(command,cwd=folder,env=env,text=True)
            self.assertIn('reuse 0; generate 1',output)

if __name__=='__main__':unittest.main()
