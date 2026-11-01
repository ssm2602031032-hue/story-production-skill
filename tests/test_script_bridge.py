import copy,csv,importlib.util,json,shutil,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];S=R/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from script_bridge import scaffold,validate,build,leaf_anchors,policies
from context_edit import audit,scaffold as align_init
from delivery_utils import digest
from creative_tools import source_index,plan as route
class BridgeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.source=self.root/'source.json';self.visual=self.root/'visual.json';self.bridge=self.root/'bridge.json'
  for target,name in [(self.source,'example-bridge-source.json'),(self.visual,'example-bridge-visual.json'),(self.bridge,'example-script-bridge.json')]:target.write_bytes((S/'assets'/name).read_bytes())
  self.data=json.loads(self.bridge.read_text(encoding='utf-8'));self.ids=[s['id'] for s in json.loads(self.visual.read_text(encoding='utf-8'))['shots']]
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.bridge.write_bytes((json.dumps(self.data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 def test_valid_mapping_preserves_explicit_adaptation_loss_and_estimated_speech(self):
  r=validate(self.source,self.visual,self.bridge);self.assertTrue(r['valid'],r);self.assertEqual(r['coverage']['beats'],4);self.assertEqual(r['coverage']['visual_jobs'],3);self.assertTrue(any('estimated' in w for w in r['warnings']))
 def test_scaffold_is_not_claimed_as_completed_conversion(self):
  out=self.root/'init.json';r=scaffold(self.source,self.visual,out);self.assertEqual(r['status'],'not_authored');self.assertFalse(validate(self.source,self.visual,out)['valid'])
 def test_invented_source_quote_cannot_pass(self):
  self.data['beats'][0]['quote']='原文不存在的新秘密';self.save();self.assertFalse(validate(self.source,self.visual,self.bridge)['valid'])
 def test_changed_source_or_visual_invalidates_mapping(self):
  self.source.write_bytes(self.source.read_bytes()+b'\n');self.visual.write_bytes(self.visual.read_bytes()+b'\n');r=validate(self.source,self.visual,self.bridge);self.assertTrue(any('Source fingerprint' in e for e in r['errors']));self.assertTrue(any('Visual contract changed' in e for e in r['errors']))
 def test_omitting_a_causal_prerequisite_requires_repair(self):
  self.data['beats'][0].update(treatment='omit',targets=[],adaptation_note='Requested deletion');self.data['reveal_order']=[];self.save();self.assertTrue(any('omitted prerequisite' in e for e in validate(self.source,self.visual,self.bridge)['errors']))
  self.data['beats'][1]['dependency_repair']='A newly authored visible request now establishes the same causal need';self.save();r=validate(self.source,self.visual,self.bridge);self.assertTrue(r['valid']);self.assertTrue(any('manually verify replacement' in x for x in r['human_review']))
 def test_every_source_unit_and_visual_job_must_be_accounted_for(self):
  self.data['beats']=[];self.data['reveal_order']=[];self.data['shot_links'].pop();self.save();r=validate(self.source,self.visual,self.bridge);self.assertFalse(r['valid']);self.assertTrue(any('without mapping' in e for e in r['errors']));self.assertTrue(any('shot_links' in e for e in r['errors']))
 def test_dependency_cycles_are_rejected(self):
  self.data['beats'][0]['depends_on']=['B03'];self.save();self.assertTrue(any('cycle' in e for e in validate(self.source,self.visual,self.bridge)['errors']))
 def test_revelation_order_is_not_inferred_from_causal_order(self):
  self.data['reveal_order']=[{'before':'B03','after':'B01','reason':'Bad example'}];self.save();self.assertFalse(validate(self.source,self.visual,self.bridge)['valid'])
 def test_changed_dialogue_requires_reason_and_visible_speaker_binding(self):
  self.data['dialogue'][0]['spoken_text']='让我自己来。';self.data['dialogue'][0]['speaker_asset']='unknown';self.save();r=validate(self.source,self.visual,self.bridge);self.assertTrue(any('changed dialogue' in e for e in r['errors']));self.assertTrue(any('visible speaker' in e for e in r['errors']))
 def test_estimated_dialogue_cannot_overrun_the_shot(self):
  self.data['dialogue'][0]['duration_sec']=10;self.save();self.assertTrue(any('exceeds shot' in e for e in validate(self.source,self.visual,self.bridge)['errors']))
 def test_boundary_card_cannot_skip_between_non_adjacent_jobs(self):
  self.data['boundaries'][0]['to']=self.ids[2];self.save();self.assertFalse(validate(self.source,self.visual,self.bridge)['valid'])
 def test_context_changes_editorial_guidance_without_rewriting_visible_content(self):
  original=(self.source.read_bytes(),self.visual.read_bytes());out=self.root/'dialogue';build(self.source,self.visual,self.bridge,out);p=json.loads((out/'shot-packages.json').read_text(encoding='utf-8'))
  self.data['scenes'][0]['context']='comedy';self.save();new=self.root/'comedy';build(self.source,self.visual,self.bridge,new);q=json.loads((new/'shot-packages.json').read_text(encoding='utf-8'));self.assertEqual([s['visible_prompt'] for s in p['shots']],[s['visible_prompt'] for s in q['shots']]);self.assertNotEqual(p['shots'][0]['editorial_policy'],q['shots'][0]['editorial_policy']);self.assertEqual(original,(self.source.read_bytes(),self.visual.read_bytes()))
 def test_build_separates_speech_from_visual_text_and_exports_safe_csv(self):
  self.data['shot_links'][0]['cut_trigger']='=formula-looking authored text';self.save();out=self.root/'package';build(self.source,self.visual,self.bridge,out);p=json.loads((out/'shot-packages.json').read_text(encoding='utf-8'));self.assertEqual(p['shots'][0]['speech_track'][0]['spoken_text'],'我来拿吧。');self.assertNotIn('我来拿吧。',p['shots'][0]['visible_prompt']);self.assertIn('可见发声者：乙',p['shots'][0]['visible_prompt']);self.assertFalse(p['media_generated'])
  with (out/'source-shot-map.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f));self.assertTrue(rows[1][-1].startswith("'="))
 def test_series_dependency_fingerprint_changes_when_episode_changes(self):
  directory=self.root/'series';shutil.copytree(S/'assets/example-series',directory);source=directory/'series.json';anchors,first=leaf_anchors(source);self.assertTrue(all('/S' in key for key in anchors));ep=directory/'episodes/E002/film.json';ep.write_bytes(ep.read_bytes()+b'\n');self.assertNotEqual(first,leaf_anchors(source)[1])
 def edit_fixture(self):
  edit={'version':'1.5.0','title':'declared planning test','fps':24,'width':64,'height':48,'color_intent':'sdr-review','embedded_audio_policy':'ignore','sources':{f'V{i}':{'kind':'video','path':f'take{i}.mp4','sha256':'0'*64} for i in range(3)},'picture':[{'id':f'CUT{i}','source':f'V{i}','in_frame':0,'out_frame':72,'story_ref':jid} for i,jid in enumerate(self.ids)],'audio':[]}
  path=self.root/'edit.json';path.write_text(json.dumps(edit),encoding='utf-8');a={'version':'1.7.0','edit_sha256':digest(path),'bridge_sha256':digest(self.bridge),'visual_sha256':digest(self.visual),'clips':[{'id':f'CUT{i}','job':jid,'source_zero_frame':0,'evidence':'Synthetic declared alignment for structural test, not viewed media'} for i,jid in enumerate(self.ids)],'boundary_decisions':[]};alignment=self.root/'alignment.json';alignment.write_text(json.dumps(a),encoding='utf-8');return path,alignment,edit,a
 def test_context_edit_preserves_full_moments_without_claiming_media_review(self):
  path,alignment,_,_=self.edit_fixture();r=audit(self.source,self.visual,self.bridge,path,alignment);self.assertTrue(r['valid'],r);self.assertFalse(r['media_checked']);self.assertFalse(r['actual_performance_timing_verified'])
 def test_cutting_away_a_protected_reaction_is_detected(self):
  path,alignment,e,a=self.edit_fixture();e['picture'][2]['out_frame']=24;path.write_text(json.dumps(e));a['edit_sha256']=digest(path);alignment.write_text(json.dumps(a));r=audit(self.source,self.visual,self.bridge,path,alignment);self.assertTrue(any('protected story interval' in x for x in r['errors']))
 def test_reordering_edit_requires_new_handoff_and_preserves_reveal_constraints(self):
  path,alignment,e,a=self.edit_fixture();e['picture'].reverse();path.write_text(json.dumps(e));a['edit_sha256']=digest(path);alignment.write_text(json.dumps(a));r=audit(self.source,self.visual,self.bridge,path,alignment);self.assertTrue(any('reveal order' in x for x in r['errors']));self.assertTrue(any('changed adjacency' in x for x in r['errors']))
 def test_alignment_init_does_not_pretend_media_was_examined(self):
  path,_,_,_=self.edit_fixture();out=self.root/'alignment-init.json';r=align_init(self.bridge,self.visual,path,out);self.assertIn('unverified',r['status']);self.assertTrue(all(not c['evidence'] for c in json.loads(out.read_text())['clips']))
 def test_situation_policies_do_not_impose_uniform_cut_durations(self):
  p=policies();self.assertEqual(len(p),10);self.assertNotEqual(p['action']['hold_for'],p['comedy']['hold_for']);self.assertTrue(all('duration_sec' not in value for value in p.values()))
 def test_bridge_routes_are_local_and_full_creation_stays_full(self):
  for request,task in [('做场景因果设计','scene-intent'),('剧本转分镜','script-bridge'),('处理内心戏外化','subtext-screen'),('对白时间分配','speech-budget'),('分层提示词','prompt-layers'),('按场景剪辑','scene-edit'),('做镜头交接','handoff'),('保护关键动作','story-guards')]:self.assertEqual(route(request)['task'],task)
  p=route('写一部完整电影，然后根据当前情境安排剪辑');self.assertEqual(p['task'],'full');self.assertIn('scene-context-editing',{m['id'] for m in p['modules']});self.assertEqual(route('只润色第三场台词')['task'],'dialogue')
 @unittest.skipUnless(importlib.util.find_spec('PIL'),'optional real reference image check')
 def test_bound_keyframes_are_copied_to_the_output_with_valid_relative_links(self):
  from PIL import Image
  image=self.root/'scene.png';Image.new('RGB',(48,32),'gray').save(image);v=json.loads(self.visual.read_text(encoding='utf-8'));v['assets'][0]['references']=[{'id':'R1','role':'first_frame','view':'wide','path':'scene.png','sha256':digest(image),'approved':True,'approval_note':'Synthetic test only','covers_assets':['C01','C02','P01','L01'],'inherit':'test image','exclude':'no real scene claim'}];v['shots'][0]['conditioning']={'first':'R1'};self.visual.write_text(json.dumps(v),encoding='utf-8');self.data['visual_sha256']=digest(self.visual);self.save();out=self.root/'package';build(self.source,self.visual,self.bridge,out);mapping=json.loads((out/'reference-map.json').read_text());p=out/mapping[self.ids[0]]['first'];self.assertEqual(digest(p),digest(image));self.assertTrue(any(f['path']==mapping[self.ids[0]]['first'] for f in json.loads((out/'manifest.json').read_text())['files']))
if __name__=='__main__':unittest.main()
