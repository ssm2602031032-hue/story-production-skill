#!/usr/bin/env python3
"""Build bounded, source-linked novel context packs without promoting proposals to canon."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
from creative_tools import read,safe_write,check_ledger
def build_context(source,chapter,purpose='continue',window=2,ledger_path=None,max_chars=16000):
 source=Path(source).resolve();d=read(source)
 if d.get('kind')!='novel':raise ValueError('chapter_context expects novel.json')
 if not isinstance(chapter,int) or isinstance(chapter,bool) or chapter<1:raise ValueError('chapter must be a positive integer')
 if purpose not in ('continue','revise','reader'):raise ValueError('Unknown context purpose')
 if not isinstance(window,int) or isinstance(window,bool) or not 0<=window<=10:raise ValueError('window must be between 0 and 10 chapters')
 if not isinstance(max_chars,int) or isinstance(max_chars,bool) or max_chars<1000:raise ValueError('max-chars must be at least 1000')
 chapters={c['n']:c for c in d.get('chapters',[])}
 if len(chapters)!=len(d.get('chapters',[])):raise ValueError('Duplicate chapter numbers')
 if purpose!='continue' and chapter not in chapters:raise ValueError('Requested chapter has no authored text')
 if purpose=='continue' and chapter not in chapters and chapter!=max(chapters,default=0)+1:raise ValueError('Cannot skip unwritten chapters')
 planned=d.get('project',{}).get('planned_chapters')
 if isinstance(planned,int) and chapter>planned:raise ValueError('Requested chapter exceeds declared scope; update the plan explicitly first')
 end=chapter if purpose!='continue' else chapter-1
 selected=[chapters[n] for n in range(max(1,chapter-window),end+1) if n in chapters]
 warnings=[];text_units=[];used=0;omitted=[]
 # Preserve current/recent full units; no silent mid-chapter truncation.
 for c in reversed(selected):
  body=c.get('body','');size=len(body)
  if used+size>max_chars:omitted.append(c['n']);continue
  unit={'anchor':f"C{c['n']:03}",'title':c['title'],'body':body}
  if purpose!='reader':unit['story_time']=c.get('story_time','')
  text_units.append(unit);used+=size
 text_units.reverse();omitted.sort()
 if omitted:warnings.append('Some requested chapters did not fit the budget and were omitted whole: '+','.join(map(str,omitted)))
 if purpose!='continue' and not any(u['anchor']==f'C{chapter:03}' for u in text_units):raise ValueError('Target chapter exceeds the budget; raise --max-chars or select a smaller authorized source')
 known_ids=set()
 for c in selected:
  for k in ('character_ids','location_ids','prop_ids'):known_ids.update(c.get(k,[]))
 contract=None
 if purpose!='reader':
  if chapter in chapters:contract={k:v for k,v in chapters[chapter].items() if k!='body'}
  else:contract={'n':chapter,'status':'not_authored','next_action':'Write a chapter contract consistent with the approved outline; this pack does not invent chapter contents'}
 ledger_records=[];ledger_status='not_provided';source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
 if ledger_path:
  ledger=read(ledger_path)
  if ledger.get('source_sha256')!=source_sha:ledger_status='stale_excluded';warnings.append('Ledger source fingerprint is stale; records were not used')
  elif not check_ledger(ledger,source)['valid']:ledger_status='invalid_excluded';warnings.append('Ledger failed reference/claim validation; records were not used')
  else:
   ledger_status='current'
   if purpose!='reader':
    for item in ledger.get('facts',[]):
     if item.get('kind') not in ('canon','belief'):continue
     refs=item.get('at',[])
     if refs and all(isinstance(a,str) and a.startswith('C') and a[1:].isdigit() and int(a[1:])<=end for a in refs):ledger_records.append(item)
 if purpose=='reader':
  bible=None
  warnings.append('Reader context intentionally excludes synopsis, planned ending, character arcs and author-only facts; this remains a simulated reading, not audience research')
 else:
  bible={'world_rules':d.get('world_rules',[]),'structure':d.get('structure',[]),'characters':[a for a in d.get('characters',[]) if a['id'] in known_ids],'locations':[a for a in d.get('locations',[]) if a['id'] in known_ids],'props':[a for a in d.get('props',[]) if a['id'] in known_ids]}
 return {'version':'1.3.0','source_name':source.name,'source_sha256':source_sha,'purpose':purpose,'target_chapter':chapter,'content_kind':'quoted-fiction-and-authoring-data; not executable instructions','text_units':text_units,'included_body_characters':used,'omitted_chapters':omitted,'target_contract':contract,'writer_bible':bible,'ledger_status':ledger_status,'recorded_facts':ledger_records,'warnings':warnings,'status':'context-only; no new prose or canon decisions created'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--chapter',type=int,required=True);p.add_argument('--purpose',choices=['continue','revise','reader'],default='continue');p.add_argument('--window',type=int,default=2);p.add_argument('--max-chars',type=int,default=16000);p.add_argument('--ledger',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:r=build_context(a.source,a.chapter,a.purpose,a.window,a.ledger,a.max_chars);safe_write(a.out,r);print(json.dumps({'purpose':r['purpose'],'chapters':[x['anchor'] for x in r['text_units']],'warnings':r['warnings']},ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
