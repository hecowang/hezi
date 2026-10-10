import asyncio
import importlib.util
import json
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

if __name__=='__main__':unittest.main()
