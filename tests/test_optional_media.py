"""CPU media adapter checks on generated technical fixtures, never model-generated content."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'skills/story-production/scripts'))
from media_qc import inspect_video,detect_cuts
from editorial_export import build_timeline
HAVE_MEDIA=all(importlib.util.find_spec(x) for x in ('av','numpy','opentimelineio'))
def write_fixture(path,rate=24,frames=48):
 import av,numpy as np
 with av.open(str(path),'w') as c:
  s=c.add_stream('mpeg4',rate=rate);s.width=64;s.height=48;s.pix_fmt='yuv420p'
  for i in range(frames):
   a=np.zeros((48,64,3),dtype=np.uint8);a[:,:,0 if i<frames//2 else 2]=200
   f=av.VideoFrame.from_ndarray(a,format='rgb24')
   for packet in s.encode(f):c.mux(packet)
  for packet in s.encode():c.mux(packet)
@unittest.skipUnless(HAVE_MEDIA,'Optional PyAV/NumPy/OpenTimelineIO environment is not installed')
class MediaAdapterTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.media=self.root/'fixture.mp4';write_fixture(self.media)
  self.plan=self.root/'shot-plan.json';self.plan.write_text(json.dumps({'meta':{'title':'Technical fixture','fps':24},'shots':[{'id':'S01_001','scene':1,'first_frame':0,'end_frame_exclusive':24,'picture':'red hold','pure_post':False},{'id':'S02_001','scene':2,'first_frame':24,'end_frame_exclusive':48,'picture':'blue hold','pure_post':False}]}))
  self.mapping=self.root/'media-map.json';self.mapping.write_text(json.dumps({'S01_001':{'path':'fixture.mp4','source_in_frame':0},'S02_001':{'path':'fixture.mp4','source_in_frame':24}}))
 def tearDown(self):self.tmp.cleanup()
 def test_real_file_metadata_and_decoded_coverage(self):
  r=inspect_video(self.media,max_frames=0,expected_fps=24,expected_frames=48,expected_width=64,expected_height=48)
  self.assertTrue(r['valid'],r);self.assertEqual(r['sample']['decoded_frames'],48);self.assertTrue(r['sample']['entire_video_decoded']);self.assertEqual(r['video']['average_fps'],24);self.assertGreater(r['sample']['coarse_repeated_frames'],0)
 def test_sampled_report_does_not_claim_unseen_tail(self):
  r=inspect_video(self.media,max_frames=10);self.assertEqual(r['sample']['decoded_frames'],10);self.assertFalse(r['sample']['entire_video_decoded']);self.assertTrue(any('unexamined' in x for x in r['warnings']))
 def test_wrong_expected_fps_and_count_fail(self):
  r=inspect_video(self.media,max_frames=0,expected_fps=30,expected_frames=80);self.assertFalse(r['valid']);self.assertEqual(len(r['errors']),2)
 def test_invalid_expectations_cannot_silently_pass(self):
  for kwargs in ({'expected_fps':float('nan')},{'expected_fps':0},{'expected_frames':-1},{'expected_width':True},{'expected_height':1.5}):
   with self.assertRaises(ValueError):inspect_video(self.media,**kwargs)
 def test_otio_roundtrip_preserves_clip_ranges_and_total_frames(self):
  import opentimelineio as otio
  target=self.root/'edit/timeline.otio';r=build_timeline(self.plan,target,self.mapping)
  self.assertEqual(r['story_frames'],48);self.assertFalse(r['missing_shots']);self.assertFalse(r['rendered_video'])
  t=otio.adapters.read_from_file(str(target));self.assertEqual(t.duration().rescaled_to(24).value,48);self.assertEqual(t.tracks[0][1].source_range.start_time.value,24)
  self.assertEqual(t.tracks[0][0].media_reference.target_url,'../fixture.mp4')
 def test_missing_timeline_is_explicit_and_not_a_final_film(self):
  with self.assertRaises(ValueError):build_timeline(self.plan,self.root/'bad.otio')
  r=build_timeline(self.plan,self.root/'planning.otio',allow_missing=True);self.assertEqual(r['status'],'planning-missing-media');self.assertEqual(len(r['missing_shots']),2)
 def test_out_of_range_media_and_rate_mismatch_are_rejected(self):
  self.mapping.write_text(json.dumps({'S01_001':{'path':'fixture.mp4','source_in_frame':40},'S02_001':{'path':'fixture.mp4'}}))
  with self.assertRaises(ValueError):build_timeline(self.plan,self.root/'range.otio',self.mapping)
  fast=self.root/'fast.mp4';write_fixture(fast,rate=30)
  self.mapping.write_text(json.dumps({'S01_001':{'path':'fast.mp4'},'S02_001':{'path':'fast.mp4'}}))
  with self.assertRaises(ValueError):build_timeline(self.plan,self.root/'rate.otio',self.mapping)
 @unittest.skipUnless(importlib.util.find_spec('scenedetect') and importlib.util.find_spec('cv2'),'Optional scene detector is not installed')
 def test_scene_detector_returns_real_candidate_intervals(self):
  r=detect_cuts(self.media);self.assertTrue(r['detected_intervals']);self.assertEqual(r['detected_intervals'][0]['start_frame'],0);self.assertEqual(r['detected_intervals'][-1]['end_frame_exclusive'],48)
if __name__=='__main__':unittest.main()
