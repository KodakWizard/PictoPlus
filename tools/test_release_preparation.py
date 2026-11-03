import io, unittest, zipfile
from pathlib import Path
from audit_public_release import inspect
class ReleaseChecks(unittest.TestCase):
 def test_private_content_rejected(self):
  for name,data in [('game.cia',b'x'),('app/data/save.json',b'{}'),('../escape.txt',b'x'),('note.txt',b'C:'+b'/Users/private/file')]:
   with self.subTest(name=name),self.assertRaises(AssertionError):inspect({name:data})
 def test_nested_content_rejected(self):
  stream=io.BytesIO()
  with zipfile.ZipFile(stream,'w') as z:z.writestr('private.pictosetup',b'x')
  with self.assertRaises(AssertionError):inspect({'setup.zip':stream.getvalue()})
 def test_branding_encoding(self):
  root=Path(__file__).resolve().parents[1]
  for name in ('index.html','authoring-setup.html'):
   text=(root/'app'/name).read_text(encoding='utf-8')
   self.assertIn('/assets/pictoplus.ico',text)
   self.assertNotIn('\u00c3',text)
   self.assertNotIn('\u00ef\u00bc',text)
  self.assertIn('PictoPlus \u00b7',(root/'app/index.html').read_text(encoding='utf-8'))
if __name__=='__main__':unittest.main()
