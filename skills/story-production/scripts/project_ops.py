#!/usr/bin/env python3
"""Snapshot authoritative story units and report direct revision impacts without editing sources."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from creative_tools import read,safe_write
from story_pipeline import contained
def hash_value(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def snapshot(source):
 source=Path(source).resolve();data=read(source);units={};assets={};usage={};dependencies={}
 def index_film(f,prefix=''):
  for category in ('characters','props','locations'):
   for a in f.get(category,[]):assets.setdefault(a['id'],[]).append(hash_value(a))
  for sc in f.get('scenes',[]):
   scene_ref=prefix+f"S{sc['n']:02}"
   context={k:v for k,v in sc.items() if k not in ('shots','shot_overrides')}
   for j,row in enumerate(sc.get('shots',[]),1):
    anchor=scene_ref+f'_{j:03}';override=sc.get('shot_overrides',{}).get(str(j),{})
    units[anchor]={'hash':hash_value({'row':row,'context':context,'override':override}),'text_hash':hash_value([row[4],row[5]]),'timing_hash':hash_value([row[0],f.get('project',{}).get('fps',24)]),'parent':scene_ref}
    used=set(row[10])|{override.get('location_id',sc['location_id'])}
    for a in f.get('characters',[]):
     if any(a['name'] in d[0] for d in row[5]):used.add(a['id'])
    for aid in used:usage.setdefault(aid,[]).append(anchor)
 if data.get('kind')=='novel':
  for category in ('characters','props','locations'):
   for a in data.get(category,[]):assets.setdefault(a['id'],[]).append(hash_value(a))
  for c in data.get('chapters',[]):
   key=f"C{c['n']:03}";units[key]={'hash':hash_value(c),'text_hash':hash_value(c.get('body','')),'timing_hash':hash_value(c.get('story_time','')),'parent':key}
   for aid in c.get('character_ids',[])+c.get('prop_ids',[])+c.get('location_ids',[]):usage.setdefault(aid,[]).append(key)
 elif data.get('kind')=='series':
  for category in ('characters','props','locations'):
   for a in data.get(category,[]):assets.setdefault(a['id'],[]).append(hash_value(a))
  for ep in data.get('episodes',[]):
   path=contained(source.parent,ep['source']);dependencies[ep['source']]=hashlib.sha256(path.read_bytes()).hexdigest();index_film(read(path),f"E{ep['n']:03}/")
 else:index_film(data)
 return {'version':'1.2.0','source_name':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'dependencies':dependencies,'kind':data.get('kind','film'),'project_hash':hash_value({k:v for k,v in data.items() if k not in ('chapters','scenes','episodes','characters','props','locations')}),'units':units,'assets':{a:hash_value(sorted(set(h))) for a,h in assets.items()},'asset_usage':{a:sorted(set(v)) for a,v in usage.items()},'status':'snapshot-only; no literary or media approval implied'}
def impacts(before,after,ledger=None):
 if before.get('kind')!=after.get('kind'):raise ValueError('Cannot compare different source kinds')
 old,new=before['units'],after['units'];added=sorted(set(new)-set(old));removed=sorted(set(old)-set(new))
 changed=sorted(k for k in old.keys()&new.keys() if old[k]['hash']!=new[k]['hash'])
 text_changed=[k for k in changed if old[k]['text_hash']!=new[k]['text_hash']];timing_changed=[k for k in changed if old[k]['timing_hash']!=new[k]['timing_hash']]
 asset_changed=sorted(k for k in before['assets'].keys()|after['assets'].keys() if before['assets'].get(k)!=after['assets'].get(k))
 affected=set(changed+added+removed)
 timing_reflow=set()
 if after.get('kind')!='novel':
  def group(k):return k.split('/')[0] if '/' in k else 'film'
  triggers=timing_changed+added+removed
  for g in {group(k) for k in triggers}:
   old_order=[k for k in old if group(k)==g];new_order=[k for k in new if group(k)==g]
   offsets=[order.index(k) for order in (old_order,new_order) for k in triggers if k in order]
   if offsets:timing_reflow.update(new_order[min(offsets):])
  affected.update(timing_reflow)
 for aid in asset_changed:affected.update(before.get('asset_usage',{}).get(aid,[]));affected.update(after.get('asset_usage',{}).get(aid,[]))
 records=[]
 if ledger:
  for group,keys in [('facts',['at']),('promises',['setup','resolution']),('issues',['at','fix_at']),('decisions',['affects'])]:
   for item in ledger.get(group,[]):
    refs=[a for key in keys for a in item.get(key,[])]
    if any(unit==anchor or unit.startswith(anchor+'_') or unit.startswith(anchor+'/') for anchor in refs for unit in affected):records.append({'group':group,'id':item.get('id'),'reason':'Referenced unit or reused asset changed; review rather than carrying approval forward'})
 return {'version':'1.2.0','added_units':added,'removed_units':removed,'changed_units':changed,'text_changed':text_changed,'timing_changed':timing_changed,'downstream_timing_units':sorted(timing_reflow),'assets_changed':asset_changed,'units_requiring_review':sorted(affected),'ledger_items_requiring_review':records,'project_metadata_changed':before.get('project_hash')!=after.get('project_hash'),'byte_only_or_unindexed_change':before.get('source_sha256')!=after.get('source_sha256') and not (added or removed or changed or asset_changed or before.get('project_hash')!=after.get('project_hash')),'needs_rebuild':bool(affected or before.get('project_hash')!=after.get('project_hash')),'limits':'Direct structural/reference impact and downstream timing within the affected episode only. Scene renumbering, implied facts and semantic causality still need human/agent review. No source, ledger or media status is changed.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 c=sub.add_parser('snapshot');c.add_argument('--source',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
 c=sub.add_parser('impact');c.add_argument('--before',type=Path,required=True);c.add_argument('--source',type=Path,required=True);c.add_argument('--ledger',type=Path);c.add_argument('--out',type=Path)
 a=p.parse_args()
 try:
  result=snapshot(a.source) if a.command=='snapshot' else impacts(read(a.before),snapshot(a.source),read(a.ledger) if a.ledger else None)
  if a.out:safe_write(a.out,result)
  print(json.dumps(result,ensure_ascii=False,indent=2));return 0
 except (OSError,ValueError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
