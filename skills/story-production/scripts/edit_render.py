#!/usr/bin/env python3
"""Render a bounded SDR review sequence from declared cuts and independent WAV cues using local FFmpeg."""
from pathlib import Path
import argparse,json,shutil,subprocess,sys
from creative_tools import read,safe_write
from delivery_utils import fresh,digest
from edit_decisions import validate
from story_pipeline import contained
from media_qc import inspect_video
def ffmpeg_executable():
 found=shutil.which('ffmpeg')
 if found:return found
 try:import imageio_ffmpeg;return imageio_ffmpeg.get_ffmpeg_exe()
 except (ImportError,RuntimeError) as e:raise ValueError('Local FFmpeg unavailable; install FFmpeg or optional imageio-ffmpeg. No automatic download was performed.') from e
def plan(source,output):
 d=read(source);r=validate(source);out=Path(output)
 if out.suffix.lower()!='.mp4':raise ValueError('Review render output must be .mp4')
 fps=r['fps'];cmd=[ffmpeg_executable(),'-hide_banner','-loglevel','error','-nostdin','-n'];filters=[];videos=[];audios=[]
 for i,row in enumerate(r['picture']+r['audio']):
  p=contained(Path(source).resolve().parent,d['sources'][row['source']]['path']);cmd+=['-i',str(p)]
  if i<len(r['picture']):
   label=f'v{i}';filters.append(f'[{i}:v:0]trim=start_frame={row["in_frame"]}:end_frame={row["out_frame"]},setpts=N/{fps}/TB,scale={d["width"]}:{d["height"]}:force_original_aspect_ratio=decrease,pad={d["width"]}:{d["height"]}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[{label}]');videos.append(f'[{label}]')
  else:
   j=i-len(r['picture']);label=f'a{j}';length=(row['out_frame']-row['in_frame'])/fps;samples=48000//fps
   chain=f'[{i}:a:0]atrim=start_sample={row["in_frame"]*samples}:end_sample={row["out_frame"]*samples},asetpts=PTS-STARTPTS,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,volume={row["gain_db"]:.9f}dB'
   if row['fade_in_frames']:chain+=f',afade=t=in:st=0:d={row["fade_in_frames"]/fps:.9f}'
   if row['fade_out_frames']:chain+=f',afade=t=out:st={length-row["fade_out_frames"]/fps:.9f}:d={row["fade_out_frames"]/fps:.9f}'
   chain+=f',adelay={row["timeline_in_frame"]*samples}S:all=1[{label}]';filters.append(chain);audios.append(f'[{label}]')
 filters.append(''.join(videos)+f'concat=n={len(videos)}:v=1:a=0[vout]')
 if audios:filters.append(''.join(audios)+f'amix=inputs={len(audios)}:duration=longest:dropout_transition=0:normalize=0,apad=whole_len={r["total_frames"]*(48000//fps)},atrim=end_sample={r["total_frames"]*(48000//fps)}[aout]')
 cmd+=['-filter_complex',';'.join(filters),'-map','[vout]']
 if audios:cmd+=['-map','[aout]','-c:a','aac','-b:a','192k','-ar','48000','-ac','2']
 else:cmd+=['-an']
 cmd+=['-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-r',str(fps),'-frames:v',str(r['total_frames']),'-movflags','+faststart',str(out.resolve())]
 if sum(len(x)+3 for x in cmd)>28000:raise ValueError('Command is too large for portable execution; split this review sequence')
 return {'command':cmd,'frames':r['total_frames'],'fps':fps,'width':d['width'],'height':d['height'],'audio_expected':bool(audios),'warnings':r['warnings'],'source_decisions_sha256':digest(source),'rendered':False,'limits':'CFR SDR review encode, straight picture cuts, explicit WAV cues; letterbox fit; no source embedded audio, grades, picture transitions, burned subtitles or titles.'}
def render(source,output,timeout=600):
 out=fresh(output,'.mp4');r=plan(source,out)
 if not isinstance(timeout,int) or isinstance(timeout,bool) or timeout<1:raise ValueError('timeout must be positive seconds')
 run=subprocess.run(r['command'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
 if run.returncode:raise ValueError('FFmpeg render failed; any partial output is not verified: '+run.stderr[-2400:])
 checked=inspect_video(out,max_frames=0,expected_fps=r['fps'],expected_frames=r['frames'],expected_width=r['width'],expected_height=r['height'])
 if not checked['valid'] or bool(checked['audio'])!=r['audio_expected']:raise ValueError('Rendered streams/frame count failed validation: '+'; '.join(checked['errors']))
 if digest(source)!=r['source_decisions_sha256']:raise ValueError('Edit decisions changed while rendering; output is not approved')
 validate(source) # Detect source bytes changed during the render.
 return {**r,'rendered':True,'output':str(out),'sha256':digest(out),'technical_validation':checked,'visual_reviewed':False,'auditory_reviewed':False,'status':'review-render; not a graded/mixed/final-approved master'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['plan','render']);p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 try:
  fresh(a.report,'.json')
  if a.out.resolve()==a.report.resolve():raise ValueError('Media and report paths must differ')
  r=plan(a.input,a.out) if a.command=='plan' else render(a.input,a.out,a.timeout);safe_write(a.report,r);print(json.dumps({k:v for k,v in r.items() if k!='command'},ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError,subprocess.TimeoutExpired) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
