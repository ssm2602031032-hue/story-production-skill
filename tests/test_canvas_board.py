import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];S=R/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from canvas_board import layout,export_bundle,from_bridge,check_spec,overlap,project,GRID
from delivery_utils import digest
from creative_tools import plan
class CanvasTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'spec.json';self.d={'title':'Example board','groups':[{'id':'SC01','title':'Scene one'},{'id':'SC02','title':'Scene two'}],'stages':[{'id':'ref','title':'References'},{'id':'prompt','title':'Prompts'},{'id':'review','title':'Review'}],'nodes':[],'edges':[]}
  for group in ('SC01','SC02'):
   for i,stage in enumerate(('ref','prompt','review')):self.d['nodes'].append({'id':group+'_'+stage,'group':group,'stage':stage,'order':0,'title':group+' '+stage,'summary':'A brief visible card summary.','details':'Full text stays in an editable note.','status':'planned' if stage=='ref' else 'draft'})
   for a,b in (('ref','prompt'),('prompt','review')):self.d['edges'].append({'id':group+a+b,'from':group+'_'+a,'to':group+'_'+b,'label':'supports'})
  self.save()
 def save(self):self.source.write_bytes((json.dumps(self.d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 def tearDown(self):self.tmp.cleanup()
 def test_ordered_groups_stages_and_no_card_overlap(self):
  r=layout(self.source);by={x['id']:x for x in r['cards']};self.assertLess(by['SC01_ref']['x'],by['SC01_prompt']['x']);self.assertLess(by['SC01_review']['y'],by['SC02_ref']['y'])
  for i,a in enumerate(r['cards']):
   self.assertEqual(a['x']%GRID,0);self.assertEqual(a['y']%GRID,0)
   for b in r['cards'][i+1:]:self.assertFalse(overlap(a,b))
  for g in r['groups']:
   for c in (c for c in r['cards'] if c['group']==g['id']):self.assertTrue(g['x']<=c['x'] and g['y']<c['y'] and g['x']+g['width']>=c['x']+c['width'] and g['y']+g['height']>=c['y']+c['height'])
 def test_routes_do_not_cross_card_interiors(self):
  self.d['edges'].append({'id':'cross','from':'SC01_ref','to':'SC02_review','label':'shared dependency'});self.save();r=layout(self.source)
  for edge in r['edges']:
   self.assertTrue(edge['routed'])
   for a,b in zip(edge['points'],edge['points'][1:]):
    self.assertTrue(a[0]==b[0] or a[1]==b[1]);steps=int(max(abs(a[0]-b[0]),abs(a[1]-b[1]))//GRID)
    for k in range(1,steps):
     x=a[0]+(b[0]-a[0])*k/steps;y=a[1]+(b[1]-a[1])*k/steps
     self.assertFalse(any(c['x']<x<c['x']+c['width'] and c['y']<y<c['y']+c['height'] for c in r['cards']))
 def test_incremental_addition_preserves_existing_coordinates(self):
  self.d['groups']=self.d['groups'][:1];self.d['nodes']=[n for n in self.d['nodes'] if n['group']=='SC01'];self.d['edges']=[e for e in self.d['edges'] if e['id'].startswith('SC01')];self.save();first=layout(self.source);p=self.root/'previous.json';p.write_text(json.dumps(first));n=copy.deepcopy(self.d['nodes'][0]);n.update(id='A_new',order=0);self.d['nodes'].insert(0,n);self.save();second=layout(self.source,p);by={n['id']:n for n in second['cards']}
  for old in first['cards']:self.assertEqual((old['x'],old['y']),(by[old['id']]['x'],by[old['id']]['y']))
 def test_conflicting_manual_pins_fail_without_moving_them(self):
  self.d['nodes'][0]['pinned']={'x':60,'y':260};self.d['nodes'][1]['pinned']={'x':60,'y':260};self.save();before=self.source.read_bytes()
  with self.assertRaises(ValueError):layout(self.source)
  self.assertEqual(before,self.source.read_bytes())
 def test_unknown_relations_and_overlong_card_text_fail(self):
  self.d['edges'][0]['to']='missing';self.save()
  with self.assertRaises(ValueError):layout(self.source)
  self.d['edges'][0]['to']='SC01_prompt';self.d['nodes'][0]['summary']='Long text '*100;self.save()
  with self.assertRaises(ValueError):layout(self.source)
 def test_json_canvas_has_valid_refs_groups_and_editable_full_notes(self):
  out=self.root/'board';before=self.source.read_bytes();r=export_bundle(self.source,out);d=json.loads((out/'board.canvas').read_text(encoding='utf-8'));ids=[n['id'] for n in d['nodes']];self.assertEqual(len(ids),len(set(ids)));self.assertEqual(d['nodes'][0]['type'],'group');self.assertTrue(all(e['fromNode'] in ids and e['toNode'] in ids for e in d['edges']));self.assertEqual(len(list((out/'notes').glob('*.md'))),6);self.assertEqual(before,self.source.read_bytes());self.assertFalse(r['native_app_tested']);self.assertFalse(json.loads((out/'manifest.json').read_text(encoding='utf-8'))['media_generated'])
  with self.assertRaises(ValueError):export_bundle(self.source,out)
 def test_media_file_fingerprint_and_portable_copy(self):
  p=self.root/'frame.bin';p.write_bytes(b'actual local fixture');self.d['nodes'][0].update(file='frame.bin',sha256=digest(p));self.save();out=self.root/'board';export_bundle(self.source,out);check_spec(out/'source-spec.json');d=json.loads((out/'board.canvas').read_text(encoding='utf-8'));file_node=next(n for n in d['nodes'] if n['type']=='file');self.assertEqual((out/file_node['file']).read_bytes(),p.read_bytes());p.write_bytes(b'changed')
  with self.assertRaises(ValueError):layout(self.source)
 def test_approved_status_requires_review_evidence(self):
  self.d['nodes'][0]['status']='approved';self.save()
  with self.assertRaises(ValueError):layout(self.source)
 def test_bridge_import_keeps_full_prompt_and_no_invented_generated_media(self):
  from script_bridge import build
  pack=self.root/'bridge';build(S/'assets/example-bridge-source.json',S/'assets/example-bridge-visual.json',S/'assets/example-script-bridge.json',pack);spec=self.root/'imported.json';r=from_bridge(pack/'shot-packages.json',spec);self.assertEqual(r['cards'],18);data=json.loads(spec.read_text(encoding='utf-8'));self.assertTrue(all(n['status']=='planned' for n in data['nodes'] if n['stage']=='media'));self.assertTrue(all(len(n['details'])>len(n['summary']) for n in data['nodes'] if n['stage']=='prompt'));self.assertEqual(len(layout(spec)['cards']),18)
 def test_large_project_has_navigable_pages_without_losing_jobs(self):
  from script_bridge import build
  pack=self.root/'bridge';build(S/'assets/example-bridge-source.json',S/'assets/example-bridge-visual.json',S/'assets/example-script-bridge.json',pack);d=json.loads((pack/'shot-packages.json').read_text(encoding='utf-8'));seed=d['shots'][0];d['shots']=[]
  for i in range(17):
   row=copy.deepcopy(seed);row['id']=f'SHOT{i:03}';d['shots'].append(row)
  p=self.root/'long.json';p.write_text(json.dumps(d),encoding='utf-8');out=self.root/'project';r=project(p,out);self.assertEqual(r['pages'],3);pages=json.loads((out/'pages.json').read_text(encoding='utf-8'))['pages'];self.assertEqual([j for page in pages for j in page['jobs']],[s['id'] for s in d['shots']]);self.assertTrue(all((out/page['canvas']).is_file() and (out/page['index']).is_file() for page in pages))
 def test_canvas_request_routes_to_planning_without_inventing_movie_or_native_workflow(self):
  p=plan('把素材整理到无线画布上');self.assertEqual(p['task'],'canvas-board');ids={m['id'] for m in p['modules']};self.assertTrue({'canvas-information-design','canvas-auto-layout','canvas-incremental-handoff'}<=ids);self.assertNotIn('premise',ids);self.assertFalse(p['media_generated'])
  self.assertEqual(plan('只润色第三场台词')['task'],'dialogue');self.assertEqual(plan('学习图片质感和参考图片写法')['task'],'image-grounding');self.assertEqual(plan('静帧转视频提示词')['task'],'still-motion')
if __name__=='__main__':unittest.main()
