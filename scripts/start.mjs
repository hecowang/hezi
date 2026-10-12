import { spawnSync } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const result = spawnSync(process.env.PYTHON || 'python3', [resolve(root, 'scripts/generate_audio.py'), '--allow-partial'], { cwd: root, stdio: 'inherit' });
if (result.error || result.status !== 0) { console.error('Startup stopped: finish audio generation first.'); process.exit(1); }
const allowed = new Set(['index.html','style.css','app.js','course.js','speech-text.js','audio-player.js','feed-state.js']);
const mime = { html: 'text/html; charset=utf-8', css: 'text/css; charset=utf-8', js: 'text/javascript; charset=utf-8', mp3: 'audio/mpeg', json: 'application/json; charset=utf-8' };
createServer(async (req, res) => {
  try {
    if (!['GET','HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    const pathname = new URL(req.url, 'http://localhost').pathname;
    const name = pathname === '/' ? 'index.html' : pathname.slice(1);
    if (!allowed.has(name) && !/^audio\/(?:manifest\.json|[a-f0-9]{64}\.mp3)$/.test(name)) { res.writeHead(404); res.end(); return; }
    const path = resolve(root, name), info = await stat(path);
    let start=0,end=info.size-1,status=200;
    if (req.headers.range) {
      const m=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range);
      if (!m || (start=Number(m[1]))>=info.size || (end=m[2]?Math.min(Number(m[2]),end):end)<start) {
        res.writeHead(416,{'Content-Range':`bytes */${info.size}`});res.end();return;
      }
      status=206;
    }
    const headers={'Content-Type':mime[name.split('.').pop()] || 'application/octet-stream','Content-Length':end-start+1,'Accept-Ranges':'bytes','Cache-Control': name.endsWith('.mp3')?'public, max-age=31536000, immutable':'no-cache'};
    if(status===206)headers['Content-Range']=`bytes ${start}-${end}/${info.size}`;
    res.writeHead(status,headers);
    res.end(req.method==='HEAD'?undefined:(await readFile(path)).subarray(start,end+1));
  } catch { res.writeHead(404); res.end(); }
}).listen(Number(process.env.PORT || 8080), '0.0.0.0', () => console.log(`Hezi ready: http://localhost:${process.env.PORT || 8080}`));
