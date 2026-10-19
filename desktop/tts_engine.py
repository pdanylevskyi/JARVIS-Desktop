"""Isolated CPU Piper process; stdin text, stdout NDJSON WAV chunks."""
import base64,io,json,re,sys,wave
from pathlib import Path
from piper import PiperVoice,SynthesisConfig
base=Path(__file__).resolve().parent.parent
voice=PiperVoice.load(str(base/'models/piper/uk_UA-ukrainian_tts-medium.onnx'),use_cuda=False)
text=sys.stdin.read(100001)
if len(text)>20000:raise ValueError('Озвучка підтримує до 20 000 символів за відповідь.')
# Keep sentences intact when possible; never feed unbounded paragraphs to TTS.
parts=re.split(r'(?<=[.!?…])\s+|\n+',text)
chunks=[];current=''
for part in parts:
 while len(part)>500:
  cut=part.rfind(' ',0,500);cut=cut if cut>100 else 500
  if current:chunks.append(current);current=''
  chunks.append(part[:cut]);part=part[cut:].strip()
 if len(current)+len(part)>500 and current:chunks.append(current);current=''
 current=(current+' '+part).strip()
if current:chunks.append(current)
config=SynthesisConfig(speaker_id=1,length_scale=1.06,noise_scale=.55,noise_w_scale=.65)
for text in chunks:
 out=io.BytesIO()
 with wave.open(out,'wb') as wav:voice.synthesize_wav(text.lower(),wav,syn_config=config)
 print(json.dumps({'type':'audio','value':base64.b64encode(out.getvalue()).decode()}),flush=True)
