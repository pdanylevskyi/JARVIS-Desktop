import unittest
from desktop.news_reader import ArticleParser,validate_url,BBCRedirect
class ReaderTests(unittest.TestCase):
 def test_source_restriction(self):
  self.assertEqual(validate_url('https://www.bbc.com/ukrainian/a'),'https://www.bbc.com/ukrainian/a')
  for url in ('http://www.bbc.com/a','https://www.bbc.com.evil/a','https://user:pass@www.bbc.com/a','https://127.0.0.1/a','https://www.bbc.com:8080/a'):
   with self.assertRaises(ValueError):validate_url(url)
 def test_redirect_cannot_escape_source(self):
  with self.assertRaises(ValueError):BBCRedirect().redirect_request(None,None,302,'',{},'http://127.0.0.1/')
 def test_extracts_body_excludes_navigation_scripts(self):
  p=ArticleParser();p.feed('<nav><p>menu</p></nav><main><h1>Title</h1><p>Hello <b>world</b> &amp; friends.</p><script>bad()</script><aside><p>ad</p></aside><h2>Section</h2><p>Body</p></main><footer><p>footer</p></footer>')
  self.assertEqual(p.title,'Title');self.assertEqual([b['text'] for b in p.blocks],['Hello world & friends.','Section','Body'])
if __name__=='__main__':unittest.main()
