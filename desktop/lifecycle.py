"""Stop a worker when its owning SSH connection closes; queue approval replies."""
import json,os,queue,signal,threading
class InputSession:
    def __init__(self,stream,cancelled,on_disconnect=None):
        self.replies=queue.Queue();self.cancelled=cancelled
        self.on_disconnect=on_disconnect or (lambda:os._exit(0))
        def read():
            while True:
                line=stream.readline(4097)
                if not line:
                    cancelled.set();self.on_disconnect();return
                if len(line)>4096:self.replies.put({});continue
                try:self.replies.put(json.loads(line))
                except ValueError:self.replies.put({})
        threading.Thread(target=read,daemon=True).start()
    def approved(self,timeout=120):
        try:return self.replies.get(timeout=timeout).get('approved') is True and not self.cancelled.is_set()
        except queue.Empty:return False

def terminate_on_signal(cancelled):
    def stop(*_):
        cancelled.set()
        raise SystemExit(0)
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGHUP,stop)
