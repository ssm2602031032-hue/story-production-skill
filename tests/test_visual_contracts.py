import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1];S=R/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from visual_contracts import validate,compile_contract,build,style_spec,ab_suite
from delivery_utils import digest
from motion_probe import measure,detail_sheet
from creative_tools import plan as route
class VisualContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.data=json.loads((S/'assets/example-visual-contract.json').read_text(encoding='utf-8'));self.source=self.root/'visual.json';self.save()
 def save(self):self.source.write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
 def tearDown(self):self.tmp.cleanup()
 def test_missing_references_cannot_claim_locked_vehicle_or_generated_scores(self):
  r=compile_contract(self.source);self.assertEqual(len(r['jobs']),6);self.assertTrue(r['reference_tasks']);self.assertFalse(r['media_generated']);self.assertTrue(all(not j['ready_for_reference_conditioned_attempt'] for j in r['jobs']));self.assertTrue(all(j['test']['identity_score'] is None for j in r['jobs']))
 def test_car_identity_override_and_unexplained_damage_are_rejected(self):
  self.data['shots'][1]['identity_overrides']={'车门数':4};self.save();self.assertFalse(validate(self.source)['valid'])
  self.data['shots'][1].pop('identity_overrides');self.data['assets'][0]['states']['damaged']='New damage';self.data['shots'][1]['state']='damaged';self.save();self.assertTrue(any('state/damage' in x for x in validate(self.source)['errors']))
 def test_direction_flip_across_driver_insert_still_requires_spatial_reset(self):
  self.data['shots'][3]['screen_direction']='right_to_left';self.save();self.assertTrue(any('including across inserts' in e for e in validate(self.source)['errors']))
  self.data['shots'][3]['axis_reset_reason']='An authored wide reset establishes the new side';self.save();self.assertTrue(validate(self.source)['valid'])
 def test_speed_has_visible_cues_and_no_unintentional_slowdown(self):
  self.data['shots'][1]['playback_rate']=.5;self.save();self.assertFalse(validate(self.source)['valid']);self.data['shots'][1]['playback_rate']=1;self.data['shots'][1]['speed_cues']=[];self.save();self.assertFalse(validate(self.source)['valid'])
 def test_authored_distance_and_time_must_agree_with_claimed_speed(self):
  self.data['shots'][1].update(distance_m=4,declared_speed_kmh=120);self.save();self.assertTrue(any('distance/time' in e for e in validate(self.source)['errors']))
 def test_style_swap_preserves_identity_action_and_duration(self):
  first=compile_contract(self.source);styles=json.loads((S/'assets/visual-style-cards.json').read_text(encoding='utf-8'))['styles'];self.data['style']=styles['restrained-luxury'];self.save();second=compile_contract(self.source)
  for a,b in zip(first['jobs'],second['jobs']):self.assertEqual(a['identity_anchor'],b['identity_anchor']);self.assertEqual(a['duration_sec'],b['duration_sec']);self.assertNotEqual(a['positive_prompt'],b['positive_prompt'])
  self.assertEqual([x['action'] for x in first['directives'].values()],[x['action'] for x in second['directives'].values()])
 def test_style_label_alone_or_style_identity_override_is_not_executable(self):
  with self.assertRaises(ValueError):style_spec({'label':'cinematic'})
  self.data['style']['vehicle_paint']='red'
  with self.assertRaises(ValueError):style_spec(self.data['style'])
 def test_base_generation_jobs_guard_mode_duration_and_ids(self):
  base=self.root/'jobs.json';base.write_text(json.dumps({'video_jobs':[{'id':s['id'],'mode':'i2v','usable_duration_sec':s['duration_sec'],'edit_fps':24} for s in self.data['shots']]}));self.assertTrue(validate(self.source,base)['valid'])
  d=json.loads(base.read_text());d['video_jobs'][0]['usable_duration_sec']=10;base.write_text(json.dumps(d));self.assertFalse(validate(self.source,base)['valid'])
 @unittest.skipUnless(importlib.util.find_spec('PIL'),'optional Pillow')
 def test_scene_keyframe_role_hash_and_approval_bind_real_files(self):
  from PIL import Image
  im=self.root/'test.png';Image.new('RGB',(32,32),'black').save(im);a=self.data['assets'][0];a['references']=[{'id':'REF1','role':'first_frame','view':'wide','path':'test.png','sha256':digest(im),'approved':True,'approval_note':'Approved as a synthetic unit-test image only','inherit':'test image geometry','exclude':'no real vehicle identity is claimed'}];self.data['shots'][0]['conditioning']={'first':'REF1'};self.save();out=self.root/'bundle';r=build(self.source,out);self.assertEqual(r['ready_reference_attempts'],1);m=json.loads((out/'reference-map.json').read_text());self.assertTrue((out/m[self.data['shots'][0]['id']]['first']).is_file())
  a['references'][0]['role']='identity';self.save();self.assertFalse(validate(self.source)['valid']);a['references'][0]['role']='first_frame';im.write_bytes(b'changed');self.assertFalse(validate(self.source)['valid'])
 def test_visible_features_follow_view_without_forcing_front_parts_into_rear(self):
  r=compile_contract(self.source);rear=next(j for j in r['jobs'] if j['view']=='rear_three_quarter');self.assertIn('尾灯',rear['positive_prompt']);self.assertNotIn('前灯与进气格栅',rear['positive_prompt'])
 def test_global_camera_menu_is_not_issued_as_multiple_moves_in_one_shot(self):
  r=compile_contract(self.source);shot=r['jobs'][1];self.assertIn('固定路边机位',shot['positive_prompt']);self.assertNotIn(self.data['style']['camera_behavior'],shot['positive_prompt']);self.assertEqual(shot['camera_rule_for_author'],self.data['style']['camera_behavior'])
 def test_package_is_portable_and_unrun(self):
  out=self.root/'bundle';before=self.source.read_bytes();build(self.source,out);self.assertEqual(self.source.read_bytes(),before);self.assertTrue((out/'reference-tasks.json').is_file());self.assertFalse(json.loads((out/'manifest.json').read_text())['media_generated'])
 def test_single_field_style_ab_keeps_geometry_motion_and_unrun_scores(self):
  before=self.source.read_bytes();r=ab_suite(self.source,'style.texture','Matte rubber and continuous body reflections; no added sharpening.');self.assertEqual(before,self.source.read_bytes());self.assertIsNone(r['scores']);self.assertIsNone(r['winner']);self.assertFalse(r['generated_media'])
  for a,b in zip(r['baseline']['jobs'],r['candidate']['jobs']):self.assertEqual(a['identity_anchor'],b['identity_anchor']);self.assertEqual(a['duration_sec'],b['duration_sec'])
  with self.assertRaises(ValueError):ab_suite(self.source,'asset.paint','red')
 def test_absent_approved_image_and_unplanned_view_change_are_rejected(self):
  ref={'id':'R1','role':'first_frame','view':'rear','approved':True,'inherit':'identity','exclude':'other assets'};self.data['assets'][0]['references']=[ref];self.data['shots'][0]['conditioning']={'first':'R1'};self.save();r=validate(self.source);self.assertFalse(r['valid']);self.assertTrue(any('absent' in e for e in r['errors']));self.assertTrue(any('view differs' in e for e in r['errors']))
HAVE=all(importlib.util.find_spec(x) for x in ('av','cv2','numpy','PIL'))
@unittest.skipUnless(HAVE,'optional actual video/flow environment')
class MotionProbeTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def fixture(self,path,moving):
  import av,numpy as np
  rng=np.random.default_rng(4);background=rng.integers(30,220,(64,96),dtype=np.uint8);vehicle=rng.integers(40,200,(24,40),dtype=np.uint8)
  with av.open(str(path),'w') as c:
   stream=c.add_stream('ffv1',rate=24);stream.width=96;stream.height=64;stream.pix_fmt='yuv420p'
   for n in range(18):
    gray=np.roll(background,2*n if moving else 0,axis=1);gray[32:56,28:68]=vehicle;rgb=np.repeat(gray[:,:,None],3,axis=2);frame=av.VideoFrame.from_ndarray(rgb,format='rgb24')
    for packet in stream.encode(frame):c.mux(packet)
   for packet in stream.encode():c.mux(packet)
 def test_tracking_like_background_motion_is_measured_separately_from_subject(self):
  moving=self.root/'moving.mkv';still=self.root/'still.mkv';self.fixture(moving,True);self.fixture(still,False);regions={'background':[.1,.08,.8,.3],'vehicle':[.4,.6,.15,.15]};r=measure(moving,regions,max_frames=18);s=measure(still,regions,max_frames=18)
  self.assertGreater(r['summary']['background']['median_frame_widths_per_sec'],.2);self.assertLess(s['summary']['background']['median_frame_widths_per_sec'],.01);self.assertLess(r['summary']['vehicle']['median_frame_widths_per_sec'],.1);self.assertIsNone(r['ground_speed_kmh']);self.assertIsNone(r['realism_score'])
 def test_detail_crops_preserve_decoded_pixels_without_softening(self):
  import av,numpy as np
  from PIL import Image
  source=self.root/'source.mkv';self.fixture(source,True);out=self.root/'details.png';r=detail_sheet(source,[0,5],[28,32,40,24],out);self.assertFalse(r['resized']);self.assertEqual(r['scale'],1)
  with av.open(str(source)) as c:first=next(c.decode(video=0)).to_ndarray(format='rgb24')
  with Image.open(out) as im:self.assertTrue(np.array_equal(np.asarray(im)[:24,:40],first[32:56,28:68]));self.assertEqual(im.width,r['cell_width']*2);self.assertGreaterEqual(r['cell_width'],240)
class UniversalAssetTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.source=self.root/'contract.json';self.data=json.loads((S/'assets/example-multiasset-visual-contract.json').read_text(encoding='utf-8'));self.save()
 def save(self):self.source.write_text(json.dumps(self.data,ensure_ascii=False),encoding='utf-8')
 def tearDown(self):self.tmp.cleanup()
 def test_people_wardrobe_prop_and_location_are_kept_distinct(self):
  r=compile_contract(self.source);self.assertEqual({x['asset'] for x in r['jobs'][0]['supporting_assets']},{'C02','P01','L01'});self.assertIn('蓝色',r['jobs'][0]['positive_prompt']);self.assertIn('浅色木门',r['jobs'][0]['positive_prompt']);self.assertTrue(r['jobs'][0]['dramatic_goal'])
 def test_hand_closeup_does_not_request_hidden_face_or_hair(self):
  r=compile_contract(self.source);prompt=r['jobs'][1]['positive_prompt'];self.assertNotIn('黑色短发',prompt);self.assertNotIn('深棕色齐肩发',prompt);self.assertIn('米色袖口',prompt);self.assertIn('黑色短发',r['jobs'][1]['supporting_assets'][0]['identity_anchor'])
 def test_secondary_identity_and_transferred_prop_state_are_checked(self):
  self.data['shots'][0]['supporting_assets'][0]['identity_overrides']={'发型':'金色卷发'};self.save();self.assertFalse(validate(self.source)['valid']);self.data['shots'][0]['supporting_assets'][0].pop('identity_overrides');self.data['shots'][2]['supporting_assets'][0]['entry_facts']['holder']='C01';self.save();self.assertFalse(validate(self.source)['valid'])
 def test_authored_wardrobe_phase_can_change_without_changing_identity(self):
  self.data['assets'][0]['states']['LOOK_C']='蓝色外套，属于明确的后续造型阶段';b=self.data['shots'][1]['supporting_assets'][0];b.update(state='LOOK_C',state_change_reason='测试指定的造型阶段切换');self.save();self.assertTrue(validate(self.source)['valid'])
 def test_static_product_uses_same_contract_without_forcing_speed(self):
  r=compile_contract(S/'assets/example-product-visual-contract.json');self.assertEqual(r['jobs'][0]['asset'],'P01');self.assertIn('单个',r['jobs'][0]['positive_prompt']);self.assertNotIn('动作按实时速度发生',r['jobs'][0]['positive_prompt']);self.assertIsNone(r['jobs'][0]['test']['style_score'])
 def test_general_routes_do_not_capture_novel_voice_or_intentional_painting(self):
  for request,task in [('处理人物外观漂移和道具前后不一致','visual-identity'),('修正动作悬浮和没有重量感','motion-direction'),('检查物品交接','action-continuity'),('把视觉风格写成提示词','style-visual'),('排查画质很油','material'),('准备多资产首帧','reference-binding'),('测量图像运动量','motion-evidence'),('输出原尺寸细节','look-ab')]:self.assertEqual(route(request)['task'],task)
  self.assertNotIn(route('写一个油画风格的视频提示词')['task'],('material','style-visual'));self.assertEqual(route('修改小说的不同文风')['mode'],'novel');self.assertNotIn('style-to-visual',{m['id'] for m in route('修改小说的不同文风')['modules']})
 @unittest.skipUnless(importlib.util.find_spec('PIL'),'optional Pillow')
 def test_multiasset_frame_requires_declared_review_coverage(self):
  from PIL import Image
  p=self.root/'scene.png';Image.new('RGB',(32,32),'gray').save(p);ref={'id':'R1','role':'first_frame','view':'wide','path':'scene.png','sha256':digest(p),'approved':True,'approval_note':'Technical test artifact only','inherit':'scene','exclude':'not a real identity test','covers_assets':['C01']};self.data['assets'][0]['references']=[ref];self.data['shots'][0]['conditioning']={'first':'R1'};self.save();r=compile_contract(self.source);self.assertFalse(r['jobs'][0]['ready_for_reference_conditioned_attempt']);ref['covers_assets']=['C01','C02','P01','L01'];self.save();self.assertTrue(compile_contract(self.source)['jobs'][0]['ready_for_reference_conditioned_attempt'])
if __name__=='__main__':unittest.main()
