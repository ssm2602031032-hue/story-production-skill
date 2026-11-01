#!/usr/bin/env python3
"""Audit declared cut alignment against authored story moments and revelation order. Does not infer meaning from video pixels."""
from pathlib import Path
import argparse,json,sys
from creative_tools import read,safe_write
from delivery_utils import digest,index
from edit_decisions import validate as validate_edit,integer
from script_bridge import validate as validate_bridge,policies
from visual_contracts import fields,text
def audit(source,visual,bridge,edit,alignment):
 base=validate_bridge(source,visual,bridge)
 if not base['valid']:raise ValueError('Repair the story bridge first: '+'; '.join(base['errors']))
 e=validate_edit(edit,False);a=read(alignment);b=read(bridge);v=read(visual);jobs={s['id']:s for s in v['shots']};links={x['id']:x for x in b['shot_links']};scenes={x['id']:x for x in b['scenes']};errors=[];warnings=[];followup=[]
 fields(a,('version','edit_sha256','bridge_sha256','visual_sha256','clips','boundary_decisions'),'alignment')
 for field,path in [('edit_sha256',edit),('bridge_sha256',bridge),('visual_sha256',visual)]:
  if a.get(field)!=digest(path):errors.append(field+': changed input; review alignment rather than only refreshing hashes')
 maps=index(a.get('clips',[]),'aligned clips');cuts={c['id']:c for c in e['picture']}
 if set(maps)!=set(cuts):errors.append('Alignment must cover each actual picture cut exactly')
 kept={jid:[] for jid in jobs};placement={jid:[] for jid in jobs};mapped_order=[];fps=e['fps']
 for cid,c in cuts.items():
  if cid not in maps:continue
  m=maps[cid];fields(m,('id','job','source_zero_frame','evidence'),'aligned cut');jid=m.get('job');text(m.get('evidence'),cid+'.evidence')
  if jid not in jobs:errors.append(cid+': unknown visual job');continue
  zero=integer(m.get('source_zero_frame'),'source_zero_frame');start=(c['in_frame']-zero)/fps;end=(c['out_frame']-zero)/fps
  if start<0 or end>jobs[jid]['duration_sec']+1e-6:errors.append(cid+': retained frames lie outside the declared job clock');continue
  kept[jid].append((start,end));placement[jid].append((c['timeline_in_frame'],c['timeline_out_frame']));mapped_order.append((cid,jid))
  followup.append({'cut':cid,'job':jid,'context':scenes[links[jid]['scene']]['context'],'priority':policies()[scenes[links[jid]['scene']]['context']]['priority'],'authored_cut_trigger':links[jid]['cut_trigger'],'limits':'Check the actual chosen take: the alignment is an editor-supplied declaration, not semantic recognition.'})
 for jid,link in links.items():
  intervals=sorted(kept[jid])
  for window in link.get('protected_windows',[]):
   retained_order=[(max(start,window['in_sec']),min(end,window['out_sec'])) for start,end in kept[jid] if start<window['out_sec'] and end>window['in_sec']]
   if any(right[0]<left[1]-1e-6 for left,right in zip(retained_order,retained_order[1:])):errors.append(jid+'/'+window['id']+': edit repeats or reverses the protected action interval; author an explicit replay/new job instead of claiming unchanged continuity')
   cursor=window['in_sec']
   for start,end in intervals:
    if end<=cursor:continue
    if start>cursor+1e-6:break
    cursor=max(cursor,end)
    if cursor>=window['out_sec']-1e-6:break
   if cursor<window['out_sec']-1e-6:errors.append(jid+'/'+window['id']+': cut removes a protected story interval: '+window['reason'])
   elif len(intervals)>1:warnings.append(jid+': protected coverage is split across multiple cuts; verify order and the complete gesture in the actual edit')
  if not intervals:warnings.append(jid+': shot is absent from this edit; review its story function even if no interval was protected')
 beats={x['id']:x for x in b['beats']}
 for constraint in b['reveal_order']:
  left=[pos for jid in beats[constraint['before']]['targets'] for pos in placement[jid]];right=[pos for jid in beats[constraint['after']]['targets'] for pos in placement[jid]]
  if not left or not right:errors.append('Edit loses a beat participating in reveal order: '+constraint['reason'])
  elif max(p[1] for p in left)>min(p[0] for p in right):errors.append('Edit reverses/overlaps declared reveal order: '+constraint['reason'])
 original={(x['from'],x['to']) for x in b['boundaries']};extra={}
 for decision in a.get('boundary_decisions',[]):
  fields(decision,('from_cut','to_cut','reason','handoff','receive','audio_note'),'new boundary');pair=(decision.get('from_cut'),decision.get('to_cut'))
  if pair in extra:errors.append('Duplicate new boundary decision')
  for field in ('reason','handoff','receive','audio_note'):text(decision.get(field),'new boundary.'+field)
  extra[pair]=decision
 actual_pairs=set()
 for (lc,lj),(rc,rj) in zip(mapped_order,mapped_order[1:]):
  actual_pairs.add((lc,rc))
  if (lj,rj) not in original and (lc,rc) not in extra:errors.append(lc+' → '+rc+': changed adjacency needs a new situation-specific handoff')
 if set(extra)-actual_pairs:errors.append('Boundary decisions reference non-adjacent actual cuts')
 return {'version':'1.7.0','valid':not errors,'errors':errors,'warnings':warnings,'scene_review':followup,'media_checked':False,'actual_performance_timing_verified':False,'limits':'Audits source-linked declarations and frame mapping only. Protected windows are author-selected; the chosen take must be viewed to confirm the same moment occurs at that frame. Gain, sound bridges and subtitle synchronization require separate actual-media checks.'}
def scaffold(bridge,visual,edit,out):
 b=read(bridge);v=read(visual);e=validate_edit(edit,False);jobs={s['id'] for s in v['shots']};clips=[]
 for cut in e['picture']:clips.append({'id':cut['id'],'job':cut['story_ref'] if cut.get('story_ref') in jobs else '', 'source_zero_frame':0,'evidence':''})
 data={'version':'1.7.0','edit_sha256':digest(edit),'bridge_sha256':digest(bridge),'visual_sha256':digest(visual),'clips':clips,'boundary_decisions':[]};safe_write(out,data);return {'output':str(out),'status':'unverified mapping scaffold; inspect selected media to fill job/source_zero_frame/evidence','clips':len(clips)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','audit']);p.add_argument('--source',type=Path);p.add_argument('--visual',type=Path,required=True);p.add_argument('--bridge',type=Path,required=True);p.add_argument('--edit',type=Path,required=True);p.add_argument('--alignment',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  if a.command=='init':r=scaffold(a.bridge,a.visual,a.edit,a.out)
  else:
   if not a.source or not a.alignment:raise ValueError('audit needs --source and --alignment')
   r=audit(a.source,a.visual,a.bridge,a.edit,a.alignment);safe_write(a.out,r)
  print(json.dumps(r,ensure_ascii=False));return 0 if r.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
