"""GUI geometry regression; run with a display (xvfb-run on Linux)."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
from desktop import app

class LayoutTests(unittest.TestCase):
    def test_controls_fit_small_and_normal_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(app,'DATA',Path(folder)), patch.object(app,'CONFIG',Path(folder)/'settings.json'):
                root=tk.Tk()
                try:
                    client=app.App(root)
                    for size in ('820x640','1080x800'):
                        root.geometry(size);root.update()
                        widgets=[client.input,client.mic,client.send_button,client.wave]
                        def buttons(parent):
                            for child in parent.winfo_children():
                                if child.winfo_class() in ('TButton','TRadiobutton','TCheckbutton'):widgets.append(child)
                                buttons(child)
                        buttons(root)
                        for widget in widgets:
                            self.assertTrue(widget.winfo_ismapped(),(size,str(widget)))
                            x=widget.winfo_rootx()-root.winfo_rootx()
                            y=widget.winfo_rooty()-root.winfo_rooty()
                            self.assertGreaterEqual(x,0)
                            self.assertGreaterEqual(y,0)
                            self.assertLessEqual(x+widget.winfo_width(),root.winfo_width())
                            self.assertLessEqual(y+widget.winfo_height(),root.winfo_height())
                finally:root.destroy()

if __name__=='__main__':unittest.main()
