"""Native build on each OS; run with the desktop virtualenv Python."""
from pathlib import Path
import os
import subprocess
import sys
root = Path(__file__).resolve().parent.parent
dist = Path(os.environ.get('JARVIS_DIST_DIR', str(root/'dist')))
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
    '--name', 'JARVIS', '--distpath', str(dist), '--paths', str(root),
    '--collect-all', 'sounddevice', '--collect-all', 'webview',
    *(['--hidden-import','CoreLocation','--hidden-import','Quartz','--hidden-import','ApplicationServices','--hidden-import','pyautogui._pyautogui_osx','--collect-all','PIL'] if sys.platform=='darwin' else []),
    '--add-data', f'{root / "desktop/model_catalog.json"}:desktop',
    '--exclude-module', 'webview.__pyinstaller',
    '--icon', str(root/'desktop/assets'/('jarvis.icns' if sys.platform=='darwin' else 'jarvis.ico' if sys.platform=='win32' else 'jarvis.png')),
    '--add-data', f'{root / "desktop/assets/jarvis.png"}:desktop/assets',
    '--add-data', f'{root / "desktop/ui"}:desktop/ui',
    '--add-data', f'{root / "desktop/assets/DejaVuSans.ttf"}:desktop/assets',
    '--add-data', f'{root / "desktop/assets/LICENSE_DEJAVU"}:desktop/assets',
    str(root/'desktop/entry.py')], cwd=root, check=True)

if sys.platform == 'darwin':
    import plistlib
    plist = dist/'JARVIS.app/Contents/Info.plist'
    data = plistlib.loads(plist.read_bytes())
    data['NSMicrophoneUsageDescription'] = 'Запис голосу для розпізнавання на вашому сервері Ubuntu через SSH.'
    data['NSLocationUsageDescription'] = 'Показ погоди для вашого місця. Координати передаються Open-Meteo лише за вашим запитом.'
    data['NSLocationWhenInUseUsageDescription'] = 'Показ місцевої погоди за вашим розташуванням.'
    data['CFBundleIdentifier'] = 'app.jarvis.community.preview'
    data['NSLocalNetworkUsageDescription'] = 'JARVIS підключається через SSH до вашого Ubuntu в локальній мережі для чату, голосу та роботи з дозволеними папками.'
    plist.write_bytes(plistlib.dumps(data))
    subprocess.run(['xattr', '-cr', str(dist/'JARVIS.app')], check=True)
    subprocess.run(['codesign','--force','--deep','--sign','-',str(dist/'JARVIS.app')],check=True)
    subprocess.run(['codesign','--verify','--deep','--strict',str(dist/'JARVIS.app')],check=True)
