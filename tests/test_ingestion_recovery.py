import unittest,importlib.util,os,io,json,threading
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stderr,redirect_stdout
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
 s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
push=module('news_push','push-news-to-worker.py');pipeline=module('news_pipeline','news-pipeline.py')
class StrictNewsTests(unittest.TestCase):
 def run_cli(self,args,env):
  with patch.dict(os.environ,env,clear=True),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):return push.main(args)
 def test_missing_settings_fail_unless_explicitly_optional(self):
  self.assertEqual(self.run_cli([],{}),2);self.assertEqual(self.run_cli(['--optional'],{}),0);self.assertEqual(self.run_cli(['--check'],{}),0)
 def test_url_rejects_embedded_credentials_and_insecure_external_hosts(self):
  for url in ['http://example.com','https://user:password@example.com','https://example.com?token=x']:
   with self.subTest(url=url),self.assertRaises(ValueError):push.validate_url(url)
 def test_redirect_is_not_followed_and_upload_failure_is_not_success(self):
  calls=[]
  class Handler(BaseHTTPRequestHandler):
   def do_POST(self):
    self.rfile.read(int(self.headers.get('Content-Length','0')));calls.append(self.path);self.send_response(302);self.send_header('Location','/capture');self.end_headers()
   def do_GET(self):calls.append(self.path);self.send_response(200);self.end_headers()
   def log_message(self,*a):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:self.assertEqual(self.run_cli([],{'WORKER_URL':f'http://127.0.0.1:{server.server_port}','NEWS_INGEST_TOKEN':'test-only'}),1);self.assertEqual(calls,['/v1/ingest/news'])
  finally:server.shutdown();server.server_close();thread.join()
 def test_generator_failure_cannot_be_mistaken_for_a_successful_run(self):
  valid={'tiers':{'priority':{'last_success':'2026-11-09T00:00:00Z'}},'fetched':5,'candidates':2,'gemini_ok':True,'stories_online':4}
  import datetime
  start=datetime.datetime.fromisoformat('2026-11-09T00:00:00+00:00').timestamp();pipeline.verify_generation(valid,start)
  for change in [{'fetched':0},{'gemini_ok':False},{'stories_online':0},{'tiers':{'priority':{'last_success':'2026-11-08T00:00:00Z'}}}]:
   with self.subTest(change=change),self.assertRaises(ValueError):pipeline.verify_generation({**valid,**change},start)
 def test_run_without_keys_never_starts_generator_or_network(self):
  with patch.dict(os.environ,{},clear=True),patch.object(pipeline.subprocess,'run') as child,redirect_stderr(io.StringIO()):
   self.assertEqual(pipeline.main(['--run']),1);child.assert_not_called()
if __name__=='__main__':unittest.main()
