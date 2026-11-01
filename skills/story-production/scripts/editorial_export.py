#!/usr/bin/env python3
"""Build a real OpenTimelineIO interchange timeline from compiled shots and local conformed media."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
from creative_tools import read
from story_pipeline import contained
from video_prompt_tools import validate_plan
from media_qc import inspect_video
def guard_output(path):
 path=Path(path)
 for part in [path,*path.parents]:
  if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Refusing symlink/junction output')
 if path.exists():raise ValueError('Timeline exists; choose a new versioned filename')
 if path.suffix.lower()!='.otio':raise ValueError('This exporter writes native .otio only; other formats need their actual adapters')
def build_timeline(plan_path,output,media_map_path=None,allow_missing=False):
 try:import opentimelineio as otio
 except ImportError as e:raise ValueError('OpenTimelineIO is unavailable; install requirements-media.txt in the selected environment') from e
 plan_path=Path(plan_path).resolve();output=Path(output);guard_output(output);plan=read(plan_path);fps,total=validate_plan(plan)
 media_map=read(media_map_path) if media_map_path else {};root=Path(media_map_path).resolve().parent if media_map_path else Path.cwd();known={s['id'] for s in plan['shots']}
 if any(key not in known for key in media_map):raise ValueError('Media map includes an unknown shot ID')
 if not allow_missing and set(media_map)!=known:raise ValueError('Some shots have no local media. Use --allow-missing only for a visibly incomplete planning timeline.')
 timeline=otio.schema.Timeline(name=plan['meta']['title']);timeline.global_start_time=otio.opentime.RationalTime(0,fps)
 track=otio.schema.Track(name='Picture');timeline.tracks.append(track);missing=[];verified=[];cache={}
 for s in plan['shots']:
  length=s['end_frame_exclusive']-s['first_frame'];entry=media_map.get(s['id']);media_reference=otio.schema.MissingReference();start=0
  if entry is not None:
   if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):raise ValueError('Each media entry requires path')
   path=contained(root,entry['path'])
   if not path.is_file():raise ValueError('Missing mapped media: '+entry['path'])
   start=entry.get('source_in_frame',0)
   if not isinstance(start,int) or isinstance(start,bool) or start<0:raise ValueError('source_in_frame must be a nonnegative integer')
   if path not in cache:cache[path]=inspect_video(path,max_frames=0,expected_fps=fps)
   info=cache[path]
   if not info['valid']:raise ValueError('Media is not conformed to the edit timeline: '+'; '.join(info['errors']))
   spread=info['sample']['timestamp_delta_spread_sec']
   if spread is not None and spread>max(.002,1/fps*.1):raise ValueError('Variable timestamp spacing requires an explicit conform before timeline assembly')
   available=info['sample']['decoded_frames']
   if start+length>available:raise ValueError(f"{s['id']}: source range exceeds decoded media")
   relative=os.path.relpath(path,output.resolve().parent).replace(os.sep,'/')
   media_reference=otio.schema.ExternalReference(target_url=relative,available_range=otio.opentime.TimeRange(otio.opentime.RationalTime(0,fps),otio.opentime.RationalTime(available,fps)))
   verified.append({'shot':s['id'],'path':entry['path'],'sha256':info['sha256'],'source_in_frame':start,'decoded_frames':available,'fps':fps})
  else:missing.append(s['id'])
  clip=otio.schema.Clip(name=s['id'],media_reference=media_reference,source_range=otio.opentime.TimeRange(otio.opentime.RationalTime(start,fps),otio.opentime.RationalTime(length,fps)))
  clip.metadata['story_production']={'shot_id':s['id'],'scene':s['scene'],'picture':s['picture'],'pure_post':bool(s.get('pure_post')),'media_status':'missing-not-rendered' if entry is None else 'local-file-metadata-and-range-checked','audio_status':'not_assembled'}
  track.append(clip)
 timeline.metadata['story_production']={'version':'1.3.0','source_plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'fps':fps,'story_frames':total,'missing_shots':missing,'verified_media':verified,'status':'planning-missing-media' if missing else 'picture-assembly-only','limits':'No rendering, grading, audio mix, lip-sync or creative approval implied. Media paths are relative to this OTIO file; preserve the project directory structure.'}
 output.parent.mkdir(parents=True,exist_ok=True);otio.adapters.write_to_file(timeline,str(output));reopened=otio.adapters.read_from_file(str(output))
 if abs(reopened.duration().rescaled_to(fps).value-total)>.0001:raise ValueError('Exported timeline duration differs from source')
 return {'output':str(output),'opentimelineio':otio.__version__,'clips':len(track),'story_frames':total,'fps':fps,'missing_shots':missing,'status':timeline.metadata['story_production']['status'],'rendered_video':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--media-map',type=Path);p.add_argument('--allow-missing',action='store_true');a=p.parse_args()
 try:r=build_timeline(a.plan,a.out,a.media_map,a.allow_missing);print(json.dumps(r,ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
