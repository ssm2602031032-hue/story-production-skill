#!/usr/bin/env python3
"""Offline task routing and evidence-linked creative ledgers. Does not write stories or call models."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path

SKILL=Path(__file__).resolve().parents[1]
TASKS=('auto','full','brainstorm','draft','rewrite','critique','dialogue','pitch','production','research','rehearse','format','adapt','opening','emotion','antagonist','ensemble','transitions','pacing','short-form','audio','comics','nonfiction','naming','table-read','prompts','models','evaluation','impact','realism','context','regression','media-qc','subtitles','editorial','metrics','cuts')
GENRES={
 'comedy':('喜剧','搞笑','comedy','sitcom'), 'romance':('爱情','恋爱','romance'),
 'mystery':('悬疑','推理','侦探','mystery','detective'), 'thriller':('惊悚','thriller'),
 'action':('动作','追逐','营救','action'), 'sports':('运动','比赛','竞技','sports'),
 'fantasy':('奇幻','穿越','修仙','魔法','fantasy'), 'sci-fi':('科幻','science fiction','sci-fi'),
 'historical':('历史','年代','考据','historical'), 'horror':('恐怖','horror'),
 'serial':('爽文','网文','连载','升级流','serial'), 'revenge':('复仇','逆袭','revenge'),'crime':('刑侦','警匪','卧底','procedural','crime')}
EXTENSIONS={
 'evidence':('research-evidence',('研究证据','资料溯源','检查引用','csl-json')),
 'causal':('causal-knowledge-checks',('因果图','知情检查','提前知道','事件依赖')),
 'season-grid':('season-payoff-grid',('整季兑现','跨集兑现','承诺兑现表','全季伏笔表')),
 'proofread':('manuscript-proofing',('机械校对','重复段落','完稿校对')),
 'publish-book':('epub-publication',('epub','电子书导出','导出电子书')),
 'screenplay-export':('screenplay-interchange',('fdx','fountain','标准剧本导出')),
 'reference-controls':('reference-control-assets',('控制参考','controlnet','cameractrl','姿态控制','深度控制')),
 'takes':('take-registry-budget',('选片','费用估算','费用情景','候选镜头','take registry')),
 'contact':('visual-contact-review',('接触表','抽帧对照','contact sheet')),
 'audio-qc':('audio-delivery-qc',('响度','lufs','音频质检','对白wav','audio qc')),
 'localize':('subtitle-localization',('翻译字幕','译文字幕','字幕本地化','subtitle localization'))}
TASKS=TASKS+tuple(EXTENSIONS)
EDITING_EXTENSIONS={
 'roughcut':('roughcut-render',('粗剪','渲染预览','审片预览','拼接视频','合并视频','剪辑视频','剪片')),
 'subtitle-conform':('subtitle-conform',('剪后字幕','剪辑后字幕','重排字幕')),
 'edit-diff':('editorial-version-diff',('剪辑版本','剪辑差异','比较剪辑')),
 'edit-story':('story-edit-pass',('叙事剪辑','精剪方案','按剧情剪辑')),
 'edit-dialogue':('dialogue-jl-edit',('j-cut','l-cut','j/l','j-l','声音桥')),
 'edit-rhythm':('edit-rhythm-silence',('去静音','停顿候选','剪辑节奏','静音检测')),
 'edit-transitions':('cut-transitions',('动作匹配','匹配切','溶解转场','转场设计')),
 'proxy':('proxy-relink',('代理回连','原片回连','代理素材','无损裁切')),
 'nle':('nle-interchange',('剪辑交接','davinci','resolve','premiere','cmx3600','edl','音轨otio')),
 'color-handoff':('color-management-handoff',('调色交接','色彩标签','色彩管理','调色方案','cdl')),
 'title-layout':('titles-captions-safe',('片头设计','字幕安全区','文字安全区','多画幅')),
 'final-qc':('final-review-qc',('成片验收','交付验收','切点审看','成片检查'))}
TASKS=TASKS+tuple(EDITING_EXTENSIONS)
EXTENSIONS={**EDITING_EXTENSIONS,**EXTENSIONS}
VISUAL_EXTENSIONS={
 'visual-identity':('asset-identity-contracts',('资产一致性','外观一致性','人物外观漂移','角色变脸','服装漂移','车辆前后不一致','道具前后不一致')),
 'motion-direction':('motion-readability',('速度感','动作很慢','动作悬浮','没有重量感','运动表达')),
 'action-continuity':('action-edit-continuity',('动作衔接','物品交接','动作剪辑','空间跳变')),
 'style-visual':('style-to-visual',('视觉风格','画面风格','风格转译','风格编译','提示词风格')),
 'material':('material-realism',('画质很油','画面很油','油腻画面','塑料皮肤','蜡感','材质不真实','油画感太重')),
 'reference-binding':('reference-role-binding',('参考角色分离','多参考一致性','vace','场景首帧','多资产首帧')),
 'motion-evidence':('motion-evidence',('光流','图像运动量','运动量检测')),
 'look-ab':('look-ab-validation',('风格a/b','观感对照','材质对照','原尺寸细节','原始像素裁剪'))}
TASKS=TASKS+tuple(VISUAL_EXTENSIONS)
EXTENSIONS={**VISUAL_EXTENSIONS,**EXTENSIONS}
BRIDGE_EXTENSIONS={
 'scene-intent':('scene-intent-engine',('场景因果设计','场景策略','人物策略与后果')),
 'script-bridge':('source-shot-trace',('剧本转分镜','原文到镜头','小说转分镜','剧本转提示词','改编映射')),
 'subtext-screen':('subtext-to-screen',('内心戏外化','心理描写转画面','潜台词转动作')),
 'speech-budget':('dialogue-performance-budget',('对白时间分配','台词超过镜长','对白表演时长')),
 'prompt-layers':('prompt-production-layers',('提示词分层','完整镜头工作包','分层提示词')),
 'scene-edit':('scene-context-editing',('情境化剪辑','根据当前情境','按场景剪辑','场景剪辑策略')),
 'handoff':('shot-handoff-contracts',('镜间交出','镜间接收','镜头交接','镜间衔接矩阵')),
 'story-guards':('editorial-story-guards',('关键反应被剪','剪辑叙事保护','保护关键动作','剪辑提前揭示'))}
TASKS=TASKS+tuple(BRIDGE_EXTENSIONS)
EXTENSIONS={**BRIDGE_EXTENSIONS,**EXTENSIONS}
GENRE_MODULES={'comedy':'comedy','romance':'romance','mystery':'mystery-thriller','thriller':'mystery-thriller','horror':'horror-atmosphere','action':'action-stakes','sports':'action-stakes','fantasy':'worldbuilding','sci-fi':'science-fiction','historical':'historical-period','serial':'serial-rewards','revenge':'serial-rewards','crime':'crime-procedural'}
def read(path):
 value=json.loads(Path(path).read_text(encoding='utf-8-sig'))
 if not isinstance(value,dict):raise ValueError('JSON root must be an object')
 return value
def catalog():return read(SKILL/'assets/creative-modules.json')
def has(text,terms):return any(t in text for t in terms)
def cleaned(request):
 # Conservative heuristic: remove common explicit exclusions. This is not semantic parsing.
 return re.sub(r'(?:不要|不需要|不加|不写|without\s+|no\s+)(?:[\w -]{0,12}?)(?:喜剧|搞笑|爱情|悬疑|动作|奇幻|comedy|romance|mystery|action|fantasy)(?:元素)?','',request.lower())
def infer_mode(text):
 if re.search(r'(?:改编成|改成|改编为|adapt.{0,20}into).{0,12}(?:电影|film)',text):return 'film'
 if re.search(r'(?:改编成|改成|改编为|adapt.{0,20}into).{0,12}(?:电视剧|剧集|series)',text):return 'series'
 if has(text,('电视剧','剧集','整季','长剧','短剧','tv series','season')):return 'series'
 if has(text,('小说','novel')):return 'novel'
 return 'film'
def infer_task(text):
 if re.search(r'(?:写|创作|制作|完成).{0,16}(?:完整电影|电影全套|完整小说|整季剧本|小说全文|剧集全套)',text) and not has(text,('只审','只检查','不改正文')):return 'full'
 for task,(_,terms) in EXTENSIONS.items():
  if has(text,terms):return task
 if has(text,('otio','剪辑工程','剪辑交接','editorial handoff')):return 'editorial'
 if has(text,('字幕校时','字幕检查','检查字幕','asr','srt','字幕导入')):return 'subtitles'
 if has(text,('切点检测','切点候选','scenedetect','检测切点')):return 'cuts'
 if has(text,('视频参数','视频元数据','视频技术检查','媒体质检','media qc','帧时间戳')):return 'media-qc'
 if has(text,('提示词回归','promptfoo','prompt regression')):return 'regression'
 if has(text,('vbench','视频指标','视频评分指标')):return 'metrics'
 if has(text,('章节上下文','章节契约','上下文包','chapter context')) and not has(text,('续写','继续写','改写','continue chapter')):return 'context'
 if has(text,('ai感','去ai','塑料皮肤','运镜很假','运镜假','超级真实','photographic realism')):return 'realism'
 if has(text,('视频提示词','优化提示词','润色提示词','提示词模板','prompt pack')):return 'prompts'
 if has(text,('模型选型','选择视频模型','model selection')):return 'models'
 if has(text,('提示词对比','提示词评测','benchmark prompts')):return 'evaluation'
 if has(text,('改稿影响','连锁影响','哪些需要重做','revision impact')):return 'impact'
 if re.search(r'(?:只|仅).{0,18}(?:润色|修改|改写).{0,18}(?:对白|台词)',text):return 'dialogue'
 if has(text,('只改对白','只改台词','润色台词','润色对白','dialogue only','polish dialogue')):return 'dialogue'
 if has(text,('只审','审稿','审读','只检查','critique','review only')):return 'critique'
 if has(text,('读演','读本排练','台词朗读','table read','table-read')):return 'table-read'
 if has(text,('广播剧','有声书','音频剧','audio drama')):return 'audio'
 if has(text,('漫画','条漫','webtoon','comic')):return 'comics'
 if has(text,('竖屏','微短剧','短剧','vertical drama')):return 'short-form'
 if has(text,('真实事件改编','纪实改编','口述改编','nonfiction adaptation')):return 'nonfiction'
 if re.search(r'(?:只|仅|起|取|拟|想|改|选|设计|推荐).{0,10}(?:片名|书名|章名|集名|标题)',text):return 'naming'
 if has(text,('只改开头','只改结尾','重写开篇','重写结局','opening only')):return 'opening'
 if has(text,('加强情感','情感铺垫','催泪生硬','emotional payoff')):return 'emotion'
 if has(text,('设计反派','反派扁平','对手塑造','antagonist design')):return 'antagonist'
 if has(text,('梳理支线','设计群像','群像关系','ensemble design')):return 'ensemble'
 if has(text,('补转场','场景衔接','转场生硬','scene transitions')):return 'transitions'
 if has(text,('压缩篇幅','删减','节奏拖沓','有效扩写','pacing pass')):return 'pacing'
 if has(text,('改编','adapt')):return 'adapt'
 if has(text,('提案','推介','pitch','logline')):return 'pitch'
 if has(text,('考据','研究资料','research')):return 'research'
 if has(text,('角色演练','扮演角色','rehearse')):return 'rehearse'
 if has(text,('只排版','转fountain','format only')):return 'format'
 if has(text,('镜头设计','分镜设计','视觉方案','声音设计','制作方案','shot design','production only')):return 'production'
 if has(text,('改稿','重写','修订','rewrite','revise')):return 'rewrite'
 if has(text,('点子','构思','脑暴','brainstorm')):return 'brainstorm'
 if has(text,('续写','下一章','写这一场','continue chapter','draft scene')):return 'draft'
 if has(text,('不改正文','不改原文','do not rewrite')):return 'critique'
 return 'full'
def plan(request,mode='auto',task='auto',genres=None,modules=None,scope=''):
 if not isinstance(request,str) or not request.strip():raise ValueError('A non-empty request is required')
 infer_requested_mode=mode=='auto'
 clean=cleaned(request);mode=infer_mode(clean) if mode=='auto' else mode;task=infer_task(clean) if task=='auto' else task
 if infer_requested_mode and task=='publish-book':mode='novel'
 if mode not in ('film','novel','series') or task not in TASKS[1:]:raise ValueError('Unknown mode or task')
 selected_genres=list(dict.fromkeys(genres or [g for g,terms in GENRES.items() if has(clean,terms)]))
 if any(g not in GENRES for g in selected_genres):raise ValueError('Unknown genre')
 ids=[];reasons={}
 def add(mid,reason):
  if mid not in ids:ids.append(mid);reasons[mid]=reason
 base={'full':['premise','character','structure'],'brainstorm':['premise','genre-blend'],
       'draft':['scene','dialogue'],'rewrite':['revision','continuity'],'critique':['revision','continuity','reader-experience'],
       'dialogue':['dialogue'],'pitch':['pitch'],'production':['visual-design','sound-design','production-limits'],
       'research':['research'],'rehearse':['character-rehearsal'],'format':['format'],'adapt':['adaptation','adaptation-beat-transfer','source-shot-trace','structure'],
       'opening':['opening-ending'],'emotion':['emotional-payoff'],'antagonist':['antagonist-design'],'ensemble':['ensemble-subplots'],
       'transitions':['scene-transitions'],'pacing':['pacing-compression','continuity'],'short-form':['short-vertical','series'],
       'audio':['audio-drama','sound-design'],'comics':['comics-webtoon','visual-design'],
       'nonfiction':['nonfiction-adaptation','research'],'naming':['title-logline'],'table-read':['table-read','dialogue'],
       'prompts':['video-prompt-architecture','prompt-production-layers','model-selection','identity-continuity'],
       'models':['model-selection','workflow-reproducibility'],
       'evaluation':['prompt-evaluation'],'impact':['revision-impact','continuity'],
       'realism':['realism-diagnostics','camera-blocking','micro-performance','prompt-evaluation'],
       'context':['novel-context-packs'],'regression':['prompt-regression'],
       'media-qc':['technical-media-qc'],'subtitles':['subtitle-alignment'],
       'editorial':['editorial-handoff','technical-media-qc'],
       'metrics':['video-metric-reading'],'cuts':['scene-detection-review']}
 base.update({task:[module] for task,(module,terms) in EXTENSIONS.items()})
 for mid in base[task]:add(mid,'当前任务的直接方法')
 if task in EXTENSIONS or task in ('full','production','editorial','research','critique'):
  for module,terms in EXTENSIONS.values():
   if has(clean,terms):add(module,'请求中明确需要的创作或交付扩展')
 if task in ('audio','comics') and has(clean,('改编','adapt')):add('adaptation','跨媒介时保留源材料映射与取舍')
 if task in ('full','draft','rewrite','adapt','critique'):
  focused=[('opening-ending',('开篇','结局无力','首尾')),
           ('emotional-payoff',('情感铺垫','情感高潮','催泪生硬')),
           ('antagonist-design',('反派','对抗网')),
           ('ensemble-subplots',('群像','多主角','支线')),
           ('scene-transitions',('转场','场景衔接')),
           ('pacing-compression',('节奏拖沓','删减','压缩篇幅'))]
  focused += [('character-arcs',('成长弧','人物弧','角色成长','坠落弧')),('foreshadowing-design',('伏笔','回收')),('nonlinear-time',('非线性','倒叙','多时间线')),('theme-motifs',('意象','主题回响'))]
  for mid,terms in focused:
   if has(clean,terms):add(mid,'请求中明确提到的专项问题')
 if task in ('full','brainstorm','draft','rewrite') and has(clean,('风格实验','风格对照','不同文风','style comparison')):add('style-lab','用户要求比较表达风格')
 if task in ('full','draft','rewrite','adapt'):
  if mode=='novel':add('prose-voice','小说需要独立叙述视角与文风');add('novel-context-packs','按当前章组织前文、契约和知情范围')
  if mode=='series' and task in ('full','adapt'):add('series-room','全季需要持续故事来源与分工');add('series','逐集推进与兑现')
 if task in ('full','brainstorm','draft','rewrite','adapt'):
  for genre in selected_genres:add(GENRE_MODULES[genre],'用户请求中的类型方向：'+genre)
  if len(selected_genres)>1:add('genre-blend','检查多种类型的主次与体验承诺')
  if 'sci-fi' in selected_genres:add('worldbuilding','核对科幻想定的规则与替代方案')
  if 'historical' in selected_genres:add('research','年代事实与生活细节需要来源')
 if task in ('prompts','production','realism'):
  for mid,terms in [('image-to-video',('图生视频','i2v')),('text-to-video',('文生视频','t2v')),('keyframe-video',('首尾帧','关键帧','flf2v')),('motion-physics',('接触','物理','动作失真')),('workflow-reproducibility',('comfyui','工作流'))]:
   if has(clean,terms):add(mid,'视频任务明确需要：'+mid)
 if task in ('editorial','media-qc','cuts','subtitles'):
  for mid,terms in [('subtitle-alignment',('字幕','srt','asr')),('scene-detection-review',('切点','scenedetect')),('technical-media-qc',('技术参数','帧率','元数据'))]:
   if has(clean,terms):add(mid,'请求中同时要求的媒体处理')
 if task in ('evaluation','realism') and has(clean,('vbench','视频指标')):add('video-metric-reading','需要区分实际视频指标的任务边界')
 if task=='full':
  add('scene','把关键事件写成完整正文');add('dialogue','人物实际交流与声音')
  if mode in ('novel','series'):add('project-memory','长篇需要有效版本、事实与交接')
  add('continuity','完成后核对事实与状态');add('reader-experience','独立检查体验，明确模拟局限')
  if mode!='novel':add('visual-design','影视全套');add('sound-design','影视全套');add('production-limits','生成难点与工作量约束');add('format','完整交付格式')
  if mode!='novel' and has(clean,('超级真实','写实','ai感','photoreal')):add('realism-diagnostics','完整创作中的写实要求');add('camera-blocking','使用合理机位与人物调度')
 for mid in modules or []:add(mid,'用户显式选择模块')
 by={m['id']:m for m in catalog()['modules']}
 unknown=[mid for mid in ids if mid not in by]
 if unknown:raise ValueError('Unknown modules: '+', '.join(unknown))
 # Work order differs from reading everything at once. Preserve task-specific order.
 phase_order=('develop','draft','review','production','delivery')
 ids.sort(key=lambda mid:phase_order.index(by[mid]['stage']))
 rows=[dict(by[mid],reason=reasons[mid]) for mid in ids]
 batches=[]
 for phase in phase_order:
  stage_ids=[mid for mid in ids if by[mid]['stage']==phase]
  batches.extend(stage_ids[i:i+3] for i in range(0,len(stage_ids),3))
 deliverables={'full':(['完整章节正文','人物/世界与连续性记录','阅读与导出包'] if mode=='novel' else ['完整逐集正文与全季入口' if mode=='series' else '完整剧本','人物/场景/道具与连续性记录','秒级分镜与AI制作队列','阅读与导出包']),
  'brainstorm':['有区别的少量方向','推荐方案与关键未决点'],'draft':['指定范围完整正文','必要的连续性更新'],
  'rewrite':['指定范围修订稿','实际改动与受影响位置'],'critique':['有证据的问题与优先级','最小改法；不自动改正文'],
  'dialogue':['指定台词或对白替换稿','保留信息与人物关系说明'], 'pitch':['指定用途的简介/梗概/提案草稿'],
  'production':['指定范围视觉/声音/分镜方案','待制作验证项'],'research':['有来源的可用发现','冲突与未核实部分'],
  'rehearse':['有限知情的角色对话','正史支持项与新提案分开'],'format':['指定格式转换','正文未变的核对'],
  'adapt':['改编正文或用户指定方案','源章节到集/场映射及取舍原因'],
  'opening':['指定开篇/结尾实际文本','需联动的中段伏笔'],
  'emotion':['铺垫与回应关系','指定情感场景正文'],
  'antagonist':['对手目标/资源/知情与行动','指定对抗场面'],
  'ensemble':['各支线行动与相交节点','指定范围正文'],
  'transitions':['前场尾部、桥接与后场开头','时空与道具衔接说明'],
  'pacing':['指定范围删减或扩写稿','取舍损失与连续性联动'],
  'short-form':['用户指定短剧集数完整文本','竖屏构图与跨集状态'],
  'audio':['广播剧/有声版本文本','角色声线与音效录音任务；不冒称音频已生成'],
  'comics':['漫画/条漫分格脚本','阅读顺序、气泡和图像任务；不冒称成品漫画'],
  'nonfiction':['事实/推断/虚构对照','用户指定范围改编文本'],
  'naming':['少量有区别的命名候选','推荐名称及简介'],
  'table-read':['对白读本与表演提示','真实计时或明确估计，必要台词修订'],
  'prompts':['按所选模型与模式写的镜头提示词','独立参数、参考条件与待实测项'],
  'models':['可核验的模型/工作流选择','明确能力、许可与未验证项'],
  'evaluation':['固定条件的A/B测试方案','只有实际产物与观察才填写的结果记录'],
  'impact':['源版本改动与直接依赖清单','需要人工复核或重建的产物'],
  'realism':['真实摄影基准提示词与单变量对照','起始图、动作、运镜和后期的分层排查'],
  'context':['指定章的资料包与省略说明','作者与读者知情边界；不冒充已续写正文'],
  'regression':['可运行的离线Promptfoo配置','实际运行结果或明确待运行状态；不等于视频评分'],
  'media-qc':['实际媒体技术报告与采样范围','需复看的告警；不自动证明写实'],
  'subtitles':['用户指定的字幕校验或ASR导入','识别与剧本差异待核对'],
  'editorial':['真实OTIO画面时间线或明确缺素材规划工程','素材范围、帧率与缺失引用记录'],
  'metrics':['与视频任务匹配的指标方案','实际评分证据或明确未运行状态'],
  'cuts':['实际切点候选或缺少依赖说明','人工映射场次与误报复核'],
  **{key:[by[value[0]]['summary'],'实际产物与验证边界；不代替正文或生成媒体'] for key,value in EXTENSIONS.items()}}[task]
 return {'version':'1.7.0','status':'planned','request':request,'mode':mode,'task':task,'scope':scope or '遵循用户指定范围；未指定时按任务语义处理','genres':selected_genres,'modules':rows,'read_batches':batches,'deliverables':deliverables,'routing_note':'关键词路由只作起点；显式mode/task优先，不能把计划清单当作品正文或已完成任务。','media_generated':False}

def safe_write(path,value,overwrite=False):
 path=Path(path)
 for part in [path,*path.parents]:
  if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Refusing symlink/junction output')
 if path.exists() and not overwrite:raise ValueError('Output exists; use --overwrite only for an intentional update')
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def source_index(path):
 path=Path(path).resolve();data=read(path);anchors={};entities=set();dependencies={}
 def collect(f,prefix=''):
  for key in ('characters','props','locations'):
   entities.update(a['id'] for a in f.get(key,[]) if isinstance(a,dict) and isinstance(a.get('id'),str))
  for sc in f.get('scenes',[]):
   key=prefix+f"S{sc['n']:02}";parts=[]
   for i,row in enumerate(sc.get('shots',[]),1):
    if not isinstance(row,list) or len(row)!=12:continue
    text=row[4]+'\n'+'\n'.join(d[1] for d in row[5]);anchors[key+f'_{i:03}']=text;parts.append(text)
   anchors[key]='\n'.join(parts)
 if data.get('kind')=='novel':
  for key in ('characters','props','locations'):entities.update(a['id'] for a in data.get(key,[]))
  for ch in data.get('chapters',[]):anchors[f"C{ch['n']:03}"]=ch.get('body','')
 elif data.get('kind')=='series':
  for key in ('characters','props','locations'):entities.update(a['id'] for a in data.get(key,[]))
  from story_pipeline import contained
  for ep in data.get('episodes',[]):
   source=contained(path.parent,ep['source']);film=read(source);dependencies[ep['source']]=hashlib.sha256(source.read_bytes()).hexdigest()
   prefix=f"E{ep['n']:03}/";collect(film,prefix);anchors[prefix[:-1]]='\n'.join(v for k,v in anchors.items() if k.startswith(prefix) and '_' not in k)
 else:collect(data)
 return anchors,entities,{'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'dependencies':dependencies}

def new_ledger(source):
 anchors,entities,fingerprint=source_index(source)
 return {'version':'1.1.0','status':'working','source':Path(source).name,**fingerprint,'facts':[],'promises':[],'issues':[],'decisions':[],'scope_note':'人工填写实际证据；空表不代表已审校。','available_anchor_examples':list(anchors)[:12]}

def check_ledger(ledger,source):
 anchors,entities,fingerprint=source_index(source);errors=[];warnings=[];ids=set()
 characters={a['id'] for a in read(source).get('characters',[]) if isinstance(a,dict) and isinstance(a.get('id'),str)}
 def locations(values,label,required=True):
  if not isinstance(values,list) or (required and not values):errors.append(label+' needs non-empty anchor list');return
  for value in values:
   if not isinstance(value,str) or value not in anchors:errors.append(label+' unknown anchor '+str(value))
 def record(item,label):
  if not isinstance(item,dict):errors.append(label+' must be object');return False
  value=item.get('id')
  if not isinstance(value,str) or not value:errors.append(label+' needs id')
  elif value in ids:errors.append('Duplicate ledger ID '+value)
  else:ids.add(value)
  return True
 if not isinstance(ledger,dict):return {'valid':False,'errors':['Ledger must be object'],'warnings':[]}
 if ledger.get('source_sha256')!=fingerprint['source_sha256']:errors.append('Ledger source fingerprint is stale; inspect source changes before updating the ledger')
 if ledger.get('dependencies',{})!=fingerprint['dependencies']:errors.append('Episode source fingerprints changed; review affected cross-episode records')
 groups={}
 for group in ('facts','promises','issues','decisions'):
  rows=ledger.get(group,[])
  if not isinstance(rows,list):errors.append(group+' must be a list');rows=[]
  groups[group]=rows
 for item in groups['facts']:
  if not record(item,'fact'):continue
  kind=item.get('kind')
  if kind not in ('canon','belief','proposal'):errors.append('Fact kind must be canon, belief or proposal')
  if not item.get('statement'):errors.append('Fact needs statement')
  locations(item.get('at',[]),str(item.get('id')),required=kind!='proposal')
  if item.get('entity_id') and item['entity_id'] not in entities:errors.append('Unknown entity '+str(item['entity_id']))
  if kind=='belief' and item.get('holder_id') not in characters:errors.append('Belief needs a known character holder_id; it is not global truth')
  if item.get('quote') and not any(item['quote'] in anchors.get(a,'') for a in item.get('at',[])):errors.append(str(item.get('id'))+' quote not found at cited anchors')
 for item in groups['promises']:
  if not record(item,'promise'):continue
  locations(item.get('setup',[]),str(item.get('id'))+' setup')
  locations(item.get('resolution',[]),str(item.get('id'))+' resolution',required=item.get('status')=='resolved')
  if item.get('status') not in ('planned','resolved','open-intentional'):errors.append('Invalid promise status')
  if item.get('status')=='planned':warnings.append(str(item.get('id'))+' has not yet been resolved in authored text')
  if item.get('status')=='open-intentional' and not item.get('reason'):errors.append('Intentionally open promise requires reason')
 for item in groups['issues']:
  if not record(item,'issue'):continue
  if item.get('kind') not in ('contradiction','bridge','style','production'):errors.append('Invalid issue kind')
  locations(item.get('at',[]),str(item.get('id'))+' evidence')
  if not item.get('observation'):errors.append('Issue requires observation')
  status=item.get('status')
  if status not in ('open','fixed','deferred'):errors.append('Invalid issue status')
  if status=='fixed':
   locations(item.get('fix_at',[]),str(item.get('id'))+' fix')
   if not item.get('verification'):errors.append('Fixed issue needs verification explaining the actual change')
  else:warnings.append(str(item.get('id'))+' remains '+str(status))
 for item in groups['decisions']:
  if not record(item,'decision'):continue
  if item.get('status') not in ('proposed','adopted','rejected'):errors.append('Invalid decision status')
  if not item.get('decision') or not item.get('reason'):errors.append('Decision needs content and reason')
  locations(item.get('affects',[]),str(item.get('id'))+' affects',required=item.get('status')=='adopted')
 if not any(groups.values()):warnings.append('Empty ledger: no literary review has been recorded')
 return {'valid':not errors,'errors':errors,'warnings':warnings,'counts':{k:len(v) for k,v in groups.items()},'available_anchors':len(anchors),'validation_scope':'Checks fingerprints, references and claimed workflow states; does not prove causality, character quality or actual audience response.','human_review_required':True}

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
 commands.add_parser('catalog')
 c=commands.add_parser('plan');c.add_argument('--request',required=True);c.add_argument('--mode',choices=['auto','film','novel','series'],default='auto');c.add_argument('--task',choices=TASKS,default='auto');c.add_argument('--genres',nargs='*',choices=list(GENRES));c.add_argument('--modules',nargs='*');c.add_argument('--scope',default='');c.add_argument('--out',type=Path);c.add_argument('--overwrite',action='store_true')
 c=commands.add_parser('ledger-init');c.add_argument('--source',type=Path,required=True);c.add_argument('--out',type=Path,required=True)
 c=commands.add_parser('ledger-check');c.add_argument('ledger',type=Path);c.add_argument('--source',type=Path,required=True);c.add_argument('--report',type=Path)
 args=p.parse_args(argv)
 try:
  if args.command=='catalog':result=catalog()
  elif args.command=='plan':
   result=plan(args.request,args.mode,args.task,args.genres,args.modules,args.scope)
   if args.out:safe_write(args.out,result,args.overwrite)
  elif args.command=='ledger-init':result=new_ledger(args.source);safe_write(args.out,result)
  else:
   result=check_ledger(read(args.ledger),args.source)
   if args.report:safe_write(args.report,result)
  print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as exc:print('Error: '+str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
