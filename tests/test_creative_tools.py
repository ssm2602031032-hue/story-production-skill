"""Routing boundaries, licensed offline integration and evidence ledgers."""
import copy,hashlib,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'skills/story-production'
sys.path.insert(0,str(SKILL/'scripts'))
import creative_tools as creative

class CreativeToolsTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.source=self.root/'film.json';shutil.copy2(SKILL/'assets/example-film.json',self.source)
  self.ledger=creative.new_ledger(self.source)
 def tearDown(self):self.temp.cleanup()
 def selected(self,plan):return {m['id'] for m in plan['modules']}
 def test_dialogue_request_does_not_expand_into_full_production(self):
  p=creative.plan('只帮我润色第三场台词，不改剧情')
  self.assertEqual(p['task'],'dialogue');self.assertEqual(self.selected(p),{'dialogue'});self.assertFalse(p['media_generated'])
 def test_novel_full_does_not_require_film_production_modules(self):
  p=creative.plan('写一部成长小说的完整正文')
  self.assertEqual(p['mode'],'novel');self.assertIn('prose-voice',self.selected(p));self.assertNotIn('visual-design',self.selected(p))
 def test_naming_only_does_not_create_a_whole_story(self):
  p=creative.plan('只给这部悬疑小说起书名')
  self.assertEqual(p['task'],'naming');self.assertEqual(self.selected(p),{'title-logline'})
 def test_preserve_prose_is_a_constraint_not_an_automatic_review_task(self):
  p=creative.plan('只给示例短片起3个不同方向的片名并推荐一个，不改正文')
  self.assertEqual(p['task'],'naming');self.assertEqual(self.selected(p),{'title-logline'})
  p=creative.plan('为这部电影写项目提案，不改正文')
  self.assertEqual(p['task'],'pitch')
  self.assertEqual(creative.plan('只审读作品因果，不改正文')['task'],'critique')
 def test_comic_adaptation_is_not_claimed_as_a_rendered_film(self):
  p=creative.plan('把小说改编成条漫分格脚本')
  self.assertEqual(p['task'],'comics');self.assertIn('comics-webtoon',self.selected(p));self.assertIn('adaptation',self.selected(p));self.assertNotIn('format',self.selected(p))
 def test_audio_read_and_short_form_routes_are_distinct(self):
  for request,task,mid in [('改编成广播剧','audio','audio-drama'),('做对白读演，校准口气','table-read','table-read'),('制作一部竖屏短剧','short-form','short-vertical')]:
   p=creative.plan(request);self.assertEqual(p['task'],task);self.assertIn(mid,self.selected(p));self.assertFalse(p['media_generated'])
  self.assertEqual(creative.plan('制作一部竖屏短剧')['mode'],'series')
 def test_new_focus_passes_remain_bounded(self):
  for request,mid in [('只改结尾，保留人物经历','opening-ending'),('反派扁平，帮我设计反派','antagonist-design'),('梳理支线与群像关系','ensemble-subplots'),('补转场，不增加新人物','scene-transitions'),('压缩篇幅但不要丢失线索','pacing-compression')]:
   p=creative.plan(request);self.assertIn(mid,self.selected(p));self.assertNotEqual(p['task'],'full')
 def test_adaptation_uses_destination_mode(self):
  p=creative.plan('把小说改编成12集爱情悬疑剧集')
  self.assertEqual((p['mode'],p['task']),('series','adapt'))
  self.assertTrue({'adaptation','series-room','romance','mystery-thriller'}<=self.selected(p))
 def test_explicit_parameters_override_keyword_inference(self):
  p=creative.plan('小说喜剧电影',mode='novel',task='pitch')
  self.assertEqual(self.selected(p),{'pitch'});self.assertEqual(p['mode'],'novel')
 def test_common_negative_genre_does_not_add_comedy(self):
  p=creative.plan('写悬疑电影，不要喜剧元素')
  self.assertNotIn('comedy',p['genres']);self.assertNotIn('comedy',self.selected(p))
 def test_read_batches_are_small_and_phase_consistent(self):
  p=creative.plan('完整科幻爱情悬疑电视剧');by={m['id']:m for m in p['modules']}
  flattened=[]
  for batch in p['read_batches']:
   self.assertTrue(1<=len(batch)<=3);self.assertEqual(len({by[m]['stage'] for m in batch}),1);flattened+=batch
  self.assertEqual(set(flattened),self.selected(p));self.assertEqual(len(flattened),len(set(flattened)))
 def test_unknown_module_fails_instead_of_hallucinating_reference(self):
  with self.assertRaises(ValueError):creative.plan('主题',modules=['missing-module'])
 def test_catalog_has_resolvable_unique_modules(self):
  c=creative.catalog();ids=[m['id'] for m in c['modules']]
  self.assertEqual(c['module_count'],len(ids));self.assertEqual(len(ids),len(set(ids)))
  for m in c['modules']:
   p=(SKILL/m['reference']).resolve();self.assertTrue(p.is_relative_to(SKILL.resolve()));self.assertTrue(p.is_file());self.assertGreater(len(p.read_text(encoding='utf-8')),150)
 def test_vendored_snapshots_and_license_notices_match_pinned_hashes(self):
  sources=json.loads((SKILL/'assets/upstream-sources.json').read_text(encoding='utf-8'))
  self.assertEqual(len(sources['sources']),3)
  for source in sources['sources']:
   self.assertEqual(len(source['commit']),40);self.assertTrue(any('LICENSE' in f['path'] for f in source['files']))
   for f in source['files']:self.assertEqual(hashlib.sha256((SKILL/f['path']).read_bytes()).hexdigest(),f['sha256'])
 def test_empty_ledger_is_not_a_completed_review(self):
  r=creative.check_ledger(self.ledger,self.source)
  self.assertTrue(r['valid']);self.assertTrue(r['human_review_required']);self.assertTrue(any('Empty ledger' in w for w in r['warnings']))
 def test_fact_quote_and_belief_holder_are_checked(self):
  anchors,_,_=creative.source_index(self.source);quote=anchors['S01_001'].split('\n')[0]
  self.ledger['facts']=[{'id':'F1','kind':'canon','entity_id':'C01','statement':'当前发生的事','at':['S01_001'],'quote':quote},{'id':'F2','kind':'belief','holder_id':'C01','statement':'自己的理解','at':['S01']}]
  self.assertTrue(creative.check_ledger(self.ledger,self.source)['valid'])
  self.ledger['facts'][0]['quote']='原文没有写过的采访'
  self.ledger['facts'][1]['holder_id']='missing'
  r=creative.check_ledger(self.ledger,self.source);self.assertFalse(r['valid']);self.assertTrue(any('quote not found' in e for e in r['errors']))
 def test_resolved_promise_and_fixed_issue_need_actual_evidence(self):
  self.ledger['promises']=[{'id':'P1','setup':['S01'],'resolution':[],'status':'resolved'}]
  self.ledger['issues']=[{'id':'I1','kind':'bridge','at':['S01'],'observation':'衔接缺口','status':'fixed','fix_at':[],'verification':''}]
  self.assertFalse(creative.check_ledger(self.ledger,self.source)['valid'])
  self.ledger['promises'][0]['resolution']=['S03'];self.ledger['issues'][0].update(fix_at=['S02'],verification='已补当前来源镜，邻场仍成立')
  self.assertTrue(creative.check_ledger(self.ledger,self.source)['valid'])
 def test_belief_cannot_be_owned_by_a_prop(self):
  self.ledger['facts']=[{'id':'F1','kind':'belief','holder_id':'P01','statement':'错误把道具当知情者','at':['S01']}]
  self.assertFalse(creative.check_ledger(self.ledger,self.source)['valid'])
 def test_duplicate_ids_unknown_anchors_and_missing_open_reason_fail(self):
  self.ledger['facts']=[{'id':'X','kind':'canon','statement':'fact','at':['S99']}]
  self.ledger['promises']=[{'id':'X','setup':['S01'],'resolution':[],'status':'open-intentional'}]
  r=creative.check_ledger(self.ledger,self.source);self.assertFalse(r['valid']);self.assertTrue(any('Duplicate' in e for e in r['errors']))
 def test_source_change_requires_review(self):
  self.source.write_text(self.source.read_text(encoding='utf-8')+'\n',encoding='utf-8')
  self.assertFalse(creative.check_ledger(self.ledger,self.source)['valid'])
 def test_series_episode_edits_invalidate_ledger_even_if_manifest_unchanged(self):
  root=self.root/'show';shutil.copytree(SKILL/'assets/example-series',root);source=root/'series.json';ledger=creative.new_ledger(source)
  anchors,_,_=creative.source_index(source);self.assertIn('E001/S01_001',anchors)
  ep=root/'episodes/E002/film.json';ep.write_text(ep.read_text(encoding='utf-8')+'\n',encoding='utf-8')
  self.assertFalse(creative.check_ledger(ledger,source)['valid'])
 def test_novel_anchor_points_to_full_prose(self):
  source=SKILL/'assets/example-novel.json';anchors,entities,_=creative.source_index(source)
  self.assertIn('C002',anchors);self.assertGreater(len(anchors['C002']),200);self.assertIn('C01',entities)
 def test_plan_output_cannot_silently_overwrite(self):
  target=self.root/'plan.json';creative.safe_write(target,creative.plan('写一部电影'))
  with self.assertRaises(ValueError):creative.safe_write(target,creative.plan('另一主题'))

if __name__=='__main__':unittest.main()
