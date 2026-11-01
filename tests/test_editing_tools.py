import copy,hashlib,importlib.util,json,sys,tempfile,unittest,wave,xml.etree.ElementTree as ET
from pathlib import Path
R=Path(__file__).resolve().parents[1];S=R/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from edit_decisions import validate,capture,difference,timeline,from_shots
from edit_render import render,plan
from subtitle_conform import conform
from finishing_tools import silence,cdl,color_info,final_check
from creative_tools import plan as route
def decisions():
 return {'version':'1.5.0','title':'Technical cut fixture','fps':24,'width':96,'height':64,'color_intent':'sdr-review','embedded_audio_policy':'ignore','sources':{'V1':{'path':'source.mp4','kind':'video','sha256':'0'*64}},'picture':[{'id':'CUT1','source':'V1','in_frame':24,'out_frame':48},{'id':'CUT2','source':'V1','in_frame':0,'out_frame':24}],'audio':[]}
class CoreEditTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def put(self,name,d):p=self.root/name;p.write_text(json.dumps(d),encoding='utf-8');return p
 def test_unsupported_effects_cannot_be_silently_ignored(self):
  d=decisions();d['picture'][0]['speed']=2;p=self.put('edit.json',d)
  with self.assertRaises(ValueError):validate(p,False)
  d=decisions();d.pop('audio');p=self.put('edit.json',d)
  with self.assertRaises(ValueError):validate(p,False)
 def test_subtitle_conform_reorders_kept_cues_without_changing_words(self):
  p=self.put('edit.json',decisions());s=self.root/'source.srt';s.write_text('1\n00:00:00,100 --> 00:00:00,900\nFirst.\n\n2\n00:00:01,100 --> 00:00:01,900\nSecond.\n',encoding='utf-8');text,r=conform(p,s,'V1')
  self.assertLess(text.index('Second.'),text.index('First.'));self.assertEqual([x['original_cue'] for x in r['events']],[2,1]);self.assertEqual(r['events'][0]['in_frame'],3);self.assertFalse(r['dropped_original_cues'])
 def test_cut_through_a_subtitle_requires_review_and_dropped_cues_are_visible(self):
  d=decisions();d['picture']=d['picture'][:1];d['picture'][0]['in_frame']=36;p=self.put('edit.json',d);s=self.root/'source.srt';s.write_text('1\n00:00:00,000 --> 00:00:00,500\nGone.\n\n2\n00:00:01,000 --> 00:00:02,000\nPartially retained.\n',encoding='utf-8');text,r=conform(p,s,'V1');self.assertEqual(r['dropped_original_cues'],[1]);self.assertTrue(r['events'][0]['trimmed']);self.assertTrue(r['warnings']);self.assertIn('Partially retained.',text)
 def test_edit_diff_tracks_reorder_and_canvas_changes(self):
  d=decisions();a=self.put('before.json',d);d['picture'].reverse();d['width']=128;b=self.put('after.json',d);r=difference(a,b);self.assertEqual(len(r['changes']),2);self.assertTrue(r['canvas_changed']);self.assertFalse(r['media_checked'])
 def test_cdl_preserves_authored_values_and_rejects_invalid_power(self):
  d={'id':'LOOK_A','slope':[1,1.1,.9],'offset':[0,-.01,.02],'power':[1,1,1],'saturation':.95};out=self.root/'look.cc';r=cdl(d,out);self.assertFalse(r['applied_to_media']);self.assertEqual(ET.parse(out).findtext('SOPNode/Offset'),'0 -0.01 0.02');d['power'][0]=0
  with self.assertRaises(ValueError):cdl(d,self.root/'bad.cc')
 def test_silence_candidates_do_not_modify_wave(self):
  import array
  rate=48000;values=array.array('h',[0]*rate+[10000]*rate);p=self.root/'test.wav'
  if sys.byteorder!='little':values.byteswap()
  with wave.open(str(p),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(values.tobytes())
  before=p.read_bytes();r=silence(p);self.assertEqual(len(r['candidates']),1);self.assertEqual(r['candidates'][0]['end_sample_exclusive'],rate);self.assertFalse(r['media_modified']);self.assertEqual(before,p.read_bytes())
 def test_editing_routes_are_bounded_and_keep_full_creation_scope(self):
  for request,task in [('用这些镜头渲染预览','roughcut'),('重排字幕','subtitle-conform'),('比较剪辑版本','edit-diff'),('叙事剪辑方案','edit-story'),('做J/L声音桥','edit-dialogue'),('检测停顿候选','edit-rhythm'),('设计动作匹配','edit-transitions'),('做代理回连','proxy'),('导出CMX3600','nle'),('做调色交接','color-handoff'),('检查字幕安全区','title-layout'),('成片验收','final-qc')]:
   p=route(request);self.assertEqual(p['task'],task);self.assertNotIn('premise',{m['id'] for m in p['modules']})
  p=route('写一部完整电影，再做粗剪方案');self.assertEqual(p['task'],'full');self.assertIn('roughcut-render',{m['id'] for m in p['modules']})
HAVE=all(importlib.util.find_spec(x) for x in ('av','numpy','opentimelineio','imageio_ffmpeg'))
@unittest.skipUnless(HAVE,'optional editing environment')
class RealEditTests(unittest.TestCase):
 def setUp(self):
  import numpy as np
  from test_optional_media import write_fixture
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);write_fixture(self.root/'source.mp4');rate=48000;values=(.1*np.sin(2*np.pi*440*np.arange(rate)/rate)*32767).astype('<i2')
  with wave.open(str(self.root/'voice.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(values.tobytes())
  d=decisions();d['sources']['A1']={'path':'voice.wav','kind':'audio','sha256':'0'*64};d['audio']=[{'id':'VOICE1','source':'A1','in_frame':0,'out_frame':24,'timeline_in_frame':12,'gain_db':-3,'fade_in_frames':2,'fade_out_frames':2}]
  initial=self.root/'initial.json';initial.write_text(json.dumps(d));self.edit=self.root/'edit.json';capture(initial,self.edit)
 def tearDown(self):self.tmp.cleanup()
 def test_actual_render_has_correct_picture_order_audio_delay_and_duration(self):
  import av,numpy as np
  out=self.root/'preview.mp4';before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'source.mp4',self.root/'voice.wav')};r=render(self.edit,out);self.assertTrue(r['rendered']);self.assertEqual(r['technical_validation']['sample']['decoded_frames'],48)
  with av.open(str(out)) as c:frames=list(c.decode(video=0));first=frames[0].to_ndarray(format='rgb24')[32,48];last=frames[-1].to_ndarray(format='rgb24')[32,48];self.assertGreater(int(first[2]),150);self.assertGreater(int(last[0]),150)
  with av.open(str(out)) as c:sound=np.concatenate([x.to_ndarray() for x in c.decode(audio=0)],axis=1);self.assertLess(float(np.max(np.abs(sound[:,:16000]))),.001);self.assertGreater(float(np.max(np.abs(sound[:,30000:40000]))),.02)
  self.assertTrue(final_check(self.edit,out)['valid']);self.assertFalse(r['visual_reviewed']);self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'source.mp4',self.root/'voice.wav')})
  with self.assertRaises(ValueError):render(self.edit,out)
 def test_plan_does_not_render_and_changed_sources_fail(self):
  out=self.root/'planned.mp4';r=plan(self.edit,out);self.assertFalse(out.exists());self.assertFalse(r['rendered']);(self.root/'voice.wav').write_bytes(b'changed')
  with self.assertRaises(ValueError):validate(self.edit)
 def test_actual_otio_preserves_audio_start_and_source_ranges(self):
  import opentimelineio as otio
  out=self.root/'edit.otio';r=timeline(self.edit,out);self.assertEqual(r['audio_tracks'],1);self.assertFalse(r['mix_automation_applied']);t=otio.adapters.read_from_file(str(out));self.assertEqual(t.duration().rescaled_to(24).value,48);self.assertEqual(t.tracks[1][0].duration().value,12);self.assertEqual(t.tracks[0][0].source_range.start_time.value,24)
 @unittest.skipUnless(importlib.util.find_spec('otio_cmx3600_adapter'),'optional EDL adapter')
 def test_actual_edl_roundtrip_is_explicitly_picture_only(self):
  import opentimelineio as otio
  with self.assertRaises(ValueError):timeline(self.edit,self.root/'bad.edl')
  out=self.root/'edit.edl';r=timeline(self.edit,out,True);t=otio.adapters.read_from_file(str(out),adapter_name='cmx_3600',rate=24);self.assertEqual(t.duration().value,48);self.assertEqual(r['audio_tracks'],0);self.assertEqual(t.tracks[0][0].source_range.start_time.value,24)
  self.assertEqual([c.metadata['cmx_3600']['reel'].strip() for c in t.tracks[0]],[r['reels']['V1']]*2);self.assertIn(r['reels']['V1'],out.read_text(encoding='utf-8'))
 def test_out_of_range_audio_and_conflicting_fades_are_rejected(self):
  d=json.loads(self.edit.read_text());d['audio'][0]['fade_in_frames']=20;d['audio'][0]['fade_out_frames']=20;self.edit.write_text(json.dumps(d))
  with self.assertRaises(ValueError):validate(self.edit)
 def test_color_metadata_report_is_not_a_color_transform(self):
  r=color_info(self.root/'source.mp4');self.assertIn('color_trc',r['tags']);self.assertFalse(r['hdr_transfer_signaled'])
 def test_existing_shot_plan_import_keeps_selected_source_in(self):
  p=self.root/'shots.json';p.write_text(json.dumps({'meta':{'title':'Imported','fps':24},'shots':[{'id':'S01_001','scene':1,'first_frame':0,'end_frame_exclusive':24,'picture':'blue'},{'id':'S02_001','scene':2,'first_frame':24,'end_frame_exclusive':48,'picture':'red'}]}));m=self.root/'mapping.json';m.write_text(json.dumps({'S01_001':{'path':'source.mp4','source_in_frame':24},'S02_001':{'path':'source.mp4','source_in_frame':0}}));out=self.root/'imported.json';r=from_shots(p,m,out,96,64,[1]);v=validate(out);self.assertEqual(r['picture_clips'],1);self.assertEqual(v['picture'][0]['in_frame'],24);self.assertEqual(v['total_frames'],24);self.assertFalse(v['audio'])
if __name__=='__main__':unittest.main()
