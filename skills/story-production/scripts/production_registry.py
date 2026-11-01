#!/usr/bin/env python3
"""Verify declared reference/take versions and estimate generation cost; no API submission or automatic take approval."""
from pathlib import Path
import argparse,json,re,sys
from creative_tools import read,safe_write
from delivery_utils import digest,index,finite
from story_pipeline import contained
from video_prompt_tools import validate_plan
ROLES={'identity','wardrobe','location','prop','depth','pose','mask','camera','first-frame','last-frame'}
def capture_versions(registry_path,plan_path,output):
 import copy,os
 data=copy.deepcopy(read(registry_path));plan=read(plan_path);validate_plan(plan);root=Path(registry_path).resolve().parent;target=Path(output).resolve().parent
 for group in ('references','takes'):
  index(data.get(group,[]),group)
  for row in data.get(group,[]):
   path=contained(root,row.get('path'))
   if not path.is_file():raise ValueError('Missing file: '+row.get('path',''))
   relative=os.path.relpath(path,target).replace(os.sep,'/')
   if relative.startswith('../'):raise ValueError('Capture output must be in a project ancestor of all referenced files')
   row['path']=relative;row['sha256']=digest(path)
   if group=='takes':row['status']='candidate';row.pop('review_note',None)
 data['source_plan_sha256']=digest(plan_path);data['selected']={};data['version']='1.4.0';safe_write(output,data)
 return {'output':str(output),'takes_captured':len(data.get('takes',[])),'selected_takes':0,'limits':'Fresh file fingerprints only. All captured takes are candidates; existing approvals are not carried over.'}
def check_registry(registry_path,plan_path):
 registry=read(registry_path);plan=read(plan_path);validate_plan(plan);root=Path(registry_path).resolve().parent;shots={s['id'] for s in plan['shots']};errors=[];warnings=[];refs=index(registry.get('references',[]),'references');takes=index(registry.get('takes',[]),'takes');selection=registry.get('selected',{})
 if registry.get('source_plan_sha256')!=digest(plan_path):errors.append('Shot plan fingerprint changed; review selections before exporting')
 valid_paths={}
 for rid,row in list(refs.items())+list(takes.items()):
  if rid in refs and rid in takes:errors.append('Reference and take IDs must not collide: '+rid);continue
  try:
   path=contained(root,row.get('path'));expected=row.get('sha256')
   if not path.is_file():raise ValueError('File missing')
   if not isinstance(expected,str) or not re.fullmatch(r'[a-f0-9]{64}',expected):raise ValueError('Recorded SHA256 required; do not invent it')
   if digest(path)!=expected:raise ValueError('File changed since approval/reference capture')
   valid_paths[rid]=row['path']
  except (ValueError,OSError,TypeError) as e:errors.append(rid+': '+str(e))
 for rid,row in refs.items():
  if row.get('role') not in ROLES:errors.append(rid+': unknown reference role')
  if row.get('role') in ('depth','pose','mask','camera') and not row.get('workflow_evidence'):warnings.append(rid+': actual workflow support/coordinate convention has not been recorded')
 for tid,row in takes.items():
  if row.get('shot') not in shots:errors.append(tid+': unknown shot')
  if row.get('status') not in ('candidate','approved','rejected'):errors.append(tid+': unknown take status')
  if not isinstance(row.get('references',[]),list):errors.append(tid+': references must be a list');continue
  for ref in row.get('references',[]):
   if ref not in refs:errors.append(tid+': missing reference ID '+str(ref))
  if row.get('status')=='approved' and not row.get('review_note'):errors.append(tid+': approval requires an actual review note')
 if not isinstance(selection,dict):raise ValueError('selected must map shot IDs to take IDs')
 media_map={};missing=sorted(shots-set(selection))
 for shot,tid in selection.items():
  if shot not in shots or tid not in takes:errors.append(str(shot)+': unknown shot/take selection');continue
  take=takes[tid]
  if take.get('shot')!=shot or take.get('status')!='approved':errors.append(shot+': selection must be an approved take for this shot');continue
  start=take.get('source_in_frame',0)
  if not isinstance(start,int) or isinstance(start,bool) or start<0:errors.append(tid+': source_in_frame must be a nonnegative integer');continue
  if tid in valid_paths:media_map[shot]={'path':valid_paths[tid],'source_in_frame':start}
 return {'valid':not errors,'errors':errors,'warnings':warnings,'unselected_shots':missing,'media_map':media_map,'file_versions_checked':len(valid_paths),'limits':'Checks declared provenance and manual selection only. Does not choose the best take or decode media; editorial_export.py separately validates fps and source ranges.'}
def estimate(data,price,attempts,currency):
 finite(price,'price_per_second',0)
 if not isinstance(attempts,int) or isinstance(attempts,bool) or attempts<1:raise ValueError('attempts must be a positive integer')
 if not isinstance(currency,str) or not re.fullmatch(r'[A-Z]{3}',currency):raise ValueError('Use an explicit three-letter currency code')
 jobs=data.get('video_jobs')
 if not isinstance(jobs,list):raise ValueError('Expected compiled video_jobs; pure post tasks are not generation jobs')
 index(jobs,'video_jobs');seconds=sum(finite(j.get('native_duration_sec'),j['id']+'.native_duration_sec',0) for j in jobs)
 return {'currency':currency,'pricing_basis':'user-supplied per generated native second','price_per_second':price,'jobs':len(jobs),'native_seconds_one_pass':round(seconds,9),'attempts_scenario':attempts,'one_pass_cost':round(seconds*price,4),'scenario_cost':round(seconds*price*attempts,4),'excluded_post_tasks':len(data.get('post_tasks',[])),'submitted_jobs':0,'limits':'Scenario arithmetic, not a vendor quote or guarantee of success. Excludes minimum billing units, images, audio, enhancement, storage, tax and human labor; price must match the actual service billing model.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 c=sub.add_parser('check');c.add_argument('registry',type=Path);c.add_argument('--plan',type=Path,required=True);c.add_argument('--out',type=Path,required=True);c.add_argument('--media-map-out',type=Path)
 c=sub.add_parser('capture');c.add_argument('registry',type=Path);c.add_argument('--plan',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
 c=sub.add_parser('estimate');c.add_argument('jobs',type=Path);c.add_argument('--price-per-second',type=float,required=True);c.add_argument('--attempts',type=int,default=1);c.add_argument('--currency',required=True);c.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 try:
  if a.command=='capture':
   r=capture_versions(a.registry,a.plan,a.out);print(json.dumps(r,ensure_ascii=False));return 0
  if a.command=='check':
   r=check_registry(a.registry,a.plan)
   if a.media_map_out:
    if not r['valid'] or r['unselected_shots']:raise ValueError('Only a fully selected, valid registry can export a media map')
    # Map paths must remain relative to the output map, not the input registry.
    import os
    root=a.registry.resolve().parent;target=a.media_map_out.resolve().parent;mapping={k:{**v,'path':os.path.relpath(root/v['path'],target).replace(os.sep,'/')} for k,v in r['media_map'].items()}
    if any(v['path'].startswith('../') for v in mapping.values()):raise ValueError('Place media-map-out in a project ancestor of the media so downstream path containment is preserved')
    safe_write(a.media_map_out,mapping)
  else:r=estimate(read(a.jobs),a.price_per_second,a.attempts,a.currency)
  safe_write(a.out,r);print(json.dumps(r,ensure_ascii=False));return 0 if r.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
