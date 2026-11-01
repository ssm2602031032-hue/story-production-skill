import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'skills/story-production';sys.path.insert(0,str(SKILL/'scripts'))
import film_pipeline,video_prompt_tools as video,project_ops
class VideoTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.source=self.root/'film.json';self.data=json.loads((SKILL/'assets/example-film.json').read_text(encoding='utf-8'));self.save();self.plan=film_pipeline.compile_film(self.data)
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.source.write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
 def test_native_fps_and_frame_grid_are_not_edit_fps(self):
  jobs=video.compile_jobs(self.plan,'wan22-t2v-a14b','t2v')
  self.assertEqual(jobs['edit_fps'],24)
  for j in jobs['video_jobs']:
   self.assertEqual(j['native_fps'],16);self.assertLessEqual(j['native_frames'],81);self.assertEqual((j['native_frames']-1)%4,0);self.assertLessEqual(j['native_frames_covering_take'],j['native_frames'])
  self.assertEqual(jobs['summary']['covered_edit_frames'],self.plan['meta']['story_frames'])
 def test_post_tasks_do_not_get_generation_jobs(self):
  p=video.compile_jobs(self.plan,'wan22-ti2v-5b','t2v');post={s['id'] for s in self.plan['shots'] if s['pure_post']}
  self.assertEqual(post,{s['shot'] for s in p['post_tasks']});self.assertFalse(post&{j['shot'] for j in p['video_jobs']})
 def test_prompt_keeps_past_wardrobe_and_does_not_add_voice_actor(self):
  p=video.compile_jobs(self.plan,'wan22-ti2v-5b','t2v')
  past=next(j for j in p['video_jobs'] if j['shot']=='S02_001')
  self.assertIn('深绿工作围裙',past['positive_prompt']);self.assertNotIn('米色针织外套',past['positive_prompt'])
  heard=next(j for j in p['video_jobs'] if j['shot']=='S01_002')
  self.assertNotIn('C02',heard['visible_asset_ids'])
 def test_unsupported_mode_is_rejected(self):
  with self.assertRaises(ValueError):video.compile_jobs(self.plan,'wan22-ti2v-5b','flf2v')
 def test_missing_i2v_references_remain_pending(self):
  p=video.compile_jobs(self.plan,'wan22-i2v-a14b','i2v')
  self.assertEqual(p['summary']['jobs_missing_references'],len(p['video_jobs']));self.assertTrue(all(not j['generated_media'] for j in p['video_jobs']))
 def test_long_shot_does_not_apply_whole_tail_to_first_segment(self):
  (self.root/'first.png').write_bytes(b'\x89PNG\r\n\x1a\n'+b'fixture')
  (self.root/'last.png').write_bytes(b'\x89PNG\r\n\x1a\n'+b'fixture2')
  ref={'S01_001':{'first':'first.png','last':'last.png'}}
  p=video.compile_jobs(self.plan,'ltx25-comfy-flf','flf2v',ref,self.root)
  seq=[j for j in p['video_jobs'] if j['shot']=='S01_001'];self.assertGreater(len(seq),1)
  self.assertIn('first',seq[0]['reference_assets']);self.assertNotIn('last',seq[0]['reference_assets']);self.assertIn('last',seq[-1]['reference_assets']);self.assertNotIn('first',seq[-1]['reference_assets'])
 def test_endpoint_policy_does_not_crop_away_keyframe(self):
  p=video.compile_jobs(self.plan,'ltx25-comfy-flf','flf2v')
  for j in p['video_jobs']:
   c=j['endpoint_conform'];self.assertEqual(c['source_last_index'],j['native_frames']-1);self.assertEqual(c['target_last_index'],j['edit_out_frame_exclusive']-j['edit_in_frame']-1);self.assertTrue(c['manual_review_required']);self.assertEqual((j['native_frames']-1)%8,0)
 def test_reference_escape_and_unknown_jobs_are_rejected(self):
  with self.assertRaises(ValueError):video.compile_jobs(self.plan,'wan22-ti2v-5b','i2v',{'S01_001':{'first':'../outside.png'}},self.root)
  with self.assertRaises(ValueError):video.compile_jobs(self.plan,'wan22-ti2v-5b','t2v',directives={'UNKNOWN':{'action':'x'}})
 def test_duplicate_shot_ids_and_noncontinuous_timeline_fail(self):
  p=copy.deepcopy(self.plan);p['shots'][1]['id']=p['shots'][0]['id']
  with self.assertRaises(ValueError):video.compile_jobs(p,'wan22-ti2v-5b','t2v')
  p=copy.deepcopy(self.plan);p['shots'][1]['first_frame']+=1
  with self.assertRaises(ValueError):video.compile_jobs(p,'wan22-ti2v-5b','t2v')
 def test_lint_flags_camera_contradiction_without_quality_score(self):
  result=video.lint('Static camera with a fast 360 orbit, 8K masterpiece award-winning hyperrealistic.','wan22-ti2v-5b','t2v')
  self.assertTrue(result['valid']);self.assertGreaterEqual(len(result['warnings']),2);self.assertNotIn('quality_score',result)
 def test_realism_brief_is_specific_and_unrendered(self):
  p=video.realism_brief('阴天窗边的成年店员','把信封推向桌子另一端')
  self.assertIn('三脚架固定',p['positive_zh']);self.assertIn('信封',p['positive_zh']);self.assertEqual(p['status'],'unrendered-photographic-baseline')
 def test_unrun_benchmark_has_no_winner_or_scores(self):
  b=video.benchmark_suite('wan22-ti2v-5b',['hesitation']);r=video.benchmark_check(b,self.root)
  self.assertTrue(r['valid']);self.assertIsNone(r['mean_candidate_minus_baseline']);self.assertEqual(r['status'],'not-evaluated');self.assertFalse(b['market_ranking_claim'])
 def test_benchmark_cases_respect_profile_capabilities(self):
  b=video.benchmark_suite('ltx25-comfy-flf');self.assertTrue(all(r['mode']=='flf2v' for r in b['runs']))
  with self.assertRaises(ValueError):video.benchmark_suite('wan22-i2v-a14b',['hesitation'])
 def test_benchmark_needs_artifacts_and_matched_conditions(self):
  b=video.benchmark_suite('wan22-ti2v-5b',['hesitation']);metrics=b['metrics'];path=self.root/'sample.mp4';path.write_bytes(b'test-evidence-not-real-media');h=video.digest(path)
  for r in b['runs'][:2]:r.update(status='complete',artifact='sample.mp4',sha256=h,workflow_fingerprint='abc',settings={'model_revision':'test','width':1280,'height':704,'frames':121,'fps':24,'steps':50,'sampler':'test','guidance':5,'reference_hashes':[]},prompt='one main action',observations='test-only observation',scores={k:3 for k in metrics})
  report=video.benchmark_check(b,self.root);self.assertTrue(report['valid']);self.assertEqual(report['matched_pairs'],1)
  b['runs'][1]['settings']['fps']=30;self.assertFalse(video.benchmark_check(b,self.root)['valid'])
  b['runs'][0]['artifact']='missing.mp4';self.assertFalse(video.benchmark_check(b,self.root)['valid'])
 def test_build_does_not_change_input_and_refuses_implicit_overwrite(self):
  src=self.root/'shot-plan.json';src.write_text(json.dumps(self.plan,ensure_ascii=False),encoding='utf-8');before=src.read_bytes();out=self.root/'prompts'
  video.build(src,out,'wan22-ti2v-5b','i2v');self.assertEqual(before,src.read_bytes());self.assertTrue((out/'prompts.md').is_file())
  with self.assertRaises(ValueError):video.build(src,out,'wan22-ti2v-5b','i2v')
 def test_snapshots_report_dialogue_camera_and_asset_impacts(self):
  old=project_ops.snapshot(self.source);self.data['scenes'][0]['shots'][0][3]='短距离推进';self.save();now=project_ops.snapshot(self.source);r=project_ops.impacts(old,now)
  self.assertIn('S01_001',r['changed_units']);self.assertNotIn('S01_001',r['text_changed']);self.assertFalse(r['timing_changed'])
  old=now;self.data['characters'][0]['appearance']+='；头发稍长';self.save();r=project_ops.impacts(old,project_ops.snapshot(self.source))
  self.assertIn('C01',r['assets_changed']);self.assertTrue(r['units_requiring_review']);self.assertTrue(r['needs_rebuild'])
 def test_impact_locates_ledger_dependents_without_editing_ledger(self):
  old=project_ops.snapshot(self.source);self.data['scenes'][0]['shots'][0][0]+=1;self.save();ledger={'promises':[{'id':'P1','setup':['S01'],'resolution':['S03']}]};before=copy.deepcopy(ledger)
  r=project_ops.impacts(old,project_ops.snapshot(self.source),ledger);self.assertEqual(ledger,before);self.assertIn('S01_001',r['timing_changed']);self.assertEqual(r['ledger_items_requiring_review'][0]['id'],'P1')
  self.assertIn('S03_004',r['downstream_timing_units'])
 def test_sources_workflows_and_cards_are_real_offline_resources(self):
  profiles=video.profiles();self.assertEqual(len({p['id'] for p in profiles}),len(profiles));self.assertTrue(all(p['evidence'] and len(p['source_commit'])==40 for p in profiles))
  registry=json.loads((SKILL/'assets/workflow-snapshots.json').read_text(encoding='utf-8'))
  for item in registry['files']:
   path=SKILL/item['file'];self.assertEqual(video.digest(path),item['sha256']);self.assertIsInstance(json.loads(path.read_text(encoding='utf-8')),dict)
  cards=json.loads((SKILL/'assets/video-prompt-cards.json').read_text(encoding='utf-8'))['cards'];self.assertEqual(len(cards),len({c['positive_en'] for c in cards}));self.assertTrue(all(c['review_checks'] and c['first_state']!=c['last_state'] for c in cards))
if __name__=='__main__':unittest.main()
