import array
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from .app import pcm_level
from . import remote


class ClientTests(unittest.TestCase):
    def test_wave_is_actual_audio(self):
        self.assertEqual(pcm_level(bytes(800)),0)
        quiet=pcm_level(array.array('h',[100,-100]*100).tobytes())
        loud=pcm_level(array.array('h',[4000,-4000]*100).tobytes())
        self.assertGreater(loud,quiet)
        self.assertLessEqual(loud,1)

    def test_no_local_agent_or_models(self):
        code="import sys; import desktop.app; assert not any(m in sys.modules for m in ('desktop.files','desktop.agent','faster_whisper','reportlab'))"
        subprocess.run([sys.executable,'-c',code],check=True)

    def test_remote_protocol(self):
        class Input(io.BytesIO):
            def close(self): self.saved=self.getvalue();super().close()
        process=MagicMock();process.stdin=Input()
        process.stdout=io.BytesIO(b'{"type":"status","value":"ready"}\n{"type":"done"}\n')
        process.stderr=io.BytesIO();process.wait.return_value=0;process.poll.return_value=0
        events=[]
        with patch('subprocess.Popen',return_value=process) as launch:
            remote.request({'host':'user@server','key':'/key'},{'operation':'status'},lambda k,v:events.append((k,v)))
        self.assertEqual(json.loads(process.stdin.saved),{'operation':'status'})
        self.assertIn('desktop.worker',launch.call_args.args[0][-1])
        self.assertIn(('status','ready'),events)

    def test_streamed_chat_formats_html_and_math(self):
        import queue
        from .app import App
        from terminal_format import TerminalFormatter
        app=App.__new__(App);app.events=queue.Queue();app.formatter=TerminalFormatter(live=True)
        app.log=MagicMock();app.window=MagicMock();app.answer_mark=False
        output=[];app.append=output.append
        for chunk in ['Маса: &lt;b&gt;2&lt;/b&gt; кг, ',r'$\alpha \cdot ',r'3^{2}$']:
            app.events.put(('text',chunk))
        app.events.put(('done',''));app.poll()
        self.assertEqual(''.join(output),'Маса: 2 кг, α · 3²')

    def test_search_switch(self):
        from .commands import prepare
        rows=[{'url':'https://example.com','title':'Source','snippet':'Text'}]
        with patch('web_search.search',return_value=rows) as search, patch('page_reader.enrich',side_effect=lambda rows:rows):
            prepare('знайди в інтернеті Python',Path('.'),[],lambda *a:None,search_enabled=False)
            search.assert_not_called()
            prepare('/flash Python',Path('.'),[],lambda *a:None,search_enabled=True)
            search.assert_called_once_with('Python')
            search.reset_mock()
            prepare('/search Python',Path('.'),[],lambda *a:None,search_enabled=False)
            search.assert_called_once_with('Python')

    def test_host_validation(self):
        with self.assertRaises(ValueError):remote.request({'host':'-oProxyCommand=bad@host','key':'x'},{},lambda *a:None)


if __name__=='__main__':unittest.main()
