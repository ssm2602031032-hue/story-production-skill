#!/usr/bin/env python3
"""Trace authored source beats through visual jobs, dialogue timing, and scene-specific edit decisions. Does not write missing drama or certify artistic quality."""
from pathlib import Path
import argparse,csv,io,json,re,shutil,sys
from creative_tools import read,safe_write,source_index
from delivery_utils import digest,fresh,finite,index
from visual_contracts import compile_contract,text,fields
from story_pipeline import safe_csv
SKILL=Path(__file__).resolve().parents[1]
FUNCTIONS={'establish','action','reaction','reveal','contrast','transition','hold','detail'}
CUTS={'hard_cut','action_match','eyeline','reaction','sound_bridge','contrast','ellipsis','deliberate_jump','continuous'}
def leaf_anchors(source):
 anchors,_,fp=source_index(source);kind=read(source).get('kind')
 keys=[key for key in anchors if re.fullmatch(r'C\d+',key)] if kind=='novel' else [key for key in anchors if re.fullmatch(r'(?:E\d+/)?S\d+_\d+',key)]
 if not keys:raise ValueError('Use authored novel.json, film.json or series.json with indexed text')
 return {key:anchors[key] for key in keys},fp
def policies():return read(SKILL/'assets/scene-edit-policies.json')['policies']
def scaffold(source,visual,out,scope=None):
 anchors,fp=leaf_anchors(source);v=compile_contract(visual);selection=scope or list(anchors)
 if not selection or len(set(selection))!=len(selection) or any(x not in anchors for x in selection):raise ValueError('Scope must contain known unique source anchors')
 data={'version':'1.7.0','title':v['title'],'source_fingerprint':fp,'visual_sha256':digest(visual),'scope_mode':'selected' if scope else 'full','scope':selection,'anchor_omissions':[], 'scenes':[],'beats':[],'shot_links':[],'boundaries':[],'dialogue':[],'reveal_order':[],'status':'scaffold-only; author scene logic, mappings and editorial decisions'}
 safe_write(out,data);return {'output':str(out),'source_units':len(selection),'visual_jobs':[j['id'] for j in v['jobs']],'status':'not_authored','source_examples':[{'anchor':key,'excerpt':anchors[key][:180]} for key in selection[:3]]}
def strings(value,label,allow_empty=False):
 if not isinstance(value,list) or (not allow_empty and not value) or any(not isinstance(x,str) or not x for x in value) or len(set(value))!=len(value):raise ValueError(label+' must be a list of unique nonempty strings')
 return value
def validate(source,visual,bridge):
 anchors,fp=leaf_anchors(source);v=compile_contract(visual);d=read(bridge);errors=[];warnings=[];review=[]
 fields(d,('version','title','source_fingerprint','visual_sha256','scope_mode','scope','anchor_omissions','scenes','beats','shot_links','boundaries','dialogue','reveal_order','status'),'bridge')
 if d.get('source_fingerprint')!=fp:errors.append('Source fingerprint changed, including episode dependencies; reread affected source before updating the mapping')
 if d.get('visual_sha256')!=digest(visual):errors.append('Visual contract changed; review shot mappings and timing before rebasing')
 scope=strings(d.get('scope'),'scope')
 if d.get('scope_mode') not in ('full','selected'):errors.append('scope_mode must be full/selected')
 if any(a not in anchors for a in scope):errors.append('Unknown source anchor in scope')
 if d.get('scope_mode')=='full' and set(scope)!=set(anchors):errors.append('Full scope omits authored source units')
 visual_source=read(visual);visible_bindings={s['id']:{s['asset'],*[a['asset'] for a in s.get('supporting_assets',[])]} for s in visual_source['shots']};visual_assets={a['id']:a for a in visual_source['assets']}
 jobs={j['id']:j for j in v['jobs']};order={jid:i for i,jid in enumerate(jobs)};beats=index(d.get('beats',[]),'beats');scenes=index(d.get('scenes',[]),'scenes');links=index(d.get('shot_links',[]),'shot_links');dialogue=index(d.get('dialogue',[]),'dialogue');covered=set();omitted=set();contexts=policies()
 if not beats or not scenes:errors.append('Author at least one source beat and scene; a scaffold is not a screenplay conversion')
 for sid,scene in scenes.items():
  fields(scene,('id','context','situation','question','change','viewpoint','editing_intent'),sid)
  if scene.get('context') not in contexts:errors.append(sid+': unknown scene context')
  for field in ('situation','question','change','viewpoint','editing_intent'):text(scene.get(field),sid+'.'+field)
 for bid,b in beats.items():
  fields(b,('id','anchor','quote','goal','obstacle','action','outcome','treatment','adaptation_note','targets','depends_on','dependency_repair'),bid)
  anchor=b.get('anchor');quote=text(b.get('quote'),bid+'.quote')
  if anchor not in scope or anchor not in anchors:errors.append(bid+': anchor outside the declared source scope')
  elif quote not in anchors[anchor]:errors.append(bid+': quotation is not present verbatim at its source anchor')
  else:covered.add(anchor)
  for field in ('goal','obstacle','action','outcome'):text(b.get(field),bid+'.'+field)
  treatment=b.get('treatment')
  if treatment not in ('preserve','externalize','merge','move','omit'):errors.append(bid+': unknown adaptation treatment')
  targets=strings(b.get('targets',[]),bid+'.targets',True);dependencies=strings(b.get('depends_on',[]),bid+'.depends_on',True)
  if any(t not in jobs for t in targets):errors.append(bid+': target generation job is missing')
  if treatment=='omit' and targets:errors.append(bid+': omitted beat cannot claim visual coverage')
  if treatment!='omit' and not targets:errors.append(bid+': retained beat has no target shot')
  if treatment!='preserve' and not b.get('adaptation_note'):errors.append(bid+': explain the adaptation change or loss')
  for parent in dependencies:
   if parent not in beats:errors.append(bid+': unknown prerequisite '+parent)
   elif beats[parent].get('treatment')=='omit' and treatment!='omit':
    if not b.get('dependency_repair'):errors.append(bid+': relies on omitted prerequisite '+parent)
    else:review.append(bid+': manually verify replacement of omitted prerequisite '+parent)
 for item in d.get('anchor_omissions',[]):
  fields(item,('anchor','reason'),'anchor omission');anchor=item.get('anchor');text(item.get('reason'),'omission reason')
  if anchor not in scope or anchor in omitted:errors.append('Unknown/duplicate source omission '+str(anchor))
  omitted.add(anchor)
 if covered & omitted:errors.append('A source unit is both mapped and omitted')
 if set(scope)-covered-omitted:errors.append('Source units without mapping or explicit omission: '+', '.join(sorted(set(scope)-covered-omitted)))
 # Dependencies express causal prerequisites, not necessarily screen order.
 done=set();remaining=set(beats)
 while remaining:
  ready={bid for bid in remaining if set(beats[bid].get('depends_on',[]))<=done}
  if not ready:errors.append('Beat dependency cycle or unresolved prerequisite: '+', '.join(sorted(remaining)));break
  done|=ready;remaining-=ready
 if set(links)!=set(jobs):errors.append('shot_links must cover every visual job exactly; no missing or extra shot cards')
 for jid,link in links.items():
  fields(link,('id','scene','function','purpose','audience_before','audience_after','cut_trigger','fallback','protected_windows'),jid)
  if jid not in jobs:continue
  if link.get('scene') not in scenes:errors.append(jid+': unknown scene')
  if link.get('function') not in FUNCTIONS:errors.append(jid+': unknown shot function')
  for field in ('purpose','audience_before','audience_after','cut_trigger','fallback'):text(link.get(field),jid+'.'+field)
  related=[bid for bid,b in beats.items() if jid in b.get('targets',[])]
  if not related:review.append(jid+': no direct source beat; verify the authored reaction/bridge adds needed information')
  windows=index(link.get('protected_windows',[]),jid+'.protected_windows')
  for wid,w in windows.items():
   fields(w,('id','in_sec','out_sec','reason'),wid);start=finite(w.get('in_sec'),wid+'.in_sec',0);end=finite(w.get('out_sec'),wid+'.out_sec',0);text(w.get('reason'),wid+'.reason')
   if end<=start or end>jobs[jid]['duration_sec']+1e-6:errors.append(jid+': protected interval outside allocated shot')
 used_scenes={link.get('scene') for link in links.values()}
 if set(scenes)-used_scenes:errors.append('Scene records without visual shots')
 expected=list(zip(jobs,list(jobs)[1:]));actual=[]
 for n,boundary in enumerate(d.get('boundaries',[])):
  fields(boundary,('from','to','kind','handoff','receive','reason','audio_bridge','axis_note'),'boundary');pair=(boundary.get('from'),boundary.get('to'));actual.append(pair)
  if pair not in expected:errors.append('Boundary does not connect adjacent jobs: '+str(pair))
  if boundary.get('kind') not in CUTS:errors.append('Unsupported editorial boundary type')
  for field in ('handoff','receive','reason','audio_bridge'):text(boundary.get(field),'boundary.'+field)
 if len(actual)!=len(set(actual)) or set(actual)!=set(expected):errors.append('Every adjacent shot pair needs exactly one authored handoff')
 for rid,row in dialogue.items():
  fields(row,('id','anchor','quote','spoken_text','change_reason','speaker','speaker_asset','shot','delivery','onset_sec','duration_sec','timing_basis','timing_evidence'),rid)
  anchor=row.get('anchor');quote=text(row.get('quote'),rid+'.quote');spoken=text(row.get('spoken_text'),rid+'.spoken_text');jid=row.get('shot')
  if anchor not in scope or quote not in anchors.get(anchor,''):errors.append(rid+': dialogue source quote does not match the selected source')
  if spoken!=quote and not row.get('change_reason'):errors.append(rid+': changed dialogue needs an explicit adaptation reason')
  text(row.get('speaker'),rid+'.speaker')
  if jid not in jobs:errors.append(rid+': unknown shot');continue
  if row.get('delivery') not in ('visible','offscreen','voiceover'):errors.append(rid+': specify visible/offscreen/voiceover delivery')
  if row.get('delivery')=='visible':
   if row.get('speaker_asset') not in visible_bindings[jid]:errors.append(rid+': visible speaker must bind to a visible asset in the shot')
   elif visual_assets[row['speaker_asset']].get('category') not in ('person','character','animal'):review.append(rid+': visible speaker is an unusual object; verify intentional character design')
  start=finite(row.get('onset_sec'),rid+'.onset_sec',0);length=finite(row.get('duration_sec'),rid+'.duration_sec',.001)
  if start+length>jobs[jid]['duration_sec']+1e-6:errors.append(rid+': dialogue interval exceeds shot; do not speed it up silently')
  if row.get('timing_basis') not in ('estimate','readthrough','recorded'):errors.append(rid+': unknown timing basis')
  if row.get('timing_basis') in ('readthrough','recorded') and not row.get('timing_evidence'):errors.append(rid+': timed delivery needs an evidence note; not automatic audio verification')
  cjk=len(re.findall(r'[\u4e00-\u9fff]',spoken));words=len(re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*",spoken))
  if cjk/length>6 or words/length>3:review.append(rid+': dense dialogue relative to allocated time; read it aloud before shortening action/reaction')
  if row.get('timing_basis')=='estimate':warnings.append(rid+': duration is estimated, not recorded or lip-synced')
 for row in d.get('reveal_order',[]):
  fields(row,('before','after','reason'),'reveal_order');text(row.get('reason'),'reveal reason');left,right=row.get('before'),row.get('after')
  if left not in beats or right not in beats:errors.append('Reveal order references unknown beat');continue
  a=[order[x] for x in beats[left].get('targets',[]) if x in order];b=[order[x] for x in beats[right].get('targets',[]) if x in order]
  if not a or not b:errors.append('Reveal order needs retained target shots')
  elif max(a)>=min(b):errors.append('Reveal order conflicts or is ambiguous within one shot; map the declared revelation to separate ordered jobs')
 return {'version':'1.7.0','valid':not errors,'errors':errors,'warnings':warnings,'human_review':review,'source_fingerprint':fp,'visual_sha256':digest(visual),'bridge_sha256':digest(bridge),'coverage':{'scope_mode':d.get('scope_mode'),'source_units':len(scope),'mapped_units':len(covered),'explicitly_omitted_units':len(omitted),'beats':len(beats),'visual_jobs':len(jobs),'dialogue_lines':len(dialogue)},'limits':'Checks declared mappings, exact excerpts, scopes and timing. A quotation covering a chapter does not prove all its content was adapted; scene meaning, performance and editorial quality still need reading/viewing.'}
def build(source,visual,bridge,out):
 report=validate(source,visual,bridge)
 if not report['valid']:raise ValueError('; '.join(report['errors']))
 out=Path(out)
 if out.exists():raise ValueError('Choose a fresh output directory')
 fresh(out/'manifest.json');d=read(bridge);v=compile_contract(visual);jobs={j['id']:j for j in v['jobs']};scenes=index(d['scenes'],'scenes');beats=index(d['beats'],'beats');links=index(d['shot_links'],'links');packages=[];table=[];notes=['# '+d['title'],'原文、作者改编决定、视觉提示词与剪辑说明分别保留。以下是制作设计，未生成影像或核准表演时长。']
 for jid,j in jobs.items():
  link=links[jid];scene=scenes[link['scene']];related=[b for b in d['beats'] if jid in b['targets']];speech=[row for row in d['dialogue'] if row['shot']==jid];policy=policies()[scene['context']]
  speakers=list(dict.fromkeys(row['speaker'] for row in speech if row['delivery']=='visible'));prompt=j['positive_prompt']
  if speakers:prompt+=' 可见发声者：'+'、'.join(speakers)+'；其余可见人物保持对应的倾听反应，精确台词使用独立声音轨并另验口型。'
  elif speech:prompt+=' 这些台词仅来自画外或旁白，镜内人物不为这些声音做说话口型。'
  v['directives'][jid]['positive_prompt']=prompt
  package={'id':jid,'source_beats':[{'id':b['id'],'anchor':b['anchor'],'quote':b['quote'],'treatment':b['treatment'],'adaptation_note':b.get('adaptation_note','')} for b in related],'director_context':scene,'shot_function':link,'visible_prompt':prompt,'visual_conditions':{'mode':j['mode'],'duration_sec':j['duration_sec'],'conditioning':j['conditioning'],'missing_conditions':j['missing_conditions']},'speech_track':speech,'sound_note':j['sound_note'],'editorial_policy':policy,'model_payload_status':'not_submitted; native dialogue syntax and reference parameters need the actual model adapter','rendered':False};packages.append(package)
  table.append([jid,link['scene'],scene['context'],';'.join(b['id'] for b in related),';'.join(b['anchor'] for b in related),link['function'],j['duration_sec'],link['cut_trigger']])
  notes += ['## '+jid+' · '+link['function'],'来源：'+'；'.join(b['anchor']+' / '+b['id']+' / '+b['quote'] for b in related),'场景问题：'+scene['question']+'\n\n本镜作用：'+link['purpose'],'可见提示词：\n\n'+prompt,'对白单独轨道：\n\n'+('\n'.join(row['speaker']+'（'+row['delivery']+'）：'+row['spoken_text'] for row in speech) or '无已映射对白；不自动补台词'),'剪辑触发：'+link['cut_trigger']+'\n\n情境策略：'+policy['priority'],'替代覆盖：'+link['fallback']]
 safe_write(out/'bridge-report.json',report);safe_write(out/'shot-packages.json',{'version':'1.7.0','source_fingerprint':report['source_fingerprint'],'visual_sha256':report['visual_sha256'],'bridge_sha256':report['bridge_sha256'],'shots':packages,'boundaries':d['boundaries'],'media_generated':False})
 for rel,record in v['copy_files'].items():
  target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(record['path'],target)
  if digest(target)!=record['sha256']:raise ValueError('Reference changed during package copy')
 safe_write(out/'reference-map.json',v['reference_map']);safe_write(out/'visual-directives.json',v['directives']);safe_write(out/'dialogue-track.json',{'lines':d['dialogue'],'status':'authored text and timing declarations; no audio generated or verified'})
 buf=io.StringIO();writer=csv.writer(buf);writer.writerow(['job','scene','context','beats','source_anchors','function','planned_seconds','cut_trigger']);writer.writerows([[safe_csv(cell) for cell in row] for row in table]);(out/'source-shot-map.csv').write_bytes(buf.getvalue().encode('utf-8-sig'));(out/'director-and-prompts.md').write_text('\n\n'.join(notes)+'\n',encoding='utf-8')
 files=[{'path':p.relative_to(out).as_posix(),'sha256':digest(p)} for p in sorted(out.rglob('*')) if p.is_file()];safe_write(out/'manifest.json',{'files':files,'source_fingerprint':report['source_fingerprint'],'media_generated':False});return {'output':str(out),'shots':len(packages),'warnings':report['warnings'],'human_review':report['human_review'],'media_generated':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','audit','build']);p.add_argument('source',type=Path);p.add_argument('--visual',type=Path,required=True);p.add_argument('--bridge',type=Path);p.add_argument('--scope',nargs='+');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  if a.command=='init':r=scaffold(a.source,a.visual,a.out,a.scope)
  else:
   if not a.bridge:raise ValueError('audit/build needs --bridge')
   if a.command=='build':r=build(a.source,a.visual,a.bridge,a.out)
   else:r=validate(a.source,a.visual,a.bridge);safe_write(a.out,r)
  print(json.dumps(r,ensure_ascii=False));return 0 if r.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
