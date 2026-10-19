import unittest,threading
from unittest.mock import Mock
from desktop.mac_agent import validate,run,approved_navigation,needs_approval
class MacAgentTests(unittest.TestCase):
 def backend(self):
  b=Mock();b.observe.return_value={'app':'Test','pid':1,'image':'fake'};b.unchanged.return_value=True;return b
 def test_rejects_shell_and_bad_coordinates(self):
  for action in [{'kind':'shell','reason':'x'},{'kind':'click','reason':'x','x':float('nan'),'y':.3},{'kind':'key','reason':'x','keys':['shell']},{'kind':'open_url','reason':'x','url':'file:///etc/passwd'}]:
   with self.assertRaises(ValueError):validate(action)
 def test_denial_stops_without_effect(self):
  b=self.backend();run('test',b,lambda *_:{'kind':'click','reason':'Send message','x':.2,'y':.3},lambda _:False,Mock(),threading.Event())
  b.execute.assert_not_called()
 def test_cancel_during_approval_stops(self):
  b=self.backend();cancel=threading.Event()
  def approval(_):cancel.set();return True
  with self.assertRaises(RuntimeError):run('test',b,lambda *_:{'kind':'type','reason':'text','text':'hi'},approval,Mock(),cancel)
  b.execute.assert_not_called()
 def test_changed_screen_stops(self):
  b=self.backend();b.unchanged.return_value=False
  run('test',b,lambda *_:{'kind':'key','reason':'Send','keys':['enter']},lambda _:True,Mock(),threading.Event())
  b.execute.assert_not_called()
 def test_one_action_then_observe_before_finish(self):
  b=self.backend();planner=Mock(side_effect=[{'kind':'click','reason':'Open','x':.2,'y':.3},{'kind':'done','reason':'Verified'}]);approval=Mock(return_value=True)
  run('test',b,planner,approval,Mock(),threading.Event())
  self.assertEqual(b.observe.call_count,2);self.assertEqual(b.execute.call_count,1);approval.assert_called_once()
 def test_deadline_blocks_action(self):
  b=self.backend()
  with self.assertRaises(RuntimeError):run('test',b,Mock(),Mock(),Mock(),threading.Event(),clock=Mock(side_effect=[0,901]))
  b.execute.assert_not_called()
 def test_search_only_skips_approval_for_user_words(self):
  a={'kind':'open_url','reason':'search','url':'https://www.google.com/search?q=periodic+table'}
  self.assertTrue(approved_navigation(a,'Search periodic table'))
  self.assertFalse(approved_navigation(a,'Open my email'))
  a['url']='https://www.google.com/search?q=secretpassword'
  self.assertFalse(approved_navigation(a,'Search periodic table'))
 def test_changed_screen_replans_without_stale_action(self):
  b=self.backend();b.unchanged.return_value=False
  planner=Mock(side_effect=[{'kind':'click','reason':'click','x':.3,'y':.3},{'kind':'done','reason':'Need help'}])
  run('test',b,planner,lambda _:True,Mock(),threading.Event())
  self.assertEqual(planner.call_count,2);b.execute.assert_not_called()
 def test_only_fixed_navigation_skips_approval(self):
  self.assertFalse(needs_approval({'kind':'key','keys':['command','l']},'',{'app':'Google Chrome'}))
  for keys in [['command','s'],['command','backspace'],['enter']]:
   self.assertTrue(needs_approval({'kind':'key','keys':keys},''))
  self.assertTrue(needs_approval({'kind':'click','effect':'navigation'},''))
 def test_native_navigation_click_does_not_prompt(self):
  b=self.backend();b.navigation_target.return_value=True
  planner=Mock(side_effect=[{'kind':'click','reason':'Focus','x':.2,'y':.3},{'kind':'done','reason':'Done'}]);approval=Mock()
  run('Focus',b,planner,approval,Mock(),threading.Event())
  approval.assert_not_called();b.execute.assert_called_once()
 def test_native_target_rechecked_before_click(self):
  b=self.backend();b.navigation_target.side_effect=[True,False]
  planner=Mock(side_effect=[{'kind':'click','reason':'Focus','x':.2,'y':.3},{'kind':'done','reason':'Changed'}])
  run('Focus',b,planner,Mock(),Mock(),threading.Event())
  b.execute.assert_not_called()
if __name__=='__main__':unittest.main()
