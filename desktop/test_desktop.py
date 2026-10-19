import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from .files import Files, drawing
from . import agent


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base/'allowed'; self.root.mkdir()
        self.files = Files([self.root])

    def tearDown(self):
        self.temp.cleanup()

    def test_traversal_absolute_hidden_and_unknown_root(self):
        for path in ('../outside', str(self.base/'outside'), '.ssh/private', 'a/../../outside'):
            with self.assertRaises(ValueError): self.files.path(0, path)
        with self.assertRaises(ValueError): self.files.path(-1, 'a')
        with self.assertRaises(ValueError): self.files.path(True, 'a')

    def test_symlink_escape(self):
        try:
            (self.root/'escape').symlink_to(self.base, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink privilege unavailable on this Windows host')
        with self.assertRaises(ValueError): self.files.call('write_text', {'path':'escape/out.txt','text':'bad'})
        with self.assertRaises(ValueError): self.files.call('read_document', {'path':'escape/out.txt'})

    def test_no_overwrite_and_no_code_execution(self):
        self.files.call('write_text', {'path':'notes/plan.txt', 'text':'План майстерні'})
        with self.assertRaises(FileExistsError): self.files.call('write_text', {'path':'notes/plan.txt', 'text':'changed'})
        self.assertEqual((self.root/'notes/plan.txt').read_text(encoding='utf-8'), 'План майстерні')
        self.files.call('write_text', {'path':'example.py', 'text':'# text only'})
        with self.assertRaises(ValueError): self.files.call('shell', {'command':'echo wrong'})

    def test_document_roundtrip(self):
        for ext in ('pdf','docx'):
            self.files.call('create_document', {'path':f'note.{ext}', 'title':'Майстерня', 'sections':[{'heading':'Інструменти','text':'Штангенциркуль та дриль. <b>Це звичайний текст.</b>'}]})
            content = self.files.call('read_document', {'path':f'note.{ext}'})['text']
            self.assertIn('Штангенциркуль', content)
            self.assertIn('<b>', content)

    def test_legacy_commands_keep_scope_and_reset_budget(self):
        from .commands import prepare
        quiet=lambda *a:None
        self.assertEqual(prepare('/flash привіт',self.base,[self.root],quiet)[1]['max_tokens'],8192)
        self.assertEqual(prepare('/long поясни',self.base,[self.root],quiet)[1]['max_tokens'],8192)
        self.assertEqual(prepare('привіт',self.base,[self.root],quiet)[1]['max_tokens'],4096)
        (self.root/'note.txt').write_text('Документ',encoding='utf-8')
        self.assertIn('Документ',prepare('/file note.txt',self.base,[self.root],quiet)[1]['context'])
        with self.assertRaises(ValueError):prepare('/file ../secret.txt',self.base,[self.root],quiet)

    def test_drawing_geometry(self):
        self.assertTrue(drawing('Ескіз', [{'type':'rect','x':10,'y':10,'width':50,'height':40}]).startswith(b'%PDF'))
        for element in ({'type':'circle','x':5,'y':5,'radius':10}, {'type':'rect','x':250,'y':10,'width':30,'height':20}, {'type':'text','x':0,'y':float('nan')}):
            with self.assertRaises(ValueError): drawing('Bad', [element])


class AgentTests(unittest.TestCase):
    def test_fifteen_minute_limit_replaces_step_cap(self):
        replies=[{'role':'assistant','content':'','tool_calls':[{'id':str(i),'type':'function','function':{'name':'list_files','arguments':'{"root":0,"path":"."}'}}]} for i in range(14)]
        replies.append({'role':'assistant','content':'Готово'})
        with tempfile.TemporaryDirectory() as folder, patch.object(agent,'completion',side_effect=replies) as model:
            result=agent.run('unused',[folder],[],'Тест',lambda *a:None,threading.Event())
            self.assertEqual(model.call_count,15)
            self.assertEqual(result[-1]['content'],'Готово')
        with tempfile.TemporaryDirectory() as folder, patch.object(agent.time,'monotonic',side_effect=[0,900]), patch.object(agent,'completion') as model:
            with self.assertRaisesRegex(RuntimeError,'15 хвилин'):
                agent.run('unused',[folder],[],'Тест',lambda *a:None,threading.Event())
            model.assert_not_called()

    def test_tool_results_and_history(self):
        replies = [{'role':'assistant','content':'','tool_calls':[{'id':'1','type':'function','function':{'name':'write_text','arguments':json.dumps({'root':0,'path':'hello.txt','text':'Вітаю'})}}]}, {'role':'assistant','content':'Готово, сер.'}]
        with tempfile.TemporaryDirectory() as folder, patch.object(agent, 'completion', side_effect=replies) as model:
            events=[]
            result = agent.run('unused',[folder],[],'Створи файл',lambda k,v: events.append((k,v)),threading.Event(),{'approve':lambda _:True})
            self.assertEqual(Path(folder,'hello.txt').read_text(encoding='utf-8'),'Вітаю')
            self.assertEqual(result[-1]['content'],'Готово, сер.')
            self.assertTrue(any(k=='saved' for k,v in events))
            self.assertTrue(any(m['role']=='tool' for m in model.call_args.args[1]))

    def test_reasoning_modes_and_status(self):
        wire=b'data: {"choices":[{"delta":{"reasoning_content":"internal"}}]}\n\ndata: {"choices":[{"delta":{"content":"Done"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n'
        for options,budget,total in [({},4096,8192),({'thinking_budget':0,'max_tokens':5000},0,5000),({'thinking_budget':0,'max_tokens':8192},0,8192),({'thinking_budget':8192,'max_tokens':8192},8192,16384)]:
            events=[]
            with patch('urllib.request.urlopen',return_value=io.BytesIO(wire)) as call:
                agent.completion('http://localhost',[],lambda k,v:events.append((k,v)),options=options)
            body=json.loads(call.call_args.args[0].data)
            self.assertEqual(body['reasoning_budget_tokens'],budget)
            self.assertEqual(body['max_tokens'],total)
            self.assertEqual(body['chat_template_kwargs']['enable_thinking'],budget>0)
            self.assertNotIn(('text','internal'),events)
            self.assertIn(('phase','Міркування J.A.R.V.I.S.…'),events)

    def test_cancel_prevents_tools(self):
        stop=threading.Event(); stop.set()
        with tempfile.TemporaryDirectory() as folder, patch.object(agent,'completion') as model:
            with self.assertRaises(RuntimeError): agent.run('',[folder],[],'test',lambda *a:None,stop)
            model.assert_not_called()

    def test_fragmented_sse(self):
        events = [{'choices':[{'delta':{'tool_calls':[{'index':0,'id':'t1','function':{'name':'write_text','arguments':'{"path":'}}]}}]}, {'choices':[{'delta':{'tool_calls':[{'index':0,'function':{'arguments':'"ok.txt"}'}}]},'finish_reason':'tool_calls'}]}]
        wire = b''.join(b'data: '+json.dumps(e).encode()+b'\n\n' for e in events)+b'data: [DONE]\n'
        observed=[]
        with patch('urllib.request.urlopen', return_value=io.BytesIO(wire)):
            reply = agent.completion('http://127.0.0.1:8080',[],lambda k,v:observed.append((k,v)))
        self.assertIn(('status','Модель готує наступний крок…'),observed)
        self.assertIn(('phase','Генерую параметри інструмента…'),observed)
        self.assertEqual(json.loads(reply['tool_calls'][0]['function']['arguments']),{'path':'ok.txt'})


class VoiceTests(unittest.TestCase):
    def test_server_pcm_and_model(self):
        import base64
        import numpy as np
        from types import SimpleNamespace
        from desktop.worker import transcribe
        with patch('faster_whisper.WhisperModel') as model:
            model.return_value.transcribe.return_value = ([SimpleNamespace(text=' Створи документ ')], None)
            result=transcribe(base64.b64encode(np.zeros(1600,dtype=np.int16).tobytes()).decode())
            self.assertEqual(result,'Створи документ')
            self.assertEqual(model.return_value.transcribe.call_args.args[0].dtype,np.float32)
            self.assertEqual(model.call_args.kwargs['device'],'cpu')
            self.assertTrue(model.call_args.kwargs['local_files_only'])
            self.assertIn('large-v3-turbo',model.call_args.args[0])

    def test_server_translation(self):
        import sys
        from types import SimpleNamespace
        from desktop import worker
        events=[]
        request=io.BytesIO(b'{"operation":"chat","prompt":"test"}\n')
        turns=[{'role':'assistant','content':'This is the answer.'}]
        with patch.object(sys,'stdin',SimpleNamespace(buffer=request)), patch.object(worker,'roots',return_value=['/server']), patch.object(worker.agent,'run',return_value=turns), patch.object(worker,'emit',side_effect=lambda k,v='':events.append((k,v))), patch('self_translation.translate',return_value='Це відповідь.') as translator:
            worker.main()
        self.assertEqual(translator.call_args.args[1],'http://127.0.0.1:8080')
        self.assertIn(('translation_begin',''),events)
        self.assertEqual(turns[-1]['content'],'Це відповідь.')


if __name__ == '__main__': unittest.main()
