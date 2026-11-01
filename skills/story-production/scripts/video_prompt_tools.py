#!/usr/bin/env python3
"""Prepare model-aware video prompt jobs and unrun comparison protocols. Never calls a media API."""
from __future__ import annotations
import argparse,hashlib,json,math,re,sys
from pathlib import Path
from fractions import Fraction
from creative_tools import read,safe_write
from prompt_contract import check as check_prompt_contract
ASSETS=Path(__file__).resolve().parents[1]/'assets'
def profiles():return read(ASSETS/'video-model-profiles.json')['profiles']
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def choose(profile_id):
 p=next((p for p in profiles() if p['id']==profile_id),None)
 if p is None:raise ValueError('Unknown profile: '+profile_id)
 return p
def lint(prompt,profile_id,mode):
 p=choose(profile_id);errors=[];warnings=[];t=prompt.lower()
 if mode not in p['modes']:errors.append('Mode is not supported by this pinned profile')
 if not prompt.strip():errors.append('Prompt is empty')
 contract=check_prompt_contract(prompt)
 labels={'fixed_and_moving_camera':'Check conflicting fixed-camera and moving-camera instructions; describe phases if intentional','quality_adjective_stack':'Quality adjectives dominate; replace with visible light, material, action and camera evidence','conflicting_depth_of_field':'Depth-of-field instructions conflict'}
 warnings.extend(labels[i] for i in contract['issues'] if i in labels)
 if mode=='i2v' and any(x in t for x in ('change clothes','different face','换衣服','变成另一张脸')):warnings.append('Appearance change may conflict with reference identity; separate it into an intentional shot')
 words=len(re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*",prompt))
 if p.get('max_english_words') and words>p['max_english_words']:warnings.append(f"Above the official {p['max_english_words']}-word English prompt guidance; edit meaningfully, do not blindly truncate")
 if len(re.findall(r'[\u4e00-\u9fff]',prompt))>700:warnings.append('Long Chinese prompt: manually compress nonessential detail; this is a local heuristic, not a model token limit')
 return {'valid':not errors,'errors':errors,'warnings':warnings,'english_word_count':words,'scope':'Text preflight only; no video quality has been measured'}
def validate_plan(p):
 if not isinstance(p.get('meta'),dict) or not isinstance(p.get('shots'),list) or not p['shots']:raise ValueError('Expected compiled shot-plan.json with nonempty shots')
 fps=p['meta'].get('fps')
 if not isinstance(fps,int) or isinstance(fps,bool) or fps<=0:raise ValueError('Edit fps must be a positive integer')
 cursor=0;seen=set()
 for s in p['shots']:
  if s['id'] in seen:raise ValueError('Duplicate shot ID')
  seen.add(s['id'])
  a,b=s['first_frame'],s['end_frame_exclusive']
  if not isinstance(a,int) or not isinstance(b,int) or isinstance(a,bool) or isinstance(b,bool) or a!=cursor or b<=a:raise ValueError('Shot timeline has a gap, overlap or invalid frame interval')
  cursor=b
 return fps,cursor
def refs_for(mapping,root,key):
 values=mapping.get(key,{})
 if not isinstance(values,dict):raise ValueError('Reference entry must be object')
 result={}
 for role in ('first','last'):
  if not values.get(role):continue
  rel=values[role]
  if not isinstance(rel,str) or Path(rel).is_absolute() or re.match(r'^[A-Za-z]:',rel):raise ValueError('Reference paths must be relative to reference-map file')
  p=(root/rel).resolve()
  if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('Reference missing or escapes reference-map directory')
  with p.open('rb') as f:head=f.read(12)
  if not (head.startswith(b'\x89PNG\r\n\x1a\n') or head.startswith(b'\xff\xd8\xff') or (head.startswith(b'RIFF') and head[8:12]==b'WEBP')):raise ValueError('Reference must have a PNG, JPEG or WebP signature')
  result[role]={'path':rel,'sha256':digest(p),'review_status':'file-exists; visual identity must be approved separately'}
 return result
def compile_jobs(plan,profile_id,mode,reference_map=None,reference_root=None,directives=None):
 profile=choose(profile_id)
 if mode not in profile['modes']:raise ValueError(f'{profile_id} does not support {mode}; select an explicit compatible workflow')
 fps,total=validate_plan(plan);native_fps=profile['native_fps'];preset=profile['preset_frames'];capacity=(preset*fps)//native_fps
 if capacity<1:raise ValueError('Native preset cannot contain one edit frame')
 grid=profile.get('frame_grid')
 if grid and (preset-grid['offset'])%grid['multiple']:raise ValueError('Profile frame preset violates its documented grid')
 chars={a['id']:a for a in plan['assets'].get('characters',[])};props={a['id']:a for a in plan['assets'].get('props',[])}
 scenes={s['scene']:s for s in plan.get('scenes',[])}
 refs=reference_map or {};directives=directives or {};jobs=[];posts=[];warnings=[];used=set()
 if refs and mode=='t2v':raise ValueError('Reference images are not conditioning in t2v mode; choose a supported i2v/flf2v profile instead')
 for shot in plan['shots']:
  if shot.get('pure_post'):
   posts.append({'shot':shot['id'],'edit_in_frame':shot['first_frame'],'edit_out_frame_exclusive':shot['end_frame_exclusive'],'instruction':shot['picture'],'sound':shot['sound']});continue
  frames=shot['end_frame_exclusive']-shot['first_frame'];parts=math.ceil(frames/capacity);q,r=divmod(frames,parts);local=0
  for k in range(parts):
   length=q+(k<r);jid=f"{shot['id']}_G{k+1:02}";used.add(jid);override=directives.get(jid,{})
   wanted_native=math.ceil(Fraction(length*native_fps,fps))
   native_count=(max(0,math.ceil(Fraction(wanted_native-grid['offset'],grid['multiple'])))*grid['multiple']+grid['offset']) if grid else preset
   native_count=max(1,native_count)
   scale=float(Fraction(native_count*fps,native_fps*length))
   if not isinstance(override,dict):raise ValueError('Each directive must be object')
   reference=refs_for(refs,reference_root or Path.cwd(),jid)
   global_refs=refs_for(refs,reference_root or Path.cwd(),shot['id'])
   if parts==1 and not reference:reference=global_refs
   elif parts>1:
    if k==0 and 'first' not in reference and 'first' in global_refs:reference['first']=global_refs['first']
    if k==parts-1 and 'last' not in reference and 'last' in global_refs:reference['last']=global_refs['last']
   required=['first'] if mode=='i2v' else ['first','last'] if mode=='flf2v' else []
   missing=[v for v in required if v not in reference]
   action=override.get('action',shot['picture']);first=override.get('first',shot['first_anchor'] if k==0 else f'沿上一生成单元批准尾帧继续，镜内第{local/fps:.3f}秒的具体状态待预演锁定')
   last=override.get('last',shot['last_anchor'] if k==parts-1 else '本镜中间状态待预演确定，不能提前完成全镜结尾')
   camera=override.get('camera',shot['camera']);visible=[]
   sc=scenes.get(shot['scene'],{});wardrobe={**sc.get('costumes',{}),**sc.get('shot_overrides',{}).get(str(shot['index']),{}).get('costumes',{})}
   for aid in shot['asset_ids']:
    a=chars.get(aid) or props.get(aid)
    if a:
     lock=a['name']+'：'+a.get('appearance',a.get('design',''))
     if aid in chars:lock+='；本镜衣装：'+a.get('costumes',{}).get(wardrobe.get(aid),'按批准本镜造型核对')
     visible.append(lock)
   if mode=='t2v':text='；'.join(['主体与环境：'+('；'.join(visible) or '只呈现已批准场景'),'地点：'+shot.get('effective_location',shot.get('scene_heading','')),'开始：'+first,'主要动作：'+action])
   else:text='；'.join(['从已批准参考画面延续，保持身份、衣装、物件数量与场景几何','开始：'+first,'只执行这段运动：'+action])
   text+=f"；景别与透视：{shot['size']}，约{shot['lens_mm_equiv']}mm等效；摄影："+camera+'；光线：'+shot.get('effective_light','沿用批准参考的光源与曝光')+'；结束：'+last
   if shot.get('dialogue'):
    if all(any(t in d['speaker'] for t in ['画外','录音','未来声','电话','旁白']) or d.get('voice_source_shot') for d in shot['dialogue']):text+='；镜内人物听而不说，不对画外声做口型'
   if isinstance(override.get('positive_prompt'),str) and override['positive_prompt'].strip():text=override['positive_prompt'].strip()
   notes=[]
   if parts>1 and not all(override.get(f) for f in ('action','first','last')):notes.append('多段长镜尚需逐段具体动作与中间锚点；不可直接把全镜动作重复执行')
   if missing:notes.append('待生成并批准参考：'+','.join(missing))
   if native_fps!=fps:notes.append('保持真实时长转换帧率；不可直接重解释原生帧率造成加/慢速')
   if native_count!=preset:notes.append('按官方帧网格选择接近本段长度的帧数，属于合法网格规划；非原始示例长度，仍需实际工作流和画质验证')
   if abs(scale-1)>.1:notes.append('原生时长与目标相差超过10%；不得自动加速/拉慢，需调整分段、合法帧数或在实际尾态之后使用已验证把手')
   notes.append('端点保持复核：不能默认裁掉原生尾部；确认完整首尾状态映射到目标片段，音频单独保持批准时序')
   check=lint(text,profile_id,mode);notes+=check['warnings']
   a_frame=shot['first_frame']+local;b_frame=a_frame+length
   voice_sources=[]
   for d in plan.get('dialogues',[]):
    if d.get('shot')!=shot['id']:continue
    voice_in=round(d['start_sec']*fps);voice_out=round(d['end_sec']*fps)
    if voice_in<b_frame and voice_out>a_frame:voice_sources.append({'dialogue_id':d['id'],'speaker':d['speaker'],'text':d['text'],'source_in_frame':voice_in,'source_out_frame_exclusive':voice_out,'overlaps_other_generation_unit':voice_in<a_frame or voice_out>b_frame,'rule':'复用该对白的同一完整批准音频，剪辑阶段按时间位置取对应段，不在每个视频片段重新TTS'})
   audio={'strategy':'separate-approved-audio','instruction':shot.get('sound',''),'dialogue_sources':voice_sources,'native_audio_supported':profile['native_audio'],'note':'即便支持视听联合，精确台词与复用原声仍需实际核对；不自动替换批准音频'}
   conform={'policy':'preserve-both-endpoints; never assume prefix-trim is valid','source_first_index':0,'source_last_index':native_count-1,'target_first_index':0,'target_last_index':length-1,'full_span_duration_ratio':scale,'manual_review_required':True,'large_retime_requires_redesign':abs(scale-1)>.1,'audio_policy':'Do not retime approved dialogue or claim lip sync; conform video and recheck actual mouth/action timing'}
   jobs.append({'id':jid,'shot':shot['id'],'part':k+1,'parts':parts,'mode':mode,'positive_prompt':text,'negative_prompt':override.get('negative_prompt',''),'negative_field_policy':profile['negative_prompt'],'reference_assets':reference,'missing_reference_roles':missing,'edit_in_frame':shot['first_frame']+local,'edit_out_frame_exclusive':shot['first_frame']+local+length,'edit_fps':fps,'usable_duration_sec':float(Fraction(length,fps)),'native_fps':native_fps,'native_frames':native_count,'native_duration_sec':float(Fraction(native_count,native_fps)),'native_frames_covering_take':wanted_native,'native_frame_policy':'nearest-covering-documented-grid' if grid else 'observed-preset-only; arbitrary frame rule unknown','endpoint_conform':conform,'size_reference':{'width':profile['preset_width'],'height':profile['preset_height'],'note':'documented workflow/config example; review actual output dimensions and reference aspect ratio'},'first_anchor':first,'last_anchor':last,'camera':camera,'visible_asset_ids':shot['asset_ids'],'voice_asset_ids':shot.get('voice_asset_ids',[]),'audio':audio,'review_notes':notes,'status':'awaiting-author-and-reference-review','generated_media':False})
   local+=length
 for key in directives:
  if key not in used:raise ValueError('Directive references unknown generation unit '+key)
 known=set(used)|{s['id'] for s in plan['shots'] if not s.get('pure_post')}
 for key in refs:
  if key not in known:raise ValueError('Reference map contains unknown generation unit/shot '+key)
 covered=sum(j['edit_out_frame_exclusive']-j['edit_in_frame'] for j in jobs)+sum(s['edit_out_frame_exclusive']-s['edit_in_frame'] for s in posts)
 if covered!=total:raise ValueError('Generation and post timeline coverage mismatch')
 return {'version':'1.2.0','profile':profile,'source_plan_sha256':None,'edit_fps':fps,'story_frames':total,'video_jobs':jobs,'post_tasks':posts,'summary':{'video_jobs':len(jobs),'post_tasks':len(posts),'jobs_missing_references':sum(bool(j['missing_reference_roles']) for j in jobs),'jobs_requiring_segment_design':sum(any('多段长镜' in n for n in j['review_notes']) for j in jobs),'covered_edit_frames':covered},'execution':'planning only; no API submission, dependency installation, model download or GPU generation','quality_claim':'Unmeasured; suitable prompts and actual outputs must be compared for the chosen model/workflow.'}
def build(plan_path,out,profile_id,mode,refs_path=None,directives_path=None,overwrite=False):
 plan_path=Path(plan_path).resolve();out=Path(out)
 if plan_path.is_relative_to(out.resolve()):raise ValueError('Output must not contain the source plan')
 if out.exists() and any(out.iterdir()) and not overwrite:raise ValueError('Output directory is not empty')
 for name in ['video-jobs.json','preflight.json','prompts.md','manifest.json']:
  path=out/name
  for part in [path,*path.parents]:
   if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Refusing symlink/junction output')
 result=compile_jobs(read(plan_path),profile_id,mode,read(refs_path) if refs_path else None,Path(refs_path).resolve().parent if refs_path else None,read(directives_path) if directives_path else None);result['source_plan_sha256']=digest(plan_path)
 safe_write(out/'video-jobs.json',result,overwrite)
 report={'model':profile_id,'mode':mode,**result['summary'],'gpu_tested':False,'notes':'Draft jobs; missing references, segment design and actual workflow versions must be resolved before media execution.'};safe_write(out/'preflight.json',report,overwrite)
 text=['# 模型适配提示词工作包','\n'+result['quality_claim'],f"\n模型：{result['profile']['title']}\n\n工作流：{result['profile']['workflow_url']}\n\n许可：{result['profile']['license_label']}。具体条款见模型资料表。"]
 for j in result['video_jobs']:
  text += [f"\n## {j['id']}\n\n成片帧 {j['edit_in_frame']}—{j['edit_out_frame_exclusive']}（出点不含），{j['edit_fps']}fps；原生预设{j['native_frames']}帧/{j['native_fps']}fps。",j['positive_prompt'],'\n制作复核：'+'；'.join(j['review_notes'])]
 target=out/'prompts.md'
 if target.is_symlink():raise ValueError('Refusing symlink output')
 target.write_text('\n\n'.join(text)+'\n',encoding='utf-8')
 files=[{'path':n,'sha256':digest(out/n),'bytes':(out/n).stat().st_size} for n in ['video-jobs.json','preflight.json','prompts.md']]
 safe_write(out/'manifest.json',{'generated_by':'story-production-video-prompts','source_sha256':digest(plan_path),'files':files,'media_generated':False},overwrite)
 return report
def benchmark_suite(profile_id,cases=None):
 profile=choose(profile_id);cards={c['id']:c for c in read(ASSETS/'video-prompt-cards.json')['cards']}
 selected=cases or [c for c in ['hesitation','listening','handoff','follow-walk','car-side','team-signal','flf-sit','flf-turn'] if cards[c]['mode'] in profile['modes']]
 known=set(cards)
 if any(c not in known for c in selected):raise ValueError('Unknown prompt card')
 if any(cards[c]['mode'] not in profile['modes'] for c in selected):raise ValueError('Prompt card mode is not supported by the selected profile')
 return {'version':'1.2.0','profile':profile_id,'status':'not_run','protocol':'Each case compares baseline and candidate with the same model, workflow, inputs, parameters and seed. Use matched seeds. Record actual files and human observations; leave unrun scores null.','metrics':['action_fidelity','identity','geometry','camera','texture','editability'],'runs':[{'case':case,'mode':cards[case]['mode'],'seed':seed,'variant':variant,'status':'pending','workflow_fingerprint':None,'settings':None,'prompt':None,'artifact':None,'sha256':None,'scores':None,'observations':None} for case in selected for seed in (42,123) for variant in ('baseline','candidate')],'market_ranking_claim':False}
def benchmark_check(data,root):
 errors=[];complete=[];groups={};metrics=data.get('metrics',[])
 profile=choose(data.get('profile'))
 if metrics!=['action_fidelity','identity','geometry','camera','texture','editability']:errors.append('Use the documented metric set; do not remove failed dimensions')
 for row in data.get('runs',[]):
  key=(row.get('case'),row.get('seed'),row.get('variant'))
  if row.get('mode') not in profile['modes']:errors.append('Run mode is not supported by the selected profile')
  if key in groups:errors.append('Duplicate comparison run '+str(key))
  groups[key]=row
  if row.get('variant') not in ('baseline','candidate'):errors.append('Unknown variant')
  if row.get('status') not in ('pending','complete','failed'):errors.append('Unknown run status')
  if row.get('status')!='complete':continue
  artifact=row.get('artifact')
  if not isinstance(artifact,str) or Path(artifact).is_absolute():errors.append('Completed run needs relative local artifact');continue
  p=(root/artifact).resolve()
  if not p.is_relative_to(root.resolve()) or not p.is_file():errors.append('Missing/out-of-scope artifact');continue
  if digest(p)!=row.get('sha256'):errors.append('Artifact hash mismatch');continue
  if not row.get('workflow_fingerprint') or not isinstance(row.get('settings'),dict) or not row.get('prompt') or not row.get('observations'):errors.append('Completed run needs workflow/settings/prompt/observations')
  required={'model_revision','width','height','frames','fps','steps','sampler','guidance','reference_hashes'}
  if not isinstance(row.get('settings'),dict) or not required<=row['settings'].keys():errors.append('Completed run must record all matched model, sampling and reference settings')
  scores=row.get('scores')
  if not isinstance(scores,dict) or any(not isinstance(scores.get(k),(int,float)) or isinstance(scores.get(k),bool) or not math.isfinite(scores[k]) or not 0<=scores[k]<=5 for k in metrics):errors.append('Completed run requires finite human scores 0–5 for every metric')
  else:complete.append(row)
 pairs=[]
 for row in complete:
  if row['variant']!='baseline':continue
  other=groups.get((row['case'],row['seed'],'candidate'))
  if not other or other not in complete:continue
  if row['settings']!=other['settings'] or row['workflow_fingerprint']!=other['workflow_fingerprint']:errors.append('Unmatched conditions; cannot attribute difference to prompt');continue
  pairs.append({k:other['scores'][k]-row['scores'][k] for k in metrics})
 return {'valid':not errors,'errors':errors,'completed_runs':len(complete),'matched_pairs':len(pairs),'mean_candidate_minus_baseline':{k:sum(p[k] for p in pairs)/len(pairs) for k in metrics} if pairs and not errors else None,'status':'measured-by-supplied-human-records' if pairs and not errors else 'not-evaluated','limits':'Checks records and files, not the honesty of ratings or visual quality. No market-wide superiority inference.'}
def realism_brief(scene,action,camera='locked'):
 if not scene.strip() or not action.strip():raise ValueError('A concrete scene and one main action are required')
 cameras={'locked':'三脚架固定机位，视角与构图全程保持不变。','small-push':'相机以稳定的短距离缓慢靠近，角度不变，不环绕，不叠加变焦。','side-track':'相机在主体侧面以相同步速短距离平移，主体与背景视差连续。'}
 if camera not in cameras:raise ValueError('Unknown realism camera baseline')
 base=f'{scene}。{action}。'+cameras[camera]+'光线来自场景中明确存在的自然光或灯具，保持一致的方向、曝光和自然白平衡。皮肤保留细微自然纹理，衣料褶皱只随动作变化。使用能够看清主要动作的景深，背景透视与物件位置稳定。表演克制，完成动作后自然停住。'
 return {'status':'unrendered-photographic-baseline','positive_zh':base,'reference_requirements':['先检查起始图本身的脸、手、光源、透视与材质','保持同一参考与模型设置做A/B，不用换种子挑最漂亮结果代替比较'],'comparison':[{'variant':'A','change':'固定机位，只保留一个小动作'},{'variant':'B','change':'其他条件完全不变，仅加入所选小幅相机运动'}],'diagnostics':['对比原生成与超分/补帧/锐化后结果','记录第一次出现纹理漂移、悬浮视差或不合理动作的位置'],'limits':'草案只把写实意图变成可检查条件；未测量画面质量，不保证任一模型达到绝对最真实。'}
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 sub.add_parser('profiles');sub.add_parser('cards');c=sub.add_parser('card');c.add_argument('id')
 c=sub.add_parser('lint');c.add_argument('--prompt',required=True);c.add_argument('--profile',required=True);c.add_argument('--mode',choices=['t2v','i2v','flf2v'],required=True)
 c=sub.add_parser('build');c.add_argument('plan',type=Path);c.add_argument('--out',type=Path,required=True);c.add_argument('--profile',required=True);c.add_argument('--mode',choices=['t2v','i2v','flf2v'],required=True);c.add_argument('--references',type=Path);c.add_argument('--directives',type=Path);c.add_argument('--overwrite',action='store_true')
 c=sub.add_parser('benchmark-init');c.add_argument('--profile',required=True);c.add_argument('--cases',nargs='*');c.add_argument('--out',type=Path,required=True)
 c=sub.add_parser('benchmark-check');c.add_argument('input',type=Path)
 c=sub.add_parser('realism');c.add_argument('--scene',required=True);c.add_argument('--action',required=True);c.add_argument('--camera',choices=['locked','small-push','side-track'],default='locked');c.add_argument('--out',type=Path)
 args=p.parse_args()
 try:
  if args.command=='profiles':result=profiles()
  elif args.command=='cards':result=[{k:c[k] for k in ('id','title','mode')} for c in read(ASSETS/'video-prompt-cards.json')['cards']]
  elif args.command=='card':
   result=next((c for c in read(ASSETS/'video-prompt-cards.json')['cards'] if c['id']==args.id),None)
   if result is None:raise ValueError('Unknown prompt card')
  elif args.command=='lint':result=lint(args.prompt,args.profile,args.mode)
  elif args.command=='build':result=build(args.plan,args.out,args.profile,args.mode,args.references,args.directives,args.overwrite)
  elif args.command=='benchmark-init':result=benchmark_suite(args.profile,args.cases);safe_write(args.out,result)
  elif args.command=='realism':
   result=realism_brief(args.scene,args.action,args.camera)
   if args.out:safe_write(args.out,result)
  else:result=benchmark_check(read(args.input),args.input.resolve().parent)
  print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if not isinstance(result,dict) or result.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
