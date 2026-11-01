import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from chapter_context import build_context
from subtitle_tools import check_srt,import_segments
from prompt_regression import export_suite
from video_prompt_tools import lint
from creative_tools import new_ledger
class ContextSubtitleTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.novel=self.root/'novel.json';self.novel.write_bytes((S/'assets/example-novel.json').read_bytes())
 def tearDown(self):self.tmp.cleanup()
 def test_reader_does_not_receive_future_outline_or_character_arcs(self):
  d=json.loads(self.novel.read_text(encoding='utf-8'));d['chapters'][0]['story_time']='author-only hidden chronology';self.novel.write_text(json.dumps(d),encoding='utf-8')
  p=build_context(self.novel,1,'reader');self.assertIsNone(p['writer_bible']);self.assertIsNone(p['target_contract']);self.assertEqual([x['anchor'] for x in p['text_units']],['C001']);self.assertFalse(p['recorded_facts']);self.assertNotIn('author-only hidden chronology',json.dumps(p))
 def test_invalid_current_ledger_is_not_promoted_to_context(self):
  ledger=new_ledger(self.novel);ledger['facts']=[{'id':'F1','kind':'belief','statement':'an unfounded belief','holder_id':'unknown','at':['C001']}]
  path=self.root/'ledger.json';path.write_text(json.dumps(ledger),encoding='utf-8');p=build_context(self.novel,2,'continue',ledger_path=path)
  self.assertEqual(p['ledger_status'],'invalid_excluded');self.assertFalse(p['recorded_facts'])
 def test_continue_uses_prior_text_without_copying_target_body(self):
  p=build_context(self.novel,2,'continue');self.assertEqual([x['anchor'] for x in p['text_units']],['C001']);self.assertNotIn('body',p['target_contract']);self.assertTrue(p['writer_bible'])
 def test_future_chapter_must_be_next_and_in_declared_scope(self):
  with self.assertRaises(ValueError):build_context(self.novel,3,'continue')
  d=json.loads(self.novel.read_text(encoding='utf-8'));d['project']['planned_chapters']=3;self.novel.write_text(json.dumps(d))
  p=build_context(self.novel,3,'continue');self.assertEqual(p['target_contract']['status'],'not_authored')
  with self.assertRaises(ValueError):build_context(self.novel,5,'continue')
 def test_reader_target_is_not_silently_truncated(self):
  d=json.loads(self.novel.read_text(encoding='utf-8'));d['chapters'][1]['body']='长文本'*1000;self.novel.write_text(json.dumps(d))
  with self.assertRaises(ValueError):build_context(self.novel,2,'reader',max_chars=1000)
 def test_asr_import_preserves_supplied_times_and_warns_about_authority(self):
  source={'segments':[{'start':.25,'end':1.1,'text':'你好。'},{'start':1.3,'end':2.2,'text':'请进。'}]};original=copy.deepcopy(source);text,r=import_segments(source)
  self.assertEqual(source,original);self.assertIn('00:00:00,250 --> 00:00:01,100',text);self.assertFalse(r['word_timing_invented']);self.assertIn('recognition hypothesis',r['dialogue_authority'])
 def test_srt_detects_bad_intervals_overrun_and_overlap(self):
  text='1\n00:00:00,000 --> 00:00:01,000\n你好\n\n2\n00:00:00,900 --> 00:00:03,000\n再见\n';r=check_srt(text,duration=2)
  self.assertFalse(r['valid']);self.assertTrue(any('overlaps' in w for w in r['warnings']))
  with self.assertRaises(ValueError):import_segments({'segments':[{'start':float('nan'),'end':1,'text':'bad'}]})
 def test_promptfoo_export_runs_local_provider_contract(self):
  out=self.root/'suite';r=export_suite(out);self.assertEqual(r['cases'],5);self.assertFalse(r['promptfoo_executed'])
  spec=importlib.util.spec_from_file_location('provider_test',out/'offline_provider.py');provider=importlib.util.module_from_spec(spec);spec.loader.exec_module(provider)
  config=json.loads((out/'promptfooconfig.yaml').read_text(encoding='utf-8'))
  for test in config['tests']:
   result=provider.call_api(test['vars']['prompt'],{},{});self.assertEqual(result['output'],test['assert'][0]['value']);self.assertFalse(result['metadata']['model_called'])
 def test_explicit_no_orbit_is_not_a_camera_conflict(self):
  self.assertFalse(lint('Static camera, no orbit. She turns her head.','wan22-ti2v-5b','t2v')['warnings'])
if __name__=='__main__':unittest.main()
