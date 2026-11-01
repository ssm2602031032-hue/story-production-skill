#!/usr/bin/env python3
"""Check author-supplied evidence, event dependencies, knowledge and season promises; no automatic story interpretation."""
from pathlib import Path
import argparse,json,sys,re
from creative_tools import read,safe_write
from delivery_utils import index,finite
def evidence(data):
 sources=index(data.get('sources',[]),'sources');claims=index(data.get('claims',[]),'claims');errors=[];warnings=[];csl=[]
 for sid,s in sources.items():
  if not s.get('title') or not re.match(r'^https?://[^\s]+$',s.get('url','')):errors.append(sid+': title and public source URL required')
  if not s.get('accessed'):errors.append(sid+': record actual access date')
  if not s.get('excerpt'):warnings.append(sid+': no excerpt; quotation matching unavailable')
  item={'id':sid,'type':s.get('type','webpage'),'title':s.get('title',''),'URL':s.get('url','')}
  if s.get('author'):item['author']=[{'literal':s['author']}]
  if s.get('issued'):item['issued']={'literal':s['issued']}
  csl.append(item)
 for cid,c in claims.items():
  if c.get('kind') not in ('fact','inference','fiction'):errors.append(cid+': kind must be fact, inference or fiction')
  if not c.get('statement') or not c.get('used_at'):errors.append(cid+': statement and used_at needed')
  refs=c.get('source_ids',[])
  if not isinstance(refs,list):errors.append(cid+': source_ids must be a list');continue
  if c.get('kind')=='fact' and not refs:errors.append(cid+': factual claim has no source')
  if any(sid not in sources for sid in refs):errors.append(cid+': unknown source')
  if c.get('quote') and not any(c['quote'] in sources[sid].get('excerpt','') for sid in refs if sid in sources):errors.append(cid+': quote not present in supplied excerpts')
  if c.get('kind')=='inference' and not c.get('reason'):warnings.append(cid+': inference reasoning not recorded')
 return {'valid':not errors,'errors':errors,'warnings':warnings,'csl_json':csl,'limits':'Checks supplied records only, not source authenticity or factual truth. No web requests or DOI resolution.'}
def graph(data):
 events=index(data.get('events',[]),'events');facts=index(data.get('facts',[]),'facts');characters=data.get('characters',[])
 if not events:raise ValueError('At least one event is required')
 if not isinstance(characters,list) or any(not isinstance(x,str) or not x for x in characters) or len(set(characters))!=len(characters):raise ValueError('characters must contain unique IDs')
 errors=[];warnings=[];parents={};times={}
 for fid,f in facts.items():
  if not isinstance(f.get('known_by',[]),list) or any(c not in characters for c in f.get('known_by',[])):errors.append(fid+': invalid initial knowledge holder')
 for eid,e in events.items():
  times[eid]=finite(e.get('story_time'),eid+'.story_time')
  req=e.get('requires',[])
  if not isinstance(req,list) or len(set(req))!=len(req):raise ValueError(eid+': requires must be unique event IDs')
  parents[eid]=set(req)
  for dep in req:
   if dep not in events:errors.append(eid+': unknown prerequisite '+str(dep))
  for group in ('uses','reveals'):
   if not isinstance(e.get(group,[]),list):raise ValueError(eid+': '+group+' must be a list')
   for fact in e.get(group,[]):
    if not isinstance(fact,dict) or fact.get('fact') not in facts:errors.append(eid+': unknown fact in '+group);continue
    recipients=fact.get('to',[]) if group=='reveals' else [fact.get('by')]
    if not isinstance(recipients,list) or not recipients or any(c not in characters for c in recipients):errors.append(eid+': invalid knowledge holder in '+group)
 if errors:return {'valid':False,'errors':errors,'warnings':warnings}
 remaining=set(events);order=[];ancestors={}
 while remaining:
  ready=sorted((eid for eid in remaining if parents[eid]<=set(order)),key=lambda x:(times[x],x))
  if not ready:errors.append('Causal cycle among: '+', '.join(sorted(remaining)));break
  for eid in ready:
   ancestors[eid]=set(parents[eid])
   for dep in parents[eid]:ancestors[eid].update(ancestors[dep])
   order.append(eid);remaining.remove(eid)
 if not errors:
  for eid,e in events.items():
   for dep in parents[eid]:
    if times[dep]>times[eid]:errors.append(eid+': prerequisite '+dep+' occurs later in story time')
   for use in e.get('uses',[]):
    fid,who=use['fact'],use['by'];known=who in facts[fid].get('known_by',[])
    learned=[other for other,row in events.items() if other!=eid and (times[other]<times[eid] or other in ancestors[eid]) and any(r['fact']==fid and who in r.get('to',[]) for r in row.get('reveals',[]))]
    if not known and not learned:errors.append(eid+': '+who+' uses '+fid+' before any established disclosure')
  if len(set(times.values()))<len(times):warnings.append('Equal-time disclosures count only through explicit prerequisite paths; within-event learning must be split into ordered events')
 rows=[{'id':eid,'unit':events[eid].get('unit',''),'story_time':times[eid],'requires':sorted(parents[eid])} for eid in order]
 return {'valid':not errors,'errors':errors,'warnings':warnings,'event_order':rows,'limits':'Validates declared event relations, not prose, motives or plausibility. Presentation order can differ from story time.'}
def season(data):
 units=data.get('units',[]);promises=index(data.get('promises',[]),'promises');errors=[];warnings=[];coverage={}
 if not isinstance(units,list) or not units or any(not isinstance(x,str) or not x for x in units) or len(set(units))!=len(units):raise ValueError('units must list unique chapter/episode IDs in presentation order')
 pos={u:i for i,u in enumerate(units)}
 for pid,p in promises.items():
  setup,payoff=p.get('setup'),p.get('payoff');status=p.get('status')
  if setup not in pos:errors.append(pid+': unknown setup unit')
  if status not in ('planned','resolved','open-intentional'):errors.append(pid+': unknown promise status')
  if payoff is not None and payoff not in pos:errors.append(pid+': unknown payoff unit')
  if setup in pos and payoff in pos and pos[payoff]<pos[setup]:errors.append(pid+': payoff precedes setup in declared presentation order; model the retrospective revelation explicitly')
  if status=='resolved' and (payoff not in pos or not p.get('evidence')):errors.append(pid+': resolved promise needs payoff and text evidence')
  if status=='open-intentional' and not p.get('reason'):errors.append(pid+': intentional open ending needs reason')
  if status=='planned':warnings.append(pid+': remains planned')
  coverage[pid]={'setup':setup,'payoff':payoff,'status':status,'units_waited':pos[payoff]-pos[setup] if payoff in pos and setup in pos else None}
 return {'valid':not errors,'errors':errors,'warnings':warnings,'coverage':coverage,'limits':'Checks author-supplied coverage, not whether the dramatic payoff works; evidence strings still need source review.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['evidence','graph','season']);p.add_argument('input',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 try:
  r={'version':'1.4.0',**globals()[a.command](read(a.input))};safe_write(a.out,r);print(json.dumps(r,ensure_ascii=False));return 0 if r['valid'] else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
