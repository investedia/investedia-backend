import contextlib,importlib.util,io,json,os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
push=load('connections_push','push-connections-to-worker.py');pipeline=load('connections_pipeline','news-pipeline.py')
class LiveConnectionsTests(unittest.TestCase):
 def test_check_never_uploads(self):
  with patch.object(push.urllib.request,'build_opener') as network,contextlib.redirect_stdout(io.StringIO()):self.assertEqual(push.main(['--check']),0);network.assert_not_called()
 def test_upload_uses_connections_route_and_requires_acknowledgement(self):
  response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False);response.read.return_value=b'{"ok":true,"count":1}'
  opener=Mock();opener.open.return_value=response
  with patch.object(push.urllib.request,'build_opener',return_value=opener):
   self.assertTrue(push.push('https://worker.example','test-only',push.payload())['ok']);request=opener.open.call_args.args[0];self.assertEqual(request.full_url,'https://worker.example/v1/ingest/connections')
   response.read.return_value=b'{"ok":false}'
   with self.assertRaises(ValueError):push.push('https://worker.example','test-only',push.payload())
 def test_upload_refuses_unsafe_urls_and_oversize_without_network(self):
  with patch.object(push.urllib.request,'build_opener') as network:
   for url in ['http://outside.example','https://user:pass@outside.example','https://outside.example?token=bad']:
    with self.assertRaises(ValueError):push.push(url,'test-only',push.payload())
   with patch.object(push,'MAX_BYTES',10),self.assertRaises(ValueError):push.push('https://worker.example','test-only',push.payload())
   network.assert_not_called()
 def test_pipeline_publishes_connections_after_generator_and_news(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'.local').mkdir();(root/'assets/globe').mkdir(parents=True);(root/'assets/globe/news-status.json').write_text('{}')
   calls=[]
   def run(args,**kwargs):calls.append(Path(next(str(a) for a in args if str(a).endswith('.py'))).name)
   with patch.object(pipeline,'ROOT',root),patch.object(pipeline,'preflight',return_value={}),patch.object(pipeline,'verify_generation'),patch.object(pipeline,'exclusive_run',return_value=contextlib.nullcontext()),patch.object(pipeline.subprocess,'run',side_effect=run),contextlib.redirect_stdout(io.StringIO()):
    self.assertEqual(pipeline.main(['--run']),0)
   self.assertEqual(calls,['update_globe_news.py','connections.py','push-news-to-worker.py','push-connections-to-worker.py'])
 def test_pipeline_connections_upload_failure_is_visible(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'.local').mkdir();(root/'assets/globe').mkdir(parents=True);(root/'assets/globe/news-status.json').write_text('{}')
   def run(args,**kwargs):
    if any(str(a).endswith('push-connections-to-worker.py') for a in args):raise subprocess.CalledProcessError(1,args)
   with patch.object(pipeline,'ROOT',root),patch.object(pipeline,'preflight',return_value={}),patch.object(pipeline,'verify_generation'),patch.object(pipeline,'exclusive_run',return_value=contextlib.nullcontext()),patch.object(pipeline.subprocess,'run',side_effect=run),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(pipeline.main(['--run']),1)
if __name__=='__main__':unittest.main()
