"""JARVIS thin client: UI and microphone only; all AI and file actions use SSH."""
import array
import base64
from collections import deque
import json
import math
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter import font as tkfont
from . import remote
from terminal_format import TerminalFormatter

DATA = Path.home() / '.jarvis-public'
CONFIG = DATA / 'settings.json'
BG, PANEL, CYAN, TEXT, MUTED = '#000000', '#020b16', '#36dcff', '#ccefff', '#5887a6'


def pcm_level(data):
    samples = array.array('h', data)
    if not samples: return 0.0
    return min(1.0, math.sqrt(sum(v*v for v in samples) / len(samples)) / 5000)


class App:
    def __init__(self, window):
        self.window = window
        self.events = queue.Queue()
        self.formatter=TerminalFormatter(live=True)
        self.history, self.audio, self.roots = [], [], []
        self.attachment=None
        self.busy, self.connected = False, False
        self.recording = None
        self.cancelled = threading.Event()
        self.levels = deque([0.0]*90, maxlen=90)
        self.level, self.record_started, self.answer_mark = 0.0, 0, False
        DATA.mkdir(exist_ok=True)
        self.settings = {'host':'','key':str(Path.home()/'.ssh/id_ed25519')}
        if CONFIG.exists():
            try:
                old=json.loads(CONFIG.read_text(encoding='utf-8'))
                self.settings.update({k:old[k] for k in ('host','key') if k in old})
            except (ValueError,OSError): pass
        self.persist()  # Drop obsolete client-side folder permissions.
        window.title('J.A.R.V.I.S. • COMMAND INTERFACE')
        icon_path=Path(__file__).parent/'assets/jarvis.png'
        if icon_path.exists():
            self.app_icon=tk.PhotoImage(file=str(icon_path)).subsample(8)
            window.iconphoto(True,self.app_icon)
        window.geometry('1080x800'); window.minsize(820,640); window.configure(bg=BG)
        window.columnconfigure(0,weight=1)
        window.rowconfigure(2,weight=1)
        style=ttk.Style(); style.theme_use('clam')
        style.configure('.',background=BG,foreground=TEXT,font=('Helvetica',11))
        style.configure('TButton',background=PANEL,foreground=CYAN,bordercolor='#164970',padding=(14,9))
        style.map('TButton',background=[('active','#06223c')],foreground=[('disabled',MUTED)])
        style.configure('TEntry',fieldbackground=PANEL,foreground=TEXT,insertcolor=CYAN)
        header=tk.Frame(window,bg=BG);header.grid(row=0,column=0,sticky='ew',padx=24,pady=(12,8))
        arc=tk.Canvas(header,width=64,height=64,bg=BG,highlightthickness=0);arc.pack(side='left',padx=(0,16))
        for inset in (4,11,20): arc.create_oval(inset,inset,64-inset,64-inset,outline=CYAN,width=2)
        arc.create_line(32,0,32,64,fill='#164970');arc.create_line(0,32,64,32,fill='#164970')
        labels=tk.Frame(header,bg=BG);labels.pack(side='left')
        tk.Label(labels,text='J.A.R.V.I.S.',font=('Helvetica',25,'bold'),bg=BG,fg=CYAN).pack(anchor='w')
        tk.Label(labels,text='ПЕРСОНАЛЬНИЙ АСИСТЕНТ  /  СЕРВЕРНИЙ РЕЖИМ',font=('Helvetica',9),bg=BG,fg=MUTED).pack(anchor='w')
        ttk.Button(header,text='Підключення',command=self.connection).pack(side='right')
        nav=tk.Frame(window,bg=BG);nav.grid(row=1,column=0,sticky='ew',padx=24,pady=(0,8))
        ttk.Button(nav,text='Папки сервера',command=self.folders).pack(side='left')
        ttk.Button(nav,text='Новий діалог',command=self.clear).pack(side='left',padx=8)
        ttk.Button(nav,text='Копіювати',command=self.copy_text).pack(side='left')
        ttk.Button(nav,text='Зображення',command=self.attach_image).pack(side='left',padx=(8,0))
        tk.Label(nav,text='SSH  •  БЕЗ ХМАРНИХ СЕРВІСІВ',bg=BG,fg=MUTED,font=('Helvetica',9)).pack(side='right')
        self.chat_font=tkfont.nametofont('TkFixedFont').copy();self.chat_font.configure(size=12)
        self.log=scrolledtext.ScrolledText(window,height=6,width=40,wrap='word',font=self.chat_font,spacing1=2,spacing3=3,padx=20,pady=20,bg=PANEL,fg=TEXT,insertbackground=CYAN,selectbackground='#075d94',relief='flat',state='disabled')
        self.log.grid(row=2,column=0,sticky='nsew',padx=24)
        for shortcut in ('<Control-c>', '<Control-C>', '<Control-Shift-C>'):
            self.log.bind(shortcut,self.copy_text)
        if window.tk.call('tk','windowingsystem') == 'aqua':
            self.log.bind('<Command-c>',self.copy_text)
        self.copy_menu=tk.Menu(window,tearoff=False)
        self.copy_menu.add_command(label='Копіювати виділене / відповідь',command=self.copy_text)
        self.copy_menu.add_command(label='Копіювати весь діалог',command=lambda:self.copy_text(all_text=True))
        self.log.bind('<Button-3>',self.show_copy_menu)
        if window.tk.call('tk','windowingsystem') == 'aqua':
            self.log.bind('<Button-2>',self.show_copy_menu)
            self.log.bind('<Control-Button-1>',self.show_copy_menu)
        self.log.tag_config('action',foreground=CYAN);self.log.tag_config('error',foreground='#a0dcff')
        self.wave=tk.Canvas(window,height=65,bg=BG,highlightthickness=0);self.wave.grid(row=3,column=0,sticky='ew',padx=24,pady=(4,0))
        modebar=tk.Frame(window,bg=BG);modebar.grid(row=4,column=0,sticky='ew',padx=24,pady=(0,8))
        self.mode=tk.StringVar(value='normal')
        for column,(label,value) in enumerate([('Звичайний','normal'),('⚡ Flash','flash'),('Long','long')]):
            ttk.Radiobutton(modebar,text=label,variable=self.mode,value=value).grid(row=0,column=column,sticky='w',padx=(0,8))
        self.web_search=tk.BooleanVar(value=False)
        ttk.Checkbutton(modebar,text='Пошук в інтернеті',variable=self.web_search).grid(row=1,column=0,columnspan=5,sticky='w',pady=(4,0))
        self.phase=tk.StringVar(value='')
        tk.Label(window,textvariable=self.phase,bg=BG,fg=CYAN,anchor='w').grid(row=8,column=0,sticky='ew',padx=24,pady=(0,6))
        attachmentbar=tk.Frame(window,bg=BG)
        attachmentbar.grid(row=9,column=0,sticky='ew',padx=24,pady=(0,6))
        self.image_status=tk.StringVar(value='Без зображення')
        tk.Label(attachmentbar,textvariable=self.image_status,bg=BG,fg=MUTED).pack(side='left')
        ttk.Button(attachmentbar,text='Прибрати зображення',command=self.remove_image).pack(side='right')
        self.input=tk.Text(window,height=3,wrap='word',font=('Helvetica',13),bg=PANEL,fg=TEXT,insertbackground=CYAN,relief='flat',padx=12,pady=10)
        self.input.grid(row=5,column=0,sticky='ew',padx=24,pady=(0,8));self.input.bind('<Control-Return>',lambda e:self.send())
        for shortcut in ('<Control-v>','<Control-V>','<Shift-Insert>','<<Paste>>'):
            self.input.bind(shortcut,self.paste_text)
        if window.tk.call('tk','windowingsystem')=='aqua':
            self.input.bind('<Command-v>',self.paste_text)
            self.input.bind('<Command-V>',self.paste_text)
        self.paste_menu=tk.Menu(window,tearoff=False)
        self.paste_menu.add_command(label='Вставити текст',command=self.paste_text)
        self.input.bind('<Button-3>',self.show_paste_menu)
        if window.tk.call('tk','windowingsystem')=='aqua':
            self.input.bind('<Button-2>',self.show_paste_menu)
            self.input.bind('<Control-Button-1>',self.show_paste_menu)
        controls=tk.Frame(window,bg=BG);controls.grid(row=6,column=0,sticky='ew',padx=24)
        ttk.Button(controls,text='Вставити',command=self.paste_text).pack(side='left',padx=(0,8))
        self.mic=ttk.Button(controls,text='●  Голос',command=self.voice);self.mic.pack(side='left')
        self.record_label=tk.Label(controls,text='Мікрофон вимкнений',bg=BG,fg=MUTED);self.record_label.pack(side='left',padx=12)
        self.send_button=ttk.Button(controls,text='НАДІСЛАТИ  →',command=self.send);self.send_button.pack(side='right')
        ttk.Button(controls,text='Зупинити',command=self.cancelled.set).pack(side='right',padx=8)
        self.status=tk.StringVar(value='Підключіть Ubuntu. На клієнті немає файлового агента або моделей.')
        tk.Label(window,textvariable=self.status,bg=BG,fg=MUTED,anchor='w',wraplength=1000).grid(row=7,column=0,sticky='ew',padx=24,pady=(8,10))
        self.append('Системи готові, сер. Очікую підключення до вашого комп’ютера.\n','action')
        window.after(50,self.poll);window.after(33,self.animate);window.protocol('WM_DELETE_WINDOW',self.close)

    def attach_image(self):
        if self.busy:return
        name=filedialog.askopenfilename(parent=self.window,title='Зображення для Джарвіса',filetypes=[('Зображення','*.png *.jpg *.jpeg *.webp')])
        if not name:return
        try:
            path=Path(name)
            if path.stat().st_size>10*1024*1024:raise ValueError('Максимум 10 МБ.')
            with path.open('rb') as f:raw=f.read(10*1024*1024+1)
            if len(raw)>10*1024*1024:raise ValueError('Максимум 10 МБ.')
            self.attachment={'name':path.name,'data':base64.b64encode(raw).decode('ascii')}
            self.image_status.set('Прикріплено: '+path.name[:48])
        except Exception as exc:messagebox.showerror('Зображення',str(exc),parent=self.window)

    def remove_image(self):
        self.attachment=None;self.image_status.set('Без зображення')

    def persist(self):
        CONFIG.write_text(json.dumps(self.settings,ensure_ascii=False,indent=2),encoding='utf-8')

    def append(self,text,tag=None):
        if not text:return
        follow=self.log.yview()[1]>=0.98
        self.log.configure(state='normal');self.log.insert('end',text,tag or ());self.log.configure(state='disabled')
        if follow:self.log.see('end')

    def paste_text(self,event=None):
        try:text=self.window.clipboard_get()
        except tk.TclError:
            self.status.set('Буфер обміну не містить тексту.');return 'break'
        self.input.focus_set()
        self.input.edit_separator()
        try:self.input.delete('sel.first','sel.last')
        except tk.TclError:pass
        self.input.insert('insert',text)
        self.input.see('insert');self.input.edit_separator()
        return 'break'

    def show_paste_menu(self,event):
        try:self.paste_menu.tk_popup(event.x_root,event.y_root)
        finally:self.paste_menu.grab_release()
        return 'break'

    def copy_text(self,event=None,all_text=False):
        if all_text:
            text=self.log.get('1.0','end-1c')
        else:
            try:text=self.log.get('sel.first','sel.last')
            except tk.TclError:
                if self.answer_mark:text=self.log.get('answer_start','end-1c')
                else:text=next((m['content'] for m in reversed(self.history) if m['role']=='assistant'),'')
        if text.strip():
            self.window.clipboard_clear();self.window.clipboard_append(text)
            self.status.set('Скопійовано до буфера обміну.')
        else:self.status.set('Виділіть текст для копіювання.')
        return 'break'

    def show_copy_menu(self,event):
        try:self.copy_menu.tk_popup(event.x_root,event.y_root)
        finally:self.copy_menu.grab_release()
        return 'break'

    def clear(self):
        if self.busy or self.recording:return
        self.history.clear();self.answer_mark=False;self.remove_image()
        self.log.configure(state='normal');self.log.delete('1.0','end');self.log.configure(state='disabled')

    def launch(self,payload):
        self.formatter=TerminalFormatter(live=True)
        self.answer_mark=False
        self.busy=True;self.send_button.configure(state='disabled');self.cancelled.clear()
        def worker():
            try: remote.request(dict(self.settings),payload,lambda k,v:self.events.put((k,v)),self.cancelled)
            except Exception as exc:self.events.put(('error',str(exc)))
            finally:self.events.put(('idle',''))
        threading.Thread(target=worker,daemon=True).start()

    def folders(self):
        if self.busy:return
        if not self.connected:self.connection();return
        dialog=tk.Toplevel(self.window);dialog.title('Дозволені папки на Ubuntu');dialog.configure(bg=BG)
        tk.Label(dialog,text='Абсолютні шляхи НА СЕРВЕРІ, по одному на рядок.',bg=BG,fg=TEXT).pack(padx=16,pady=12)
        box=tk.Text(dialog,width=70,height=8,bg=PANEL,fg=TEXT,insertbackground=CYAN);box.pack(padx=16)
        box.insert('1.0','\n'.join(self.roots))
        def save():
            values=[s.strip() for s in box.get('1.0','end').splitlines() if s.strip()]
            dialog.destroy();self.history.clear();self.launch({'operation':'set_roots','roots':values})
        ttk.Button(dialog,text='Зберегти на сервері',command=save).pack(pady=12)

    def connection(self):
        if self.busy or self.recording:return
        dialog=tk.Toplevel(self.window);dialog.title('SSH • Ubuntu');dialog.configure(bg=BG)
        host,key=tk.StringVar(value=self.settings['host']),tk.StringVar(value=self.settings['key'])
        for label,value in [('SSH користувач@сервер',host),('SSH ключ на клієнті',key)]:
            tk.Label(dialog,text=label,bg=BG,fg=TEXT).pack(anchor='w',padx=16,pady=(12,4))
            ttk.Entry(dialog,textvariable=value,width=60).pack(padx=16)
        ttk.Button(dialog,text='Обрати ключ',command=lambda:key.set(filedialog.askopenfilename(parent=dialog) or key.get())).pack(pady=8)
        def connect():
            if not Path(key.get()).expanduser().is_file():
                messagebox.showerror('SSH','Файл ключа не знайдено.',parent=dialog);return
            self.settings.update(host=host.get().strip(),key=key.get());self.persist();dialog.destroy()
            self.connected=False;self.status.set('Підключаю сервер…');self.launch({'operation':'status'})
        ttk.Button(dialog,text='Підключитися',command=connect).pack(pady=12)

    def send(self):
        if self.busy or self.recording:return
        prompt=self.input.get('1.0','end').strip()
        if not prompt and self.attachment:prompt='Опиши це зображення українською.'
        if not prompt:return
        if prompt=='/exit':self.close();return
        if prompt=='/clear':self.input.delete('1.0','end');self.clear();return
        if prompt=='/help':
            self.input.delete('1.0','end')
            self.append('\n/clear · /exit · /flash запит · /long запит · /workshop запит\n/file шлях · /search запит · /memory · /memory add текст · /memory edit\n','action');return
        if not self.connected:self.connection();return
        if not prompt.startswith('/') and self.mode.get()!='normal':prompt='/'+self.mode.get()+' '+prompt
        self.mode.set('normal')
        self.phase.set('Очікую відповідь сервера…')
        if len(prompt)>12000:messagebox.showerror('Запит','Максимум 12 000 символів.');return
        self.input.delete('1.0','end');self.append('\nВи: '+prompt+'\n','action');self.append('J.A.R.V.I.S.: ')
        self.answer_mark=False;self.status.set('Сервер готує відповідь…')
        payload={'operation':'chat','prompt':prompt,'history':self.history[-8:],'search_enabled':self.web_search.get()}
        if self.attachment:
            payload['image']=dict(self.attachment)
            self.append('[Зображення: '+self.attachment['name']+']\n','action')
        self.launch(payload)

    def voice(self):
        if self.busy:return
        if not self.connected:self.connection();return
        if self.recording:
            self.recording.stop();self.recording.close();self.recording=None
            self.level=0;self.mic.configure(text='●  Голос');self.record_label.configure(text='Розпізнавання на Ubuntu…')
            pcm=b''.join(self.audio);self.audio.clear()
            self.launch({'operation':'transcribe','audio':base64.b64encode(pcm).decode('ascii')})
            self.status.set('Whisper large-v3-turbo розпізнає українську на сервері.');return
        try:
            import sounddevice as sd
            import time
            self.audio=[];self.levels.clear();self.levels.extend([0.0]*90)
            def capture(data,frames,time_info,status):
                chunk=bytes(data);self.audio.append(chunk);self.level=pcm_level(chunk)
            self.recording=sd.RawInputStream(samplerate=16000,channels=1,dtype='int16',blocksize=800,callback=capture)
            self.recording.start();self.record_started=time.monotonic()
            self.mic.configure(text='■  Завершити запис');self.status.set('Хвиля показує реальний рівень мікрофона. Текст з’явиться після завершення запису.')
            current=self.recording;self.window.after(60000,lambda:self.voice() if self.recording is current else None)
        except Exception as exc:
            if self.recording:self.recording.close()
            self.recording=None;messagebox.showerror('Мікрофон',str(exc))

    def animate(self):
        import time
        width=max(self.wave.winfo_width(),300);height=65;middle=height/2
        self.levels.append(self.level if self.recording else 0.0)
        self.wave.delete('all');self.wave.create_line(0,middle,width,middle,fill='#103857')
        step=width/len(self.levels)
        for i,level in enumerate(self.levels):
            amplitude=1+level*26
            self.wave.create_line(i*step,middle-amplitude,i*step,middle+amplitude,fill=CYAN if self.recording else '#164970',width=3)
        if self.recording:
            elapsed=int(time.monotonic()-self.record_started)
            self.record_label.configure(text=f'ЗАПИС  {elapsed//60:02}:{elapsed%60:02}  /  01:00',fg=CYAN)
        self.window.after(33,self.animate)

    def edit_memory(self,before):
        dialog=tk.Toplevel(self.window);dialog.title('Пам’ять майстерні • Ubuntu');dialog.configure(bg=BG)
        box=scrolledtext.ScrolledText(dialog,width=85,height=25,bg=PANEL,fg=TEXT,insertbackground=CYAN)
        box.pack(fill='both',expand=True,padx=12,pady=12);box.insert('1.0',before)
        def save():
            if self.busy:return
            after=box.get('1.0','end-1c');dialog.destroy()
            self.launch({'operation':'memory_save','before':before,'after':after})
        ttk.Button(dialog,text='Зберегти на Ubuntu',command=save).pack(pady=12)

    def reset_answer(self):
        self.formatter=TerminalFormatter(live=True)
        if self.answer_mark:
            self.log.configure(state='normal');self.log.delete('answer_start','end-1c');self.log.configure(state='disabled')

    def poll(self):
        while True:
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='text':
                if not self.answer_mark:
                    self.log.mark_set('answer_start','end-1c');self.log.mark_gravity('answer_start','left');self.answer_mark=True
                self.append(self.formatter.feed(value))
            elif kind=='phase':self.phase.set(value)
            elif kind=='translation_begin':self.reset_answer();self.phase.set('Переклад українською…')
            elif kind=='replace_answer':self.reset_answer();self.append(self.formatter.feed(value)+self.formatter.finish())
            elif kind=='action':self.status.set('Сервер виконує: '+value)
            elif kind=='saved':self.append('\nФайл на Ubuntu: '+value+'\n','action')
            elif kind=='memory_edit':self.edit_memory(value)
            elif kind=='roots':self.roots=value
            elif kind=='status':
                if value.startswith('Ubuntu підключено'):self.connected=True
                self.status.set(value)
            elif kind=='transcript':self.input.insert('end',value);self.record_label.configure(text='Текст готовий — перевірте та надішліть',fg=MUTED)
            elif kind=='history':self.history=(self.history+value)[-8:]
            elif kind in ('error','warning'):self.append('\n'+value+'\n','error');self.status.set(value[:180])
            elif kind=='done':
                self.append(self.formatter.finish())
                if hasattr(self,'phase'):self.phase.set('Готово')
            elif kind=='idle':
                self.append(self.formatter.finish());self.busy=False;self.send_button.configure(state='normal')
        self.window.after(50,self.poll)

    def close(self):
        self.cancelled.set()
        if self.recording:self.recording.stop();self.recording.close()
        self.window.destroy()


def main():
    from .webapp import main as web_main
    web_main()


if __name__=='__main__':main()
