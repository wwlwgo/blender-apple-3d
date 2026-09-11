"""Record the actual Three.js canvas at deterministic 30 fps."""
import base64
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent / 'apple_video'
FRAMES=ROOT / 'frames'
FRAMES.mkdir(exist_ok=True)
preview='--preview' in sys.argv
indices=[0,75,150,225] if preview else range(300)
errors=[]
with sync_playwright() as p:
    options={'headless': True}
    if os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'):
        options['executable_path']=os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE']
    if sys.platform == 'darwin':
        options['args']=['--use-angle=metal']
    browser=p.chromium.launch(**options)
    page=browser.new_page(viewport={'width':1080,'height':1920},device_scale_factor=1)
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.on('console',lambda m: errors.append(m.text) if m.type=='error' else None)
    page.goto((ROOT/'capture.html').as_uri(),wait_until='networkidle')
    page.wait_for_function('window.captureReady === true',timeout=60000)
    if errors:
        raise RuntimeError('\n'.join(errors))
    for i in indices:
        path=FRAMES/f'frame_{i:04d}.png'
        data=page.evaluate('(i)=>window.captureFrame(i)',i)
        path.write_bytes(base64.b64decode(data.split(',',1)[1]))
        if i%30==0 or preview:
            print(f'Captured frame {i}/299',flush=True)
    if errors:
        raise RuntimeError('\n'.join(errors))
    browser.close()
print('CAPTURE_COMPLETE',flush=True)
