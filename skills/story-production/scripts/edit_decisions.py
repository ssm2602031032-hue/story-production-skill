#!/usr/bin/env python3
"""Versioned cut decisions with independent picture/audio ranges. No automatic creative decisions."""
from pathlib import Path
import argparse,copy,hashlib,json,math,os,sys,wave
from creative_tools import read,safe_write
from delivery_utils import digest,fresh,finite,index
from story_pipeline import contained
from media_qc import inspect_video
from video_prompt_tools import validate_plan
FPS={24,25,30,48,50,60}
def integer(v,label,minimum=0):
 if not isinstance(v,int) or isinstance(v,bool) or v<minimum:raise ValueError(label+' must be an integer >= '+str(minimum))
 return v
def known(row,allowed,label):
 if not isinstance(row,dict):raise ValueError(label+' must be an object')
 extra=set(row)-set(allowed)
 if extra:raise ValueError(label+' contains unsupported fields: '+', '.join(sorted(extra)))
def validate(path,check_media=True):
 path=Path(path);d=read(path);known(d,['version','title','fps','width','height','sources','picture','audio','embedded_audio_policy','color_intent'],'edit')
 fps=integer(d.get('fps'),'fps',1)
 if fps not in FPS:raise ValueError('Supported edit rates: 24,25,30,48,50,60; conform fractional/VFR sources separately')
 for k in ('width','height'):
  value=integer(d.get(k),k,2)
  if value%2 or value>7680:raise ValueError(k+' must be even and <=7680')
 if not isinstance(d.get('title'),str) or not d['title'].strip() or '\n' in d['title'] or '\r' in d['title']:raise ValueError('A single-line title is required')
 if d.get('embedded_audio_policy')!='ignore':raise ValueError('Declare embedded_audio_policy=ignore; source-clip audio is never implicitly mixed. Provide separate WAV audio cues.')
 if d.get('color_intent')!='sdr-review':raise ValueError('This cut renderer currently supports explicit sdr-review intent only')
 sources=d.get('sources')
 if not isinstance(sources,dict) or not sources:raise ValueError('sources must map IDs to files')
 if not isinstance(d.get('picture'),list) or not d['picture']:raise ValueError('picture must contain cut clips')
 if not isinstance(d.get('audio'),list):raise ValueError('Declare audio cues, or an explicit empty list for a silent preview')
 if len(d['picture'])+len(d['audio'])>64:raise ValueError('Render at most 64 picture/audio segments per review sequence; split long work into named sequences')
 index(d['picture']+d['audio'],'clip/cue');warnings=[];resolved={};metadata={}
 if any('\n' in r['id'] or '\r' in r['id'] for r in d['picture']+d['audio']):raise ValueError('Clip/cue IDs must be single-line')
 for sid,source in sources.items():
  if not isinstance(sid,str) or not sid:raise ValueError('Source IDs must be nonempty strings')
  known(source,['path','kind','sha256'],'source '+sid)
  if source.get('kind') not in ('video','audio'):raise ValueError(sid+': kind must be video/audio')
  file=contained(path.resolve().parent,source.get('path'));resolved[sid]=file
  if not isinstance(source.get('sha256'),str) or len(source['sha256'])!=64:raise ValueError(sid+': capture a real source SHA256 first')
  if check_media:
   if not file.is_file() or digest(file)!=source['sha256']:raise ValueError(sid+': missing or changed media')
   if source['kind']=='video':
    info=inspect_video(file,max_frames=0,expected_fps=fps)
    if not info['valid']:raise ValueError(sid+': '+'; '.join(info['errors']))
    if (info['sample']['timestamp_delta_spread_sec'] or 0)>max(.002,.1/fps):raise ValueError(sid+': variable timestamps require an explicit conform')
    import av
    with av.open(str(file)) as c:
     cc=c.streams.video[0].codec_context;trc=int(getattr(cc,'color_trc',2));prim=int(getattr(cc,'color_primaries',2))
     if cc.sample_aspect_ratio and cc.sample_aspect_ratio!=1:raise ValueError(sid+': non-square pixels require an explicit display-aspect conform')
    if trc in (16,18) or prim==9:raise ValueError(sid+': HDR/wide-gamut input needs an explicit color-managed transform before SDR review rendering')
    if trc==2 or prim==2:warnings.append(sid+': color tags unspecified; output is not a color-certified master')
    if info['audio']:warnings.append(sid+': embedded audio explicitly ignored; only declared WAV cues will be heard')
    metadata[sid]={'frames':info['sample']['decoded_frames'],'video':info['video']}
   else:
    with wave.open(str(file),'rb') as f:
     if f.getcomptype()!='NONE' or f.getsampwidth()!=2 or f.getnchannels() not in (1,2) or f.getframerate()!=48000:raise ValueError(sid+': audio must be PCM16 mono/stereo WAV at 48000 Hz')
     count=f.getnframes();raw=f.readframes(count)
     if len(raw)!=count*f.getnchannels()*2:raise ValueError(sid+': truncated WAV data')
     metadata[sid]={'samples':count,'channels':f.getnchannels(),'sample_rate':48000}
 total=0;picture=[]
 for row in d['picture']:
  known(row,['id','source','in_frame','out_frame','reason','story_ref'],'picture clip')
  sid=row.get('source')
  if sid not in sources or sources[sid]['kind']!='video':raise ValueError(row['id']+': expected a video source')
  a=integer(row.get('in_frame'),'in_frame');b=integer(row.get('out_frame'),'out_frame',1)
  if b<=a or (check_media and b>metadata[sid]['frames']):raise ValueError(row['id']+': invalid/excess source range')
  picture.append({**row,'timeline_in_frame':total,'timeline_out_frame':total+b-a});total+=b-a
 audio=[]
 for row in d['audio']:
  known(row,['id','source','in_frame','out_frame','timeline_in_frame','gain_db','fade_in_frames','fade_out_frames','reason'],'audio cue')
  sid=row.get('source')
  if sid not in sources or sources[sid]['kind']!='audio':raise ValueError(row['id']+': expected a WAV source')
  a=integer(row.get('in_frame'),'in_frame');b=integer(row.get('out_frame'),'out_frame',1);start=integer(row.get('timeline_in_frame'),'timeline_in_frame');length=b-a
  if length<=0 or start+length>total or (check_media and b*(48000//fps)>metadata[sid]['samples']):raise ValueError(row['id']+': invalid source/timeline audio range')
  gain=finite(row.get('gain_db',0),'gain_db')
  if not -120<=gain<=24:raise ValueError('Supported cue gain is -120..24 dB')
  fin=integer(row.get('fade_in_frames',0),'fade_in_frames');fout=integer(row.get('fade_out_frames',0),'fade_out_frames')
  if fin+fout>length:raise ValueError(row['id']+': audio fades exceed cue length')
  audio.append({**row,'gain_db':gain,'fade_in_frames':fin,'fade_out_frames':fout,'timeline_out_frame':start+length})
 if not audio:warnings.append('This edit has no audio cues and will produce a silent preview')
 return {'version':'1.5.0','fps':fps,'total_frames':total,'duration_sec':total/fps,'picture':picture,'audio':audio,'metadata':metadata,'warnings':warnings,'source_sha256':digest(path),'media_checked':check_media,'limits':'Straight picture cuts and independently placed WAV cues; no speed effects, picture transitions, titles, subtitles, color grade or HDR mastering are silently applied.'}
def capture(path,output):
 d=copy.deepcopy(read(path));root=Path(path).resolve().parent;target=Path(output).resolve().parent
 for source in d.get('sources',{}).values():
  p=contained(root,source['path']);rel=os.path.relpath(p,target).replace(os.sep,'/')
  if rel.startswith('../'):raise ValueError('Place the captured decision file above its media in the project tree')
  source['path']=rel;source['sha256']=digest(p)
 d['version']='1.5.0';safe_write(output,d)
 return {'output':str(output),'captured_sources':len(d.get('sources',{})),'status':'fingerprints-captured; run validate before rendering; no creative approval implied'}
def from_shots(plan_path,map_path,output,width=1280,height=720,scenes=None):
 plan=read(plan_path);fps,_=validate_plan(plan);mapping=read(map_path);out=fresh(output,'.json');root=Path(map_path).resolve().parent;dest=out.resolve().parent
 available={s['scene'] for s in plan['shots']}
 if scenes and not set(scenes)<=available:raise ValueError('Requested scene is absent from the shot plan')
 selected=[s for s in plan['shots'] if not scenes or s['scene'] in scenes]
 if len(selected)>64:raise ValueError('Select one review sequence with --scenes; at most 64 picture/audio segments per review render')
 d={'version':'1.5.0','title':plan['meta']['title'],'fps':fps,'width':width,'height':height,'color_intent':'sdr-review','embedded_audio_policy':'ignore','sources':{},'picture':[],'audio':[]};by_path={}
 for shot in selected:
  entry=mapping.get(shot['id'])
  if not isinstance(entry,dict):raise ValueError(shot['id']+': missing selected media entry')
  path=contained(root,entry.get('path'));rel=os.path.relpath(path,dest).replace(os.sep,'/')
  if rel.startswith('../'):raise ValueError('Place edit output in a project ancestor of all media')
  if path not in by_path:
   sid='V'+str(len(by_path)+1);by_path[path]=sid;d['sources'][sid]={'path':rel,'kind':'video','sha256':digest(path)}
  start=integer(entry.get('source_in_frame',0),'source_in_frame');length=shot['end_frame_exclusive']-shot['first_frame']
  d['picture'].append({'id':shot['id'],'source':by_path[path],'in_frame':start,'out_frame':start+length,'story_ref':'scene '+str(shot['scene']),'reason':'Imported selected shot-plan range; review pacing and add audio cues before mixing'})
 safe_write(out,d)
 return {'output':str(out),'picture_clips':len(selected),'audio_cues':0,'status':'imported-picture-decisions; validate actual media and explicitly author WAV cues before rendering'}
def difference(before,after):
 a=validate(before,False);b=validate(after,False);changes=[]
 for kind in ('picture','audio'):
  left={x['id']:x for x in a[kind]};right={x['id']:x for x in b[kind]}
  for cid in sorted(set(left)|set(right)):
   if left.get(cid)!=right.get(cid):changes.append({'kind':kind,'id':cid,'before':left.get(cid),'after':right.get(cid)})
 da,db=read(before),read(after)
 return {'before_sha256':digest(before),'after_sha256':digest(after),'before_frames':a['total_frames'],'after_frames':b['total_frames'],'before_fps':a['fps'],'after_fps':b['fps'],'changes':changes,'source_changes':[sid for sid in sorted(set(da['sources'])|set(db['sources'])) if da['sources'].get(sid)!=db['sources'].get(sid)],'canvas_changed':(da['width'],da['height'])!=(db['width'],db['height']),'recheck':['retime affected subtitles','inspect sound bridges and cut edges','rebuild review render from current decisions'],'media_checked':False}
def timeline(path,output,picture_only=False):
 try:import opentimelineio as otio
 except ImportError as e:raise ValueError('OpenTimelineIO is unavailable') from e
 d=read(path);r=validate(path);fps=r['fps'];out=fresh(output);suffix=out.suffix.lower()
 if suffix not in ('.otio','.edl'):raise ValueError('Use .otio or .edl')
 if suffix=='.edl' and r['audio'] and not picture_only:raise ValueError('This EDL adapter path exports picture only; use explicit --picture-only or .otio for A/V')
 if suffix=='.edl' and fps not in (24,25,30):raise ValueError('This EDL exporter supports 24/25/30 non-drop-frame only')
 rt=lambda n:otio.opentime.RationalTime(n,fps)
 tr=lambda start,length:otio.opentime.TimeRange(rt(start),rt(length))
 tl=otio.schema.Timeline(name=d['title']);tl.global_start_time=rt(0);v=otio.schema.Track(name='Picture',kind=otio.schema.TrackKind.Video);tl.tracks.append(v)
 reels={sid:hashlib.sha256(sid.encode('utf-8')).hexdigest()[:8].upper() for sid in d['sources']}
 if len(set(reels.values()))!=len(reels):raise ValueError('Reel identifier collision; choose distinct source IDs')
 def clip(row):
  sid=row['source'];p=contained(Path(path).resolve().parent,d['sources'][sid]['path']);length=row['out_frame']-row['in_frame'];available=r['metadata'][sid].get('frames',r['metadata'][sid].get('samples',0)/(48000/fps))
  ref=otio.schema.ExternalReference(target_url=os.path.relpath(p,out.resolve().parent).replace(os.sep,'/'),available_range=tr(0,available));c=otio.schema.Clip(name=row['id'],media_reference=ref,source_range=tr(row['in_frame'],length));c.metadata['story_production']={'source_id':sid,'source_sha256':d['sources'][sid]['sha256'],'gain_db':row.get('gain_db',0),'fade_in_frames':row.get('fade_in_frames',0),'fade_out_frames':row.get('fade_out_frames',0),'mix_status':'gain/fades are metadata only; recreate in the target NLE'};c.metadata['cmx_3600']={'reel':reels[sid]};return c
 for row in r['picture']:v.append(clip(row))
 if suffix=='.otio' and not picture_only:
  for row in r['audio']:
   track=otio.schema.Track(name=row['id'],kind=otio.schema.TrackKind.Audio)
   if row['timeline_in_frame']:track.append(otio.schema.Gap(source_range=tr(0,row['timeline_in_frame'])))
   track.append(clip(row));tl.tracks.append(track)
 tl.metadata['story_production']={'source_decisions_sha256':digest(path),'rendered_video':False,'mix_automation_applied':False}
 if suffix=='.edl':
  try:otio.adapters.write_to_file(tl,str(out),adapter_name='cmx_3600',rate=fps,style='avid')
  except otio.exceptions.NotSupportedError as e:raise ValueError('Install the optional otio-cmx3600-adapter package') from e
  reread=otio.adapters.read_from_file(str(out),adapter_name='cmx_3600',rate=fps)
  decoded=list(reread.tracks[0])
  if len(decoded)!=len(r['picture']):raise ValueError('EDL round-trip clip count differs')
  for actual,expected in zip(decoded,r['picture']):
   if actual.metadata.get('cmx_3600',{}).get('reel','').strip()!=reels[expected['source']]:raise ValueError('EDL round-trip lost source reel identity')
   if abs(actual.source_range.start_time.rescaled_to(fps).value-expected['in_frame'])>.001 or abs(actual.source_range.duration.rescaled_to(fps).value-(expected['out_frame']-expected['in_frame']))>.001:raise ValueError('EDL round-trip changed source range')
 else:otio.adapters.write_to_file(tl,str(out));reread=otio.adapters.read_from_file(str(out))
 if abs(reread.duration().rescaled_to(fps).value-r['total_frames'])>.001:raise ValueError('Timeline round-trip duration differs')
 return {'output':str(out),'frames':r['total_frames'],'picture_clips':len(v),'audio_tracks':0 if suffix=='.edl' or picture_only else len(r['audio']),'reels':reels,'edl_style':'avid' if suffix=='.edl' else None,'source_timecode_basis':'zero-based decoded file frames, not camera-embedded timecode','native_editor_import_tested':False,'mix_automation_applied':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 for name in ('validate','capture','otio','edl'):
  c=sub.add_parser(name);c.add_argument('input',type=Path);c.add_argument('--out',type=Path,required=True)
  if name in ('otio','edl'):c.add_argument('--picture-only',action='store_true')
 c=sub.add_parser('diff');c.add_argument('before',type=Path);c.add_argument('after',type=Path);c.add_argument('--out',type=Path,required=True)
 c=sub.add_parser('from-shots');c.add_argument('input',type=Path);c.add_argument('--media-map',type=Path,required=True);c.add_argument('--out',type=Path,required=True);c.add_argument('--width',type=int,default=1280);c.add_argument('--height',type=int,default=720);c.add_argument('--scenes',type=int,nargs='+')
 a=p.parse_args()
 try:
  if a.command=='from-shots':r=from_shots(a.input,a.media_map,a.out,a.width,a.height,a.scenes)
  elif a.command=='capture':r=capture(a.input,a.out)
  elif a.command in ('otio','edl'):r=timeline(a.input,a.out,a.picture_only)
  else:r=validate(a.input) if a.command=='validate' else difference(a.before,a.after);safe_write(a.out,r)
  print(json.dumps(r,ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError,wave.Error) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
