#!/usr/bin/env python3
"""Compile authored identity, style and motion decisions into inspectable prompt drafts. No generation or visual certification."""
from pathlib import Path
import argparse,copy,hashlib,json,math,shutil,sys
from creative_tools import read,safe_write
from delivery_utils import digest,finite,fresh,index
from story_pipeline import contained
VIEWS={'front','rear','left','right','front_three_quarter','rear_three_quarter','interior','wide','detail','top','bottom'}
STYLE_FIELDS=('lighting','palette','contrast','texture','optics','camera_behavior','editing','sound')
def text(value,label):
 if not isinstance(value,str) or not value.strip():raise ValueError(label+' needs actual descriptive text')
 return value.strip()
def fields(row,allowed,label):
 if not isinstance(row,dict):raise ValueError(label+' must be an object')
 extra=set(row)-set(allowed)
 if extra:raise ValueError(label+' has unsupported fields: '+', '.join(sorted(extra)))
def style_spec(style):
 if not isinstance(style,dict):raise ValueError('style must be an object')
 extra=set(style)-set(STYLE_FIELDS)-{'label'}
 if extra:raise ValueError('Unknown style fields (identity must stay in the asset contract): '+', '.join(sorted(extra)))
 text(style.get('label'),'style.label')
 for field in STYLE_FIELDS:text(style.get(field),'style.'+field)
 return style
def identity_text(asset,view):
 core='；'.join(k+'：'+str(v) for k,v in asset['invariants'].items())
 identity=core if any(asset['name'] in str(v) for v in asset['invariants'].values()) else asset['name']+'；'+core
 keys=asset.get('visibility',{}).get(view,list(asset['invariants']))
 visible=asset['name']+'；'+'；'.join(k+'：'+str(asset['invariants'][k]) for k in keys)
 features=[f['text'] for f in asset.get('features',[]) if view in f['views']]
 return identity,visible,features
def validate(source,base_jobs=None,contract_override=None):
 d=copy.deepcopy(contract_override) if contract_override is not None else read(source);fields(d,('version','title','mode','style','assets','shots','notes'),'visual contract');style_spec(d.get('style'));assets=index(d.get('assets',[]),'assets');shots=index(d.get('shots',[]),'shots');errors=[];warnings=[];reference_files={};refs_by_asset={};previous={};last_lateral={};last_facts={}
 if d.get('mode') not in ('t2v','i2v','flf2v'):raise ValueError('Choose t2v/i2v/flf2v; other reference workflows need their actual adapter')
 if not assets or not shots:raise ValueError('Provide assets and shots')
 text(d.get('title'),'title');root=Path(source).resolve().parent
 for aid,a in assets.items():
  fields(a,('id','name','category','invariants','states','references','features','visibility'),aid)
  text(a.get('name'),aid+'.name');locks=a.get('invariants')
  if not isinstance(locks,dict) or not locks:raise ValueError(aid+': explicit invariant fields required')
  if any(not isinstance(k,str) or not k or not isinstance(v,(str,int,float)) or isinstance(v,bool) or (isinstance(v,str) and not v.strip()) or (isinstance(v,(int,float)) and not math.isfinite(v)) for k,v in locks.items()):raise ValueError(aid+': invalid invariant value')
  if not isinstance(a.get('visibility',{}),dict):raise ValueError(aid+': visibility must map views to invariant field names')
  for view,keys in a.get('visibility',{}).items():
   if view not in VIEWS or not isinstance(keys,list) or any(k not in locks for k in keys):raise ValueError(aid+': invalid visible invariant mapping')
  if not isinstance(a.get('states'),dict) or not a['states']:raise ValueError(aid+': named state descriptions required')
  for state,value in a['states'].items():text(value,aid+'.state.'+state)
  references=index(a.get('references',[]),aid+'.references');refs_by_asset[aid]=references
  for rid,ref in references.items():
   if ref.get('view') not in VIEWS or ref.get('role') not in ('identity','style','motion','first_frame','last_frame'):raise ValueError(rid+': reference view/role required')
   text(ref.get('inherit'),rid+'.inherit');text(ref.get('exclude'),rid+'.exclude')
   if not isinstance(ref.get('covers_assets',[aid]),list) or any(x not in assets for x in ref.get('covers_assets',[aid])):raise ValueError(rid+': unknown asset in scene reference coverage')
   if not ref.get('path'):
    warnings.append(aid+'/'+rid+': image not supplied')
    if ref.get('approved') is True:errors.append(aid+'/'+rid+': cannot approve an absent reference file')
    continue
   p=contained(root,ref['path'])
   if not p.is_file() or ref.get('sha256')!=digest(p):errors.append(aid+'/'+rid+': missing or stale reference');continue
   try:
    from PIL import Image
    with Image.open(p) as im:fmt=im.format;im.verify()
   except ImportError as e:raise ValueError('Actual reference-image verification needs Pillow') from e
   except Exception:errors.append(aid+'/'+rid+': invalid reference image');continue
   if fmt not in ('PNG','JPEG','WEBP'):errors.append(rid+': use PNG/JPEG/WebP');continue
   if ref.get('approved') is True and not ref.get('approval_note'):errors.append(rid+': approval needs a recorded visual review note')
   reference_files[(aid,rid)]={'path':str(p),'sha256':ref['sha256'],'extension':{'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[fmt],'approved':ref.get('approved') is True,'covers_assets':ref.get('covers_assets',[aid])}
  for feature in a.get('features',[]):
   text(feature.get('text'),aid+'.feature');views=feature.get('views')
   if not isinstance(views,list) or not views or any(v not in VIEWS for v in views):raise ValueError(aid+': feature views invalid')
 for jid,s in shots.items():
  fields(s,('id','asset','state','view','goal','action','camera','camera_relation','start_state','end_state','cut_reason','duration_sec','screen_direction','identity_overrides','speed_intent','speed_cues','playback_rate','distance_m','declared_speed_kmh','entry_facts','exit_facts','state_change_reason','axis_reset_reason','continuity_bridge','conditioning','reference_view_reason','supporting_assets','style_overrides'),jid)
  aid=s.get('asset')
  if aid not in assets:errors.append(jid+': unknown asset');continue
  a=assets[aid]
  if s.get('state') not in a['states']:errors.append(jid+': unknown state')
  if s.get('view') not in VIEWS:errors.append(jid+': unknown view')
  for field in ('goal','action','camera','start_state','end_state','cut_reason'):text(s.get(field),jid+'.'+field)
  finite(s.get('duration_sec'),jid+'.duration_sec',.01)
  if not isinstance(s.get('entry_facts',{}),dict) or not isinstance(s.get('exit_facts',{}),dict):raise ValueError(jid+': entry/exit_facts must be objects')
  if s.get('screen_direction') not in ('left_to_right','right_to_left','toward','away','stationary','not_applicable'):errors.append(jid+': screen_direction is not explicit')
  if s.get('camera_relation') not in ('static_observer','tracking_subject','subjective','overhead','dolly','handheld_observer','roadside_fixed','parallel_follow','rear_follow','head_on','interior','other'):errors.append(jid+': camera_relation missing')
  overrides_style=s.get('style_overrides',{})
  fields(overrides_style,('lighting','palette','contrast','texture','optics'),jid+'.style_overrides')
  for key,value in overrides_style.items():text(value,jid+'.style_overrides.'+key)
  overrides=s.get('identity_overrides',{})
  if not isinstance(overrides,dict):raise ValueError('identity_overrides must be an object')
  for k,v in overrides.items():
   if k not in a['invariants'] or v!=a['invariants'][k]:errors.append(jid+': immutable identity conflict: '+k)
  speed=s.get('speed_intent','normal');cues=s.get('speed_cues',[])
  if speed not in ('high','normal','static'):errors.append(jid+': invalid speed_intent')
  if not isinstance(cues,list) or any(not isinstance(c,str) or not c.strip() for c in cues):raise ValueError(jid+': speed_cues must be descriptive strings')
  playback=finite(s.get('playback_rate',1),jid+'.playback_rate',.01)
  if speed=='high' and playback!=1:errors.append(jid+': high-speed real-time contract conflicts with retiming; author an intentional slow-motion shot separately')
  if speed=='high' and len(cues)<2:errors.append(jid+': high speed needs at least two visible motion cues, not only an adjective')
  if s.get('distance_m') is not None:
   distance=finite(s['distance_m'],jid+'.distance_m',0);actual=distance/s['duration_sec']*3.6
   if s.get('declared_speed_kmh') is not None:
    declared=finite(s['declared_speed_kmh'],jid+'.declared_speed_kmh',0)
    if abs(actual-declared)>max(5,declared*.2):errors.append(jid+': authored distance/time contradict declared ground speed')
  prior=previous.get(aid)
  direction=s.get('screen_direction')
  if s.get('axis_reset_reason'):last_lateral.pop(aid,None)
  if direction in ('left_to_right','right_to_left'):
   if aid in last_lateral and direction!=last_lateral[aid]:errors.append(jid+': screen direction reverses without a spatial reset, including across inserts')
   last_lateral[aid]=direction
  if prior:
   if prior['state']!=s.get('state') and not s.get('state_change_reason'):errors.append(jid+': unexplained state/damage change')
   prev_exit=last_facts.get(aid,{});entry=s.get('entry_facts',{})
   if not isinstance(prev_exit,dict) or not isinstance(entry,dict):raise ValueError('entry_facts/exit_facts must be objects')
   changed=[k for k in set(prev_exit)&set(entry) if prev_exit[k]!=entry[k]]
   if changed and not s.get('continuity_bridge'):errors.append(jid+': unbridged state at cut: '+', '.join(sorted(changed)))
  previous[aid]=s
  if s.get('continuity_bridge'):last_facts[aid]={}
  last_facts.setdefault(aid,{}).update(s.get('entry_facts',{}));last_facts[aid].update(s.get('exit_facts',{}))
  supporting=s.get('supporting_assets',[])
  if not isinstance(supporting,list):raise ValueError(jid+': supporting_assets must be a list')
  present={aid}
  for binding in supporting:
   fields(binding,('asset','state','view','identity_overrides','state_change_reason','entry_facts','exit_facts','continuity_bridge'),jid+'.supporting_assets')
   bid=binding.get('asset')
   if bid not in assets or bid in present:raise ValueError(jid+': supporting asset missing or duplicated')
   present.add(bid);other=assets[bid]
   if binding.get('state') not in other['states'] or binding.get('view') not in VIEWS:raise ValueError(jid+': supporting asset state/view invalid')
   b_overrides=binding.get('identity_overrides',{})
   if not isinstance(b_overrides,dict):raise ValueError('Supporting identity_overrides must be an object')
   for key,value in b_overrides.items():
    if key not in other['invariants'] or value!=other['invariants'][key]:errors.append(jid+': supporting immutable conflict '+bid+'.'+key)
   prior_binding=previous.get(bid)
   if prior_binding and prior_binding['state']!=binding['state'] and not binding.get('state_change_reason'):errors.append(jid+': unexplained supporting state change '+bid)
   entry,exit_facts=binding.get('entry_facts',{}),binding.get('exit_facts',{})
   if not isinstance(entry,dict) or not isinstance(exit_facts,dict):raise ValueError('Supporting entry/exit facts must be objects')
   changes=[key for key in set(last_facts.get(bid,{}))&set(entry) if last_facts[bid][key]!=entry[key]]
   if changes and not binding.get('continuity_bridge'):errors.append(jid+': supporting state unbridged '+bid)
   if binding.get('continuity_bridge'):last_facts[bid]={}
   last_facts.setdefault(bid,{}).update(entry);last_facts[bid].update(exit_facts);previous[bid]=binding
  conditioning=s.get('conditioning',{})
  if not isinstance(conditioning,dict) or set(conditioning)-{'first','last'}:raise ValueError(jid+': conditioning supports explicit first/last images only')
  if d['mode']=='t2v' and conditioning:errors.append(jid+': text-only mode cannot condition on supplied images')
  for role,rid in conditioning.items():
   if rid not in refs_by_asset[aid]:errors.append(jid+': unknown conditioning reference');continue
   ref=refs_by_asset[aid][rid]
   if ref['role']!=role+'_frame':errors.append(jid+': '+role+' conditioning requires an approved scene keyframe, not an identity sheet or style/motion reference')
   if ref['view']!=s.get('view') and not s.get('reference_view_reason'):errors.append(jid+': reference view differs; needs an authored view-change plan')
  if speed=='high' and s['camera_relation'] in ('parallel_follow','tracking_subject'):warnings.append(jid+': tracked subject may stay still in frame; verify near/far parallax and passing environmental landmarks in the actual output')
 if base_jobs:
  base=read(base_jobs);by={j['id']:j for j in base.get('video_jobs',[])}
  for jid,s in shots.items():
   if jid not in by:errors.append(jid+': absent from base generation jobs');continue
   if by[jid].get('mode')!=d['mode']:errors.append(jid+': mode differs from the base workflow')
   if abs(by[jid]['usable_duration_sec']-s['duration_sec'])>1/by[jid]['edit_fps']:errors.append(jid+': duration differs from the allocated generation job; redesign, do not silently retime')
 return {'valid':not errors,'errors':errors,'warnings':warnings,'reference_files':reference_files,'assets':assets,'shots':shots,'contract':d,'limits':'Structured authoring consistency only; does not visually identify actual people, objects or locations, guarantee style or measure generated quality.'}
def compile_contract(source,base_jobs=None,contract_override=None):
 r=validate(source,base_jobs,contract_override)
 if not r['valid']:raise ValueError('; '.join(r['errors']))
 d=r['contract'];style=d['style'];jobs=[];directives={};reference_map={};copy_files={};diagnostics=[];reference_tasks=[]
 for jid,s in r['shots'].items():
  style={**d['style'],**s.get('style_overrides',{})};aid=s['asset'];a=r['assets'][aid];identity,visible_identity,features=identity_text(a,s['view']);visible='；'.join(features);motion='；'.join(s.get('speed_cues',[]));supporting=[]
  for binding in s.get('supporting_assets',[]):
   asset=r['assets'][binding['asset']];full,shown,details=identity_text(asset,binding['view']);supporting.append({'asset':binding['asset'],'identity_anchor':full,'visible_identity_prompt':shown,'state':binding['state'],'text':shown+'；'+asset['states'][binding['state']]+'；'+'；'.join(details)})
  prompt=f'同一主体：{visible_identity}。本镜可见特征：{visible or "按已批准该视角参考保持轮廓"}。当前状态：{a["states"][s["state"]]}。'
  if supporting:prompt+='同时可见资产分别保持：'+'。'.join(x['text'] for x in supporting)+'。'
  prompt+=f'起始画面：{s["start_state"]}。主要动作：{s["action"]}。摄影机与主体关系：{s["camera"]}。'
  if s.get('speed_intent')=='high':prompt+='动作按实时速度发生，保持1倍播放；运动可见证据：'+motion+'。'
  elif motion:prompt+='运动细节：'+motion+'。'
  prompt+='照明：'+style['lighting']+'。色彩和反差：'+style['palette']+'；'+style['contrast']+'。材料与成像：'+style['texture']+'。焦点与光学：'+style['optics']+'。结束画面：'+s['end_state']+'。'
  missing=[];bound={}
  needed=['first'] if d['mode']=='i2v' else ['first','last'] if d['mode']=='flf2v' else []
  for role in needed:
   rid=s.get('conditioning',{}).get(role);file=r['reference_files'].get((aid,rid))
   if not file or not file['approved']:missing.append(role);continue
   uncovered={aid,*[b['asset'] for b in s.get('supporting_assets',[])]}-set(file['covers_assets'])
   if uncovered:missing.append(role+' reference lacks reviewed coverage for '+','.join(sorted(uncovered)));continue
   rel='references/'+file['sha256']+file['extension'];bound[role]=rel;copy_files[rel]=file
  if d['mode']=='t2v':missing.append('identity-conditioning: text-only attempt')
  if missing:diagnostics.append(jid+': unbound identity/keyframe conditions: '+', '.join(missing))
  for role in needed:
   if role not in bound:reference_tasks.append({'job':jid,'role':role+'_frame','asset':aid,'view':s['view'],'identity_anchor':identity,'supporting_assets':supporting,'visible_features':features,'state':a['states'][s['state']],'scene_anchor':s['start_state'] if role=='first' else s['end_state'],'lighting':style['lighting'],'texture':style['texture'],'status':'not_generated','instruction':'Use approved identity references for every visible person/object/location to create one scene frame; do not feed a multi-panel identity sheet as the video first frame. Verify visible geometry and asset coverage before approval.'})
  directives[jid]={'positive_prompt':prompt,'action':s['action'],'camera':s['camera'],'first':s['start_state'],'last':s['end_state']}
  if bound:reference_map[jid]=bound
  jobs.append({'id':jid,'asset':aid,'view':s['view'],'state':s['state'],'dramatic_goal':s['goal'],'identity_anchor':identity,'supporting_assets':supporting,'positive_prompt':prompt,'duration_sec':s['duration_sec'],'mode':d['mode'],'conditioning':bound,'missing_conditions':missing,'ready_for_reference_conditioned_attempt':not missing,'creative_approval':False,'camera_rule_for_author':style['camera_behavior'],'editing_note':s['cut_reason']+'；'+style['editing'],'sound_note':style['sound'],'test':{'status':'not_run','tested_factor':None,'protocol':'Use the ab command for one declared field; hold model/workflow/inputs/duration/postprocessing and supported seed groups fixed','generated_files':[],'identity_score':None,'speed_score':None,'style_score':None}})
 spec_sha=hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
 return {'version':'1.6.0','title':d['title'],'source_sha256':digest(source),'spec_sha256':spec_sha,'base_jobs_sha256':digest(base_jobs) if base_jobs else None,'style':d['style'],'jobs':jobs,'directives':directives,'reference_map':reference_map,'reference_tasks':reference_tasks,'copy_files':copy_files,'warnings':r['warnings']+diagnostics,'media_generated':False,'limits':r['limits']}
def ab_suite(source,factor,value,shot_id=None):
 original=read(source);candidate=copy.deepcopy(original)
 if factor in ('style.lighting','style.palette','style.contrast','style.texture','style.optics'):
  field=factor.split('.')[1];text(value,factor);candidate['style'][field]=value
 elif factor=='speed_cues':
  target=next((s for s in candidate['shots'] if s['id']==shot_id),None)
  if target is None:raise ValueError('speed_cues comparison needs a known --shot ID')
  target['speed_cues']=value
 else:raise ValueError('Choose one supported visual style field or speed_cues; identity, duration and state are not experimental knobs')
 if candidate==original:raise ValueError('The candidate did not change the selected field')
 baseline=compile_contract(source);changed=compile_contract(source,contract_override=candidate)
 if baseline['directives']==changed['directives']:raise ValueError('The selected field did not change the rendered prompt')
 def pack(r):return {k:r[k] for k in ('spec_sha256','directives','jobs','warnings')}
 return {'version':'1.6.0','status':'not_run','factor':factor,'shot_id':shot_id,'source_sha256':digest(source),'baseline':pack(baseline),'candidate':pack(changed),'fixed_fields':['asset invariants','reference bytes','action','camera','duration','state','screen direction'],'execution_controls_to_hold_fixed':['model and version','workflow','reference/control inputs','generation parameters','supported matched seed group','postprocessing'],'generated_media':False,'scores':None,'winner':None,'limits':'One authored field differs; actual model outputs are still needed. A whole-style package comparison is a different experiment, not single-factor attribution.'}
def build(source,out,base_jobs=None):
 out=Path(out)
 if out.exists():raise ValueError('Use a new visual package directory')
 fresh(out/'manifest.json');r=compile_contract(source,base_jobs);copies=r.pop('copy_files')
 for rel,file in copies.items():
  target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file['path'],target)
  if digest(target)!=file['sha256']:raise ValueError('Copied reference differs from source')
 safe_write(out/'visual-jobs.json',r);safe_write(out/'directives.json',r['directives']);safe_write(out/'reference-map.json',r['reference_map']);safe_write(out/'reference-tasks.json',{'tasks':r['reference_tasks'],'media_generated':False})
 md=['# '+r['title'],'风格已转成可见条件；这是待实测的提示词与审片标准，不是已生成效果。']
 for j in r['jobs']:
  md += ['## '+j['id'],j['positive_prompt'],f'外部时长设置：{j["duration_sec"]}秒；参考状态：'+('已绑定实际批准文件，仍需模型适配和审片' if j['ready_for_reference_conditioned_attempt'] else '待补条件 '+', '.join(j['missing_conditions'])),'剪辑：'+j['editing_note'],'声音：'+j['sound_note']]
 (out/'prompts.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8');files=[{'path':p.relative_to(out).as_posix(),'sha256':digest(p)} for p in sorted(out.rglob('*')) if p.is_file()];safe_write(out/'manifest.json',{'source_sha256':r['source_sha256'],'files':files,'media_generated':False});return {'jobs':len(r['jobs']),'ready_reference_attempts':sum(j['ready_for_reference_conditioned_attempt'] for j in r['jobs']),'warnings':r['warnings'],'output':str(out)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['audit','build','ab']);p.add_argument('source',type=Path);p.add_argument('--base-jobs',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--factor');p.add_argument('--candidate',type=Path);p.add_argument('--shot');a=p.parse_args()
 try:
  if a.command=='ab':
   if not a.candidate or not a.factor:raise ValueError('ab needs --factor and --candidate JSON containing value')
   result=ab_suite(a.source,a.factor,read(a.candidate).get('value'),a.shot);safe_write(a.out,result)
  elif a.command=='build':result=build(a.source,a.out,a.base_jobs)
  else:
   r=validate(a.source,a.base_jobs);result={k:r[k] for k in ('valid','errors','warnings','limits')};safe_write(a.out,result)
  print(json.dumps(result,ensure_ascii=False));return 0 if result.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
