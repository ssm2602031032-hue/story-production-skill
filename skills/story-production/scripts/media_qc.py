#!/usr/bin/env python3
"""Read-only technical media checks using optional PyAV; no realism or artistic score."""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
from fractions import Fraction
from creative_tools import safe_write
def media_hash(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def inspect_video(path,max_frames=240,expected_fps=None,expected_frames=None,expected_width=None,expected_height=None):
 try:import av
 except ImportError as e:raise ValueError('PyAV is unavailable. Install requirements-media.txt in the selected environment; no media check was performed.') from e
 path=Path(path).resolve()
 if not path.is_file():raise ValueError('Video file does not exist')
 if not isinstance(max_frames,int) or isinstance(max_frames,bool) or max_frames<0:raise ValueError('max_frames must be a nonnegative integer; 0 explicitly scans all frames')
 if expected_fps is not None and (not isinstance(expected_fps,(int,float)) or isinstance(expected_fps,bool) or not math.isfinite(expected_fps) or expected_fps<=0):raise ValueError('expected_fps must be finite and positive')
 for name,value in [('expected_frames',expected_frames),('expected_width',expected_width),('expected_height',expected_height)]:
  if value is not None and (not isinstance(value,int) or isinstance(value,bool) or value<=0):raise ValueError(name+' must be a positive integer')
 errors=[];warnings=[];timestamps=[];frames=0;repeated=0;black=0;previous=None;last_ts=None;previous_ts=None;max_repeat=0;run=0;limited=False
 with av.open(str(path)) as container:
  videos=list(container.streams.video)
  if not videos:raise ValueError('File has no video stream')
  stream=videos[0];rate=stream.average_rate;fps=float(rate) if rate else None;width=stream.codec_context.width;height=stream.codec_context.height
  audio=[{'codec':s.codec_context.name,'sample_rate':s.codec_context.sample_rate,'channels':s.codec_context.channels} for s in container.streams.audio]
  declared_frames=stream.frames or None;duration=float(stream.duration*stream.time_base) if stream.duration is not None and stream.time_base is not None else float(container.duration/av.time_base) if container.duration is not None else None
  for frame in container.decode(stream):
   if max_frames and frames>=max_frames:limited=True;break
   frames+=1;ts=float(frame.pts*frame.time_base) if frame.pts is not None and frame.time_base is not None else None
   if ts is not None:
    if last_ts is not None:
     delta=ts-last_ts;timestamps.append(delta)
     if delta<=0:errors.append(f'Non-increasing decoded timestamp at frame {frames}')
    previous_ts,last_ts=last_ts,ts
   # Coarse fingerprints flag review locations; a static tripod shot is not automatically wrong.
   small=frame.reformat(width=32,height=18,format='gray');plane=small.planes[0];raw=bytes(plane);line=plane.line_size
   pixels=b''.join(raw[y*line:y*line+32] for y in range(18));current=hashlib.sha256(pixels).hexdigest()
   if current==previous:repeated+=1;run+=1
   else:max_repeat=max(max_repeat,run);run=0
   previous=current
   if pixels and sum(pixels)/len(pixels)<5:black+=1
  max_repeat=max(max_repeat,run)
  codec=stream.codec_context.name
 if frames==0:errors.append('No video frames decoded')
 if expected_fps is not None and (fps is None or abs(fps-expected_fps)>.01):errors.append('Average frame rate differs from expected edit rate; do not silently reinterpret playback speed')
 if expected_width is not None and width!=expected_width:errors.append('Width differs from expected value')
 if expected_height is not None and height!=expected_height:errors.append('Height differs from expected value')
 if expected_frames is not None:
  actual=declared_frames if limited else frames
  if actual is None:warnings.append('Full frame count is unknown; run a full decode to verify')
  elif actual!=expected_frames:errors.append(f'Frame count differs: observed {actual}, expected {expected_frames}')
 spread=max(timestamps)-min(timestamps) if timestamps else None
 if spread is not None and fps and spread>max(.002,1/fps*.1):warnings.append('Decoded timestamp spacing varies; review VFR/conform policy before editing')
 if max_repeat>=max(3,round((fps or 24)*.5)):warnings.append('Coarse repeated-frame run detected; inspect whether it is an intended hold or unwanted freeze')
 if black:warnings.append('Near-black frames exist; inspect whether they are intentional black/transition frames')
 if limited:warnings.append('Only the opening sample was decoded; unexamined later footage is not validated')
 return {'version':'1.3.0','media':path.name,'sha256':media_hash(path),'backend':{'pyav':av.__version__},'video':{'codec':codec,'width':width,'height':height,'average_fps':fps,'rate_fraction':str(rate) if rate else None,'declared_frames':declared_frames,'duration_sec':duration},'audio':audio,'sample':{'decoded_frames':frames,'entire_video_decoded':not limited,'last_timestamp_sec':last_ts,'timestamp_delta_spread_sec':spread,'coarse_repeated_frames':repeated,'longest_repeat_transitions':max_repeat,'near_black_frames':black},'valid':not errors,'errors':errors,'warnings':warnings,'limits':'Technical metadata/timestamp and coarse image checks only. Does not establish photorealism, identity consistency, correct acting, lip sync, or artistic quality.'}
def detect_cuts(path,threshold=3.0):
 try:from scenedetect import detect,AdaptiveDetector
 except ImportError as e:raise ValueError('PySceneDetect/OpenCV not installed; scene detection was not run') from e
 if not math.isfinite(threshold) or threshold<=0:raise ValueError('threshold must be positive')
 scenes=detect(str(Path(path).resolve()),AdaptiveDetector(adaptive_threshold=threshold),show_progress=False)
 def frame(t):return t.frame_num if hasattr(t,'frame_num') else t.get_frames()
 def sec(t):return t.seconds if hasattr(t,'seconds') else t.get_seconds()
 return {'backend':'PySceneDetect AdaptiveDetector','detected_intervals':[{'start_frame':frame(a),'end_frame_exclusive':frame(b),'start_seconds':sec(a),'end_seconds':sec(b)} for a,b in scenes],'limits':'Detected cuts/transitions are technical candidates, not screenplay scene boundaries or proof of continuity.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('media',type=Path);p.add_argument('--max-frames',type=int,default=240);p.add_argument('--fps',type=float);p.add_argument('--frames',type=int);p.add_argument('--width',type=int);p.add_argument('--height',type=int);p.add_argument('--detect-cuts',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  r=inspect_video(a.media,a.max_frames,a.fps,a.frames,a.width,a.height)
  if a.detect_cuts:r['cut_detection']=detect_cuts(a.media)
  safe_write(a.out,r);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['valid'] else 1
 except Exception as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
