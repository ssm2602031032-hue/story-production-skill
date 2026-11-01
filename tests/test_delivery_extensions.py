import copy,hashlib,importlib.util,json,math,sys,tempfile,unittest,wave,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[1];S=R/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from narrative_checks import evidence,graph,season
from publication_tools import epub,screenplay,manuscript_audit
from production_registry import check_registry,estimate,capture_versions
from creative_tools import plan
from subtitle_tools import compare_versions
from media_review import audio_qc,contact_sheet
class DeliveryTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def put(self,name,data):p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');return p
 def test_disclosure_holders_and_equal_time_order(self):
  d={'characters':['A','B'],'facts':[{'id':'F','known_by':['A']}],'events':[{'id':'E1','story_time':1,'reveals':[{'fact':'F','to':['B']}]},{'id':'E2','story_time':1,'uses':[{'fact':'F','by':'B'}]}]}
  self.assertFalse(graph(d)['valid']);d['events'][1]['requires']=['E1'];self.assertTrue(graph(d)['valid']);d['events'][0]['reveals'][0]['to']=['A'];self.assertFalse(graph(d)['valid'])
 def test_causal_cycles_and_future_dependencies_fail(self):
  d={'characters':[],'facts':[],'events':[{'id':'A','story_time':2},{'id':'B','story_time':1,'requires':['A']}]};self.assertFalse(graph(d)['valid']);d['events'][0]['requires']=['B'];self.assertTrue(any('cycle' in s for s in graph(d)['errors']))
 def test_fact_citations_and_supplied_quotation(self):
  d={'sources':[{'id':'S1','title':'Source','url':'https://example.org/source','accessed':'2026-11-01','excerpt':'A supplied excerpt.'}],'claims':[{'id':'C1','kind':'fact','statement':'Statement','source_ids':['S1'],'used_at':['S01'],'quote':'supplied excerpt'}]}
  self.assertTrue(evidence(d)['valid']);d['claims'][0]['quote']='invented words';self.assertFalse(evidence(d)['valid']);d['claims'][0]['quote']='';d['claims'][0]['source_ids']=[];self.assertFalse(evidence(d)['valid'])
 def test_season_completion_requires_payoff_evidence(self):
  d={'units':['E001','E002'],'promises':[{'id':'P1','setup':'E001','payoff':'E002','status':'resolved'}]};self.assertFalse(season(d)['valid']);d['promises'][0]['evidence']='E002/S03: letter returned';self.assertTrue(season(d)['valid'])
 def test_epub_chapter_order_and_text_are_preserved(self):
  source=S/'assets/example-novel.json';out=self.root/'book.epub';before=source.read_bytes();r=epub(source,out);self.assertFalse(r['epubcheck_run']);d=json.loads(before)
  with zipfile.ZipFile(out) as z:
   self.assertIsNone(z.testzip());self.assertEqual(z.infolist()[0].filename,'mimetype');self.assertEqual(z.infolist()[0].compress_type,zipfile.ZIP_STORED)
   opf=ET.fromstring(z.read('EPUB/package.opf'));ns={'p':'http://www.idpf.org/2007/opf'};self.assertEqual([e.attrib['idref'] for e in opf.findall('p:spine/p:itemref',ns)],['ch001','ch002'])
   for c in d['chapters']:
    xml=ET.fromstring(z.read(f'EPUB/ch{c["n"]:03}.xhtml'));text='\n'.join(''.join(p.itertext()) for p in xml.findall('.//{http://www.w3.org/1999/xhtml}p'));self.assertEqual(text,c['body'])
  self.assertEqual(before,source.read_bytes())
  with self.assertRaises(ValueError):epub(source,out)
 def test_incomplete_novel_cannot_be_exported_as_complete(self):
  d=json.loads((S/'assets/example-novel.json').read_text(encoding='utf-8'));d['project']['planned_chapters']=3;p=self.put('novel.json',d)
  with self.assertRaises(ValueError):epub(p,self.root/'book.epub')
 def test_manuscript_repetition_report_does_not_rewrite(self):
  d=json.loads((S/'assets/example-novel.json').read_text(encoding='utf-8'));d['chapters'][1]['body']+='\n'+d['chapters'][0]['body'].splitlines()[0];p=self.put('novel.json',d);before=p.read_bytes();self.assertTrue(manuscript_audit(p)['repeated_paragraph_candidates']);self.assertEqual(before,p.read_bytes())
 def test_take_selection_requires_current_hash_and_review(self):
  plan=self.put('plan.json',{'meta':{'title':'Sample','fps':24},'shots':[{'id':'S01_001','scene':1,'first_frame':0,'end_frame_exclusive':24,'picture':'x'}]});media=self.root/'take.bin';media.write_bytes(b'actual fixture bytes')
  d={'source_plan_sha256':hashlib.sha256(plan.read_bytes()).hexdigest(),'references':[],'takes':[{'id':'T1','path':'take.bin','sha256':hashlib.sha256(media.read_bytes()).hexdigest(),'shot':'S01_001','status':'candidate'}],'selected':{'S01_001':'T1'}};p=self.put('registry.json',d);self.assertFalse(check_registry(p,plan)['valid']);d['takes'][0].update(status='approved',review_note='Human selected fixture');self.put('registry.json',d);self.assertTrue(check_registry(p,plan)['valid']);media.write_bytes(b'changed');self.assertFalse(check_registry(p,plan)['valid'])
  captured=self.root/'captured.json';capture_versions(p,plan,captured);value=json.loads(captured.read_text(encoding='utf-8'));self.assertEqual(value['takes'][0]['status'],'candidate');self.assertEqual(value['selected'],{});self.assertNotIn('review_note',value['takes'][0]);self.assertNotEqual(value['takes'][0]['sha256'],d['takes'][0]['sha256'])
 def test_extension_routes_preserve_requested_scope(self):
  for request,task in [('检查研究证据','evidence'),('检查主角提前知道密码','causal'),('审查整季兑现','season-grid'),('小说机械校对','proofread'),('导出EPUB','publish-book'),('导出FDX','screenplay-export'),('整理姿态控制参考','reference-controls'),('候选镜头选片','takes'),('做接触表','contact'),('测量对白WAV响度','audio-qc'),('核对翻译字幕','localize')]:
   p=plan(request);self.assertEqual(p['task'],task);self.assertNotIn('premise',{m['id'] for m in p['modules']})
  self.assertEqual(plan('导出EPUB')['mode'],'novel');p=plan('写一部完整电影，之后导出FDX');self.assertEqual(p['task'],'full');self.assertIn('screenplay-interchange',{m['id'] for m in p['modules']})
 def test_cost_uses_native_seconds_and_keeps_post_tasks_separate(self):
  d={'video_jobs':[{'id':'A','native_duration_sec':5},{'id':'B','native_duration_sec':6}],'post_tasks':[{'id':'C'}]};r=estimate(d,.2,3,'USD');self.assertEqual(r['scenario_cost'],6.6);self.assertEqual(r['excluded_post_tasks'],1);self.assertEqual(r['submitted_jobs'],0)
  with self.assertRaises(ValueError):estimate(d,float('nan'),1,'USD')
 def test_subtitle_translation_keeps_times_but_not_necessarily_text(self):
  a='1\n00:00:00,100 --> 00:00:01,000\n你好。\n';b=a.replace('你好。','Hello.');self.assertTrue(compare_versions(a,b)['valid']);self.assertEqual(compare_versions(a,b)['changed_text_cues'],[1]);self.assertFalse(compare_versions(a,b.replace('01,000','01,100'))['valid'])
 @unittest.skipUnless(importlib.util.find_spec('screenplain'),'optional screenplain')
 def test_actual_fdx_serialization_preserves_dialogue_literals(self):
  from film_pipeline import compile_film
  d=json.loads((S/'assets/example-film.json').read_text(encoding='utf-8'));source=self.put('film.json',d);p=self.root/'film.fdx';screenplay(source,p);xml=ET.parse(p);self.assertEqual(xml.getroot().tag,'FinalDraft')
  texts=[''.join(t.text or '' for t in e.findall('Text')) for e in xml.findall('.//Content/Paragraph[@Type="Dialogue"]')];expected=[line['text'] for shot in compile_film(d)['shots'] for line in shot['dialogue']];self.assertEqual(texts,expected)
 @unittest.skipUnless(importlib.util.find_spec('screenplain'),'optional screenplain')
 def test_exported_chinese_fountain_parses_as_actual_dialogue(self):
  from screenplain.parsers.fountain import parse
  from screenplain.types import Dialog,Slug
  p=self.root/'film.fountain';screenplay(S/'assets/example-film.json',p)
  with p.open(encoding='utf-8') as f:doc=parse(f)
  self.assertEqual(sum(isinstance(x,Slug) for x in doc.paragraphs),3);self.assertGreater(sum(isinstance(x,Dialog) for x in doc.paragraphs),0)
 @unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('pyloudnorm'),'optional loudness dependencies')
 def test_actual_pcm_audio_measurement_is_finite_and_nonmutating(self):
  import numpy as np
  rate=48000;pcm=(.1*np.sin(2*np.pi*1000*np.arange(rate)/rate)*32767).astype('<i2');p=self.root/'tone.wav'
  with wave.open(str(p),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(pcm.tobytes())
  before=p.read_bytes();r=audio_qc(p,-23);self.assertAlmostEqual(r['sample_peak_dbfs'],-20,places=2);self.assertTrue(math.isfinite(r['integrated_lufs']));self.assertEqual(r['duration_sec'],1);self.assertFalse(r['audio_modified']);self.assertEqual(before,p.read_bytes())
 @unittest.skipUnless(importlib.util.find_spec('av') and importlib.util.find_spec('PIL') and importlib.util.find_spec('numpy'),'optional image/video dependencies')
 def test_contact_sheet_uses_real_first_and_last_frames(self):
  from test_optional_media import write_fixture
  from PIL import Image
  p=self.root/'clip.mp4';write_fixture(p);out=self.root/'contact.png';r=contact_sheet(p,out,4);self.assertEqual([r['selected_frames'][i]['frame'] for i in (0,-1)],[0,47])
  with Image.open(out) as im:self.assertEqual(im.size,(1280,206));self.assertGreater(im.getpixel((160,90))[0],180);self.assertGreater(im.getpixel((1120,90))[2],180)
if __name__=='__main__':unittest.main()
