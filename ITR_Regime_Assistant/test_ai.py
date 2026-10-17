import unittest,json,io
from ai_review import request_draft
class AITests(unittest.TestCase):
 def test_completed(self):
  def opener(req,timeout):
   body=json.loads(req.data);self.assertFalse(body['store']);self.assertEqual(body['input'],'previewed facts');self.assertEqual(timeout,55)
   return io.BytesIO(json.dumps({'status':'completed','model':'test','output':[{'type':'message','content':[{'type':'output_text','text':'Draft'}]}]}).encode())
  self.assertEqual(request_draft('previewed facts','dummy-key','test',opener)['text'],'Draft')
 def test_incomplete(self):
  with self.assertRaises(ValueError):request_draft('p','k','m',lambda *a,**kw:io.BytesIO(b'{"status":"incomplete"}'))
 def test_no_credentials(self):
  with self.assertRaises(ValueError):request_draft('p','','m')
if __name__=='__main__':unittest.main()
