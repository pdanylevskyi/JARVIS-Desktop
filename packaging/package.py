"""Package an already built native client. Never copy a repository/config directory."""
import hashlib,os,platform,re,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION=os.environ.get('JARVIS_VERSION','0.2.0')
if not re.fullmatch(r'\d+\.\d+\.\d+',VERSION):raise ValueError('Version must be X.Y.Z')
OUT=ROOT/'release';OUT.mkdir(exist_ok=True)

def main():
 system=platform.system();arch=platform.machine().lower()
 if system=='Darwin':
  stage=OUT/'dmg-stage'
  if stage.exists():shutil.rmtree(stage)
  stage.mkdir();shutil.copytree(ROOT/'dist/JARVIS.app',stage/'JARVIS Community.app',symlinks=True)
  (stage/'Applications').symlink_to('/Applications')
  shutil.copy2(ROOT/'INSTALL.md',stage/'READ ME.txt')
  subprocess.run(['hdiutil','create','-volname','JARVIS Community','-srcfolder',str(stage),'-ov','-format','UDZO',str(OUT/f'JARVIS-{VERSION}-macos-{arch}.dmg')],check=True)
  shutil.rmtree(stage)
 elif system=='Windows':
  compiler=shutil.which('ISCC') or r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
  subprocess.run([compiler,str(ROOT/'packaging/windows.iss')],env={**os.environ,'JARVIS_VERSION':VERSION},check=True)
 elif system=='Linux':
  stage=OUT/'deb-stage'
  if stage.exists():shutil.rmtree(stage)
  (stage/'DEBIAN').mkdir(parents=True)
  shutil.copytree(ROOT/'dist/JARVIS',stage/'opt/jarvis-community',symlinks=True)
  (stage/'usr/bin').mkdir(parents=True);(stage/'usr/bin/jarvis-community').symlink_to('/opt/jarvis-community/JARVIS')
  appdir=stage/'usr/share/applications';appdir.mkdir(parents=True)
  (appdir/'jarvis-community.desktop').write_text('[Desktop Entry]\nType=Application\nName=JARVIS Community\nExec=/opt/jarvis-community/JARVIS\nIcon=jarvis-community\nTerminal=false\nCategories=Utility;\n')
  icons=stage/'usr/share/icons/hicolor/512x512/apps';icons.mkdir(parents=True)
  shutil.copy2(ROOT/'desktop/assets/jarvis.png',icons/'jarvis-community.png')
  debarch={'x86_64':'amd64','aarch64':'arm64'}[arch]
  (stage/'DEBIAN/control').write_text(f'Package: jarvis-community\nVersion: {VERSION}\nArchitecture: {debarch}\nMaintainer: JARVIS Community\nDepends: openssh-client, libportaudio2, libegl1, libopengl0, libxcb-cursor0, libxkbcommon-x11-0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libnss3, libasound2\nDescription: JARVIS desktop client for a user-owned Ubuntu AI server\n')
  subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(OUT/f'JARVIS-{VERSION}-linux-{debarch}.deb')],check=True)
  shutil.rmtree(stage)
 else:raise RuntimeError('Unsupported platform')
 for p in OUT.iterdir():
  if p.suffix in ('.exe','.dmg','.deb'):
   digest=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
   p.with_name(p.name+'.sha256').write_text(digest+'  '+p.name+'\n')
if __name__=='__main__':main()
