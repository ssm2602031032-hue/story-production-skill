#!/usr/bin/env python3
"""Build a portable, grouped production board and JSON Canvas file from authored information. Never changes model wiring or approves media."""
from pathlib import Path
import argparse,copy,hashlib,heapq,html,json,math,re,shutil,sys,unicodedata
from creative_tools import read,safe_write
from delivery_utils import digest,fresh,index
from story_pipeline import contained
GRID=20;WIDTH=360;HEIGHT=280;XGAP=140;YGAP=60;PAD=60
STATUS={'planned':('待制作','#8d9aac'),'draft':('草稿','#5b9dc4'),'review':('待审看','#c69236'),'approved':('已批准','#4c9c7f'),'rejected':('已弃用','#c77373')}
def display_units(s):return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)
def wrapped(s,max_units):
 lines=[];line=''
 for c in s:
  if c=='\n':lines.append(line);line='';continue
  if display_units(line+c)>max_units:lines.append(line);line=c
  else:line+=c
 if line or not lines:lines.append(line)
 return lines
def uid(prefix,value):return prefix+hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]
def check_spec(source):
 d=read(source);groups=index(d.get('groups',[]),'groups');stages=index(d.get('stages',[]),'stages');nodes=index(d.get('nodes',[]),'nodes');edges=index(d.get('edges',[]),'edges')
 if not d.get('title') or not groups or not stages or not nodes:raise ValueError('title, ordered groups/stages, and nodes are required')
 if len(nodes)>120 or len(edges)>240:raise ValueError('Split large work into scene/episode boards with an overview; limit 120 cards and 240 relations per board')
 if len(stages)>8:raise ValueError('At most eight stages per readable board; split views rather than shrinking text')
 for collection in (groups,stages):
  for key,row in collection.items():
   if not isinstance(row.get('title'),str) or not row['title'].strip() or len(row['title'])>60:raise ValueError(key+': concise group/stage title required')
 for nid,n in nodes.items():
  if n.get('group') not in groups or n.get('stage') not in stages:raise ValueError(nid+': unknown group/stage')
  if n.get('status') not in STATUS:raise ValueError(nid+': unknown status')
  if not isinstance(n.get('order'),int) or isinstance(n['order'],bool) or n['order']<0:raise ValueError(nid+': nonnegative integer reading order required')
  if not isinstance(n.get('title'),str) or not n['title'].strip() or len(wrapped(n['title'],36))>2:raise ValueError(nid+': title exceeds two card lines; use details')
  if not isinstance(n.get('summary'),str) or len(wrapped(n['summary'],40))>5:raise ValueError(nid+': summary exceeds five card lines; move full prose/prompts to details')
  if not isinstance(n.get('details',''),str):raise ValueError(nid+': details must be text')
  if n.get('status')=='approved' and not n.get('review_note'):raise ValueError(nid+': approval requires an actual review note')
  if n.get('file'):
   p=contained(Path(source).resolve().parent,n['file'])
   if not p.is_file() or n.get('sha256')!=digest(p):raise ValueError(nid+': linked material is missing or changed')
  if n.get('url') and not re.fullmatch(r'https?://[^\s]+',n['url']):raise ValueError(nid+': only explicit HTTP(S) reference links are accepted')
  if n.get('pinned'):
   p=n['pinned']
   if not isinstance(p,dict) or set(p)!={'x','y'} or any(not isinstance(v,int) or isinstance(v,bool) or v%GRID for v in p.values()):raise ValueError(nid+': pinned positions use integer multiples of the 20px board grid')
 for eid,e in edges.items():
  if e.get('from') not in nodes or e.get('to') not in nodes or e['from']==e['to']:raise ValueError(eid+': relation endpoints must be distinct existing cards')
  if not isinstance(e.get('label'),str) or not e['label'].strip():raise ValueError(eid+': name the relation; do not draw decorative unlabeled wires')
 return d,groups,stages,nodes,edges
def overlap(a,b):return a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']
def layout(source,previous=None):
 d,groups,stages,nodes,edges=check_spec(source);positions={};old={};warnings=[];group_bounds=[];y=180
 if previous:
  before=read(previous)
  if before.get('layout_engine')!='stage-grid':raise ValueError('Only a prior stage-grid layout can be preserved')
  old=index(before.get('cards',[]),'previous cards')
 reserved={}
 for nid,n in nodes.items():
  position=n.get('pinned') or (old.get(nid) if old.get(nid,{}).get('group')==n['group'] and old.get(nid,{}).get('stage')==n['stage'] else None)
  if position:
   if any(not isinstance(position.get(k),int) or isinstance(position[k],bool) or position[k]%GRID for k in ('x','y')):raise ValueError('Previous layout coordinates must be integer grid positions')
   reserved[nid]={'x':position['x'],'y':position['y'],'width':WIDTH,'height':HEIGHT}
 for gid in groups:
  members=[n for n in nodes.values() if n['group']==gid]
  if not members:continue
  counts={sid:0 for sid in stages}
  for sid_index,sid in enumerate(stages):
   column=sorted((n for n in members if n['stage']==sid),key=lambda n:(n['order'],n['id']))
   for n in column:
    if n.get('pinned'):x,ny=n['pinned']['x'],n['pinned']['y']
    elif n['id'] in old and old[n['id']].get('group')==gid and old[n['id']].get('stage')==sid:x,ny=old[n['id']]['x'],old[n['id']]['y']
    else:
     x=PAD+sid_index*(WIDTH+XGAP);ny=y+80+counts[sid]*(HEIGHT+YGAP)
     while any(overlap({'x':x,'y':ny,'width':WIDTH,'height':HEIGHT},p) for p in [*positions.values(),*reserved.values()]):ny+=HEIGHT+YGAP
    positions[n['id']]={'id':n['id'],'group':gid,'stage':sid,'x':x,'y':ny,'width':WIDTH,'height':HEIGHT};counts[sid]+=1
  placed=[positions[n['id']] for n in members];minx=min(p['x'] for p in placed)-30;miny=min(p['y'] for p in placed)-60;maxx=max(p['x']+p['width'] for p in placed)+30;maxy=max(p['y']+p['height'] for p in placed)+30
  group_bounds.append({'id':gid,'title':groups[gid]['title'],'x':minx,'y':miny,'width':maxx-minx,'height':maxy-miny});y=math.ceil(max(y,maxy+100)/GRID)*GRID
 cards=list(positions.values());collisions=[(a['id'],b['id']) for i,a in enumerate(cards) for b in cards[i+1:] if overlap(a,b)]
 if collisions:raise ValueError('Pinned/preserved card positions collide; review rather than silently moving them: '+str(collisions[:8]))
 for i,a in enumerate(group_bounds):
  for b in group_bounds[i+1:]:
   if overlap(a,b):raise ValueError('Group bounds overlap after pinned/preserved positions; use separate boards or adjust pins')
 if any(n['x']<0 or n['y']<180 for n in cards):raise ValueError('Cards must stay below the title/legend area and within nonnegative board coordinates')
 width=max(p['x']+p['width'] for p in cards)+80;height=max(p['y']+p['height'] for p in cards)+80
 if width*height>24000000:raise ValueError('Board becomes too sparse/large; split it or revise manual positions')
 routes=[];occupancy={}
 for eid,e in edges.items():
  a,b=positions[e['from']],positions[e['to']];forward=b['x']>=a['x']+a['width'];from_side='right' if forward else 'bottom';to_side='left' if forward else 'top'
  start=(a['x']+a['width'],a['y']+a['height']//2) if forward else (a['x']+a['width']//2,a['y']+a['height']);end=(b['x'],b['y']+b['height']//2) if forward else (b['x']+b['width']//2,b['y'])
  points=route(start,end,cards,width,height,occupancy)
  if points is None:warnings.append(eid+': no collision-free route found; relation retained for manual review');points=[]
  routes.append({'id':eid,'from':e['from'],'to':e['to'],'label':e['label'],'fromSide':from_side,'toSide':to_side,'points':points,'routed':bool(points)})
 return {'version':'1.8.0','layout_engine':'stage-grid','title':d['title'],'source_sha256':digest(source),'stages':list(stages.values()),'groups':group_bounds,'cards':cards,'edges':routes,'width':width,'height':height,'warnings':warnings,'native_app_tested':False,'limits':'Production planning layout only; no generation/execution links are rewired. JSON Canvas clients choose their own edge rendering and may differ from this local preview.'}
def route(start,end,cards,width,height,usage):
 start=tuple(v//GRID for v in start);end=tuple(v//GRID for v in end);maxx=math.ceil(width/GRID);maxy=math.ceil(height/GRID)
 def blocked(p):
  if p in (start,end):return False
  x,y=p[0]*GRID,p[1]*GRID
  return any(c['x']<x<c['x']+c['width'] and c['y']<y<c['y']+c['height'] for c in cards)
 frontier=[(0,0,start,None)];cost={(start,None):0};parents={};found=None
 while frontier:
  _,g,pos,direction=heapq.heappop(frontier);state=(pos,direction)
  if g!=cost.get(state):continue
  if pos==end:found=state;break
  for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
   nxt=(pos[0]+dx,pos[1]+dy);nd=(dx,dy)
   if not 0<=nxt[0]<=maxx or not 7<=nxt[1]<=maxy or blocked(nxt):continue
   step=1+(0.3 if direction is not None and direction!=nd else 0)+usage.get(nxt,0)*.15;new=g+step;ns=(nxt,nd)
   if new<cost.get(ns,float('inf')):cost[ns]=new;parents[ns]=state;priority=new+abs(nxt[0]-end[0])+abs(nxt[1]-end[1]);heapq.heappush(frontier,(priority,new,nxt,nd))
 if found is None:return None
 points=[];current=found
 while current in parents:points.append(current[0]);current=parents[current]
 points.append(start);points.reverse()
 for p in points:usage[p]=usage.get(p,0)+1
 compact=[]
 for p in points:
  p=(p[0]*GRID,p[1]*GRID)
  if len(compact)>=2 and (compact[-1][0]-compact[-2][0])*(p[1]-compact[-1][1])==(compact[-1][1]-compact[-2][1])*(p[0]-compact[-1][0]):compact[-1]=p
  else:compact.append(p)
 return compact
def export_bundle(source,out,previous=None,font=None):
 d,groups,stages,nodes,edges=check_spec(source);l=layout(source,previous);out=Path(out)
 if out.exists():raise ValueError('Choose a new canvas bundle directory; existing layouts are never overwritten')
 fresh(out/'manifest.json');raw=[];raw_edges=[];colors={sid:['#4c78a8','#6d8e7c','#8a7ba8','#b49260','#a47c82','#63798e'][i%6] for i,sid in enumerate(stages)};notes={};portable=copy.deepcopy(d);portable_nodes={n['id']:n for n in portable['nodes']}
 # Background groups appear before cards in JSON Canvas z-order.
 for g in l['groups']:raw.append({'id':uid('g',g['id']),'type':'group','label':g['title'],**{k:g[k] for k in ('x','y','width','height')},'color':'#dfe5ec'})
 for i,stage in enumerate(l['stages']):raw.append({'id':uid('h',stage['id']),'type':'text','x':PAD+i*(WIDTH+XGAP),'y':140,'width':WIDTH,'height':60,'text':'## '+stage['title'],'color':colors[stage['id']]})
 raw.append({'id':'board-title','type':'text','x':PAD,'y':20,'width':min(l['width']-120,1100),'height':90,'text':'# '+d['title']+'\n按场景从上到下，按制作阶段从左到右。卡片状态不等于媒体已生成。'})
 for c in l['cards']:
  n=nodes[c['id']];nid=uid('n',c['id']);note='notes/'+nid+'.md';notes[c['id']]=note;content='# '+n['title']+'\n\n状态：'+STATUS[n['status']][0]+'\n\n'+n['summary']+'\n\n'+n.get('details','')
  if n.get('review_note'):content+='\n\n审看记录：'+n['review_note']
  p=out/note;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((content+'\n').encode('utf-8'))
  body='## '+n['title']+'\n\n**'+STATUS[n['status']][0]+'**\n\n'+n['summary']+'\n\n[完整内容]('+note+')'
  if n.get('file'):
   original=contained(Path(source).resolve().parent,n['file']);rel='media/'+digest(original)+original.suffix.lower();dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
   if digest(dest)!=n['sha256']:raise ValueError('Material changed during copy')
   portable_nodes[c['id']]['file']=rel
   raw.append({'id':nid,'type':'text','x':c['x'],'y':c['y'],'width':WIDTH,'height':100,'text':'**'+n['title']+'** · '+STATUS[n['status']][0]+'\n[详情]('+note+')','color':colors[n['stage']]})
   raw.append({'id':nid+'file','type':'file','x':c['x'],'y':c['y']+100,'width':WIDTH,'height':HEIGHT-100,'file':rel})
  else:raw.append({'id':nid,'type':'text',**{k:c[k] for k in ('x','y','width','height')},'text':body,'color':colors[n['stage']]})
  if n.get('url'):content+='\n\n参考链接：'+n['url'];p.write_bytes((content+'\n').encode('utf-8'))
 for e in l['edges']:raw_edges.append({'id':uid('e',e['id']),'fromNode':uid('n',e['from']),'toNode':uid('n',e['to']),'fromSide':e['fromSide'],'toSide':e['toSide'],'toEnd':'arrow','label':e['label']})
 safe_write(out/'board.canvas',{'nodes':raw,'edges':raw_edges});safe_write(out/'layout.json',l);safe_write(out/'source-spec.json',portable)
 # An offline textual counterpart keeps every detail accessible without a canvas app.
 md=['# '+d['title'],'布局按场景和制作阶段组织；.canvas路径以本文件夹为根，导入时保留notes/与media/。客户端可能自行重绘连线，尚未在其原生界面验证。']
 for gid,g in groups.items():
  md.append('## '+g['title'])
  for sid,stage in stages.items():
   matches=sorted((n for n in nodes.values() if n['group']==gid and n['stage']==sid),key=lambda n:(n['order'],n['id']))
   if matches:md.append('### '+stage['title']);md.extend('- ['+n['title']+']('+notes[n['id']]+') · '+STATUS[n['status']][0] for n in matches)
 (out/'index.md').write_bytes(('\n\n'.join(md)+'\n').encode('utf-8'))
 if font:render_preview(d,l,out/'preview.png',font,Path(source).resolve().parent)
 safe_write(out/'manifest.json',{'version':'1.8.0','source_sha256':digest(source),'files':[{'path':p.relative_to(out).as_posix(),'sha256':digest(p)} for p in sorted(out.rglob('*')) if p.is_file()],'native_canvas_app_opened':False,'media_generated':False})
 return {'output':str(out),'cards':len(nodes),'groups':len(l['groups']),'relations':len(edges),'unrouted_relations':sum(not x['routed'] for x in l['edges']),'preview_generated':bool(font),'native_app_tested':False,'warnings':l['warnings']}
def render_preview(spec,l,output,font,root):
 try:from PIL import Image,ImageDraw,ImageFont,ImageOps
 except ImportError as e:raise ValueError('PNG preview needs Pillow and an actual font') from e
 if not Path(font).is_file():raise ValueError('Preview font missing')
 im=Image.new('RGB',(l['width'],l['height']),(245,247,250));draw=ImageDraw.Draw(im);regular=ImageFont.truetype(str(font),18);small=ImageFont.truetype(str(font),15);large=ImageFont.truetype(str(font),30);medium=ImageFont.truetype(str(font),22);nodes={x['id']:x for x in spec['nodes']}
 draw.text((PAD,30),spec['title'],font=large,fill='#172b42');draw.text((PAD,80),'场景 × 制作阶段  /  文字、参考、生成与审看状态分开  /  完整内容见详情文件',font=regular,fill='#53697e')
 for i,s in enumerate(l['stages']):draw.text((PAD+i*(WIDTH+XGAP),150),s['title'],font=medium,fill='#24445f')
 for g in l['groups']:draw.rounded_rectangle((g['x'],g['y'],g['x']+g['width'],g['y']+g['height']),radius=18,fill='#e9eef3');draw.text((g['x']+24,g['y']+14),g['title'],font=medium,fill='#304b63')
 for edge in l['edges']:
  pts=[tuple(p) for p in edge['points']]
  if len(pts)>1:
   draw.line(pts,fill='#8aa0b4',width=2);a,b=pts[-2:];dx,dy=b[0]-a[0],b[1]-a[1];mag=max(1,math.hypot(dx,dy));ux,uy=dx/mag,dy/mag;draw.polygon([b,(b[0]-ux*10-uy*5,b[1]-uy*10+ux*5),(b[0]-ux*10+uy*5,b[1]-uy*10-ux*5)],fill='#6c879d')
   if edge['label']!='支撑下一步':
    label=edge['label'];box=draw.textbbox((0,0),label,font=small);tw=box[2]-box[0]
    for first,last in zip(pts,pts[1:]):
     if first[1]==last[1] and abs(last[0]-first[0])>=tw+20:
      tx=(first[0]+last[0]-tw)/2;ty=first[1]-24;draw.rectangle((tx-4,ty,tx+tw+4,ty+22),fill='#f5f7fa');draw.text((tx,ty),label,font=small,fill='#5d7489');break
 for c in l['cards']:
  n=nodes[c['id']];x,y=c['x'],c['y'];draw.rounded_rectangle((x,y,x+WIDTH,y+HEIGHT),radius=12,fill='#ffffff',outline='#d2dce5',width=1);label,color=STATUS[n['status']];draw.rounded_rectangle((x+18,y+18,x+98,y+43),radius=7,fill=color);draw.text((x+28,y+19),label,font=small,fill='white')
  for i,line in enumerate(wrapped(n['title'],36)):draw.text((x+18,y+58+i*26),line,font=regular,fill='#1b3146')
  if n.get('file'):
   p=contained(root,n['file'])
   try:
    with Image.open(p) as source:thumb=ImageOps.contain(source.convert('RGB'),(WIDTH-36,128));im.paste(thumb,(x+18,y+116))
   except Exception:draw.text((x+18,y+132),'媒体文件 · 在原应用查看',font=regular,fill='#647b8e')
  else:
   for i,line in enumerate(wrapped(n['summary'],40)):draw.text((x+18,y+124+i*23),line,font=small,fill='#4c6377')
  draw.text((x+18,y+HEIGHT-28),'详情保留完整文本与来源',font=small,fill='#8194a3')
 im.save(output)
def from_bridge(packages,out,scenes=None):
 p=read(packages);shots=p.get('shots',[])
 if not shots:raise ValueError('Expected script_bridge shot-packages.json')
 if scenes:
  known={s['director_context']['id'] for s in shots}
  if not set(scenes)<=known:raise ValueError('Requested scene is not in the package')
  shots=[s for s in shots if s['director_context']['id'] in scenes]
 if len(shots)>20:raise ValueError('Select --scenes or use project mode; a detailed board holds at most 20 six-card shots')
 groups={};nodes=[];edges=[]
 stages=[{'id':x,'title':y} for x,y in [('source','原文与作用'),('reference','参考与身份'),('prompt','画面与台词'),('media','候选素材'),('review','审看与修复'),('edit','剪辑与交付')]]
 for i,s in enumerate(shots):
  jid=s['id'];scene=s['director_context'];gid=scene['id'];groups.setdefault(gid,{'id':gid,'title':gid+' · '+scene['situation'][:40]});missing=s['visual_conditions'].get('missing_conditions',[])
  cards=[('source','原文 / '+jid,s['shot_function']['purpose'], '\n\n'.join(b['anchor']+'：'+b['quote'] for b in s['source_beats'])) ,('reference','参考 / '+jid,'待补：'+', '.join(missing) if missing else '源包声明已绑定参考；本卡记录条件，实际文件需显式关联。',json.dumps(s['visual_conditions'],ensure_ascii=False,indent=2)),('prompt','提示词 / '+jid,s['visible_prompt'][:65]+'…',s['visible_prompt']+'\n\n对白：\n'+json.dumps(s['speech_track'],ensure_ascii=False,indent=2)),('media','素材 / '+jid,'尚未关联真实take；不将提示词当成已生成素材。','在选片记录中填写实际路径、版本和审看意见，再关联此卡。'),('review','检查 / '+jid,s['editorial_policy']['priority'],s['shot_function']['fallback']+'\n\n'+json.dumps(s['shot_function']['protected_windows'],ensure_ascii=False,indent=2)),('edit','剪辑 / '+jid,s['shot_function']['cut_trigger'],json.dumps(s['editorial_policy'],ensure_ascii=False,indent=2))]
  for stage,title,summary,details in cards:nodes.append({'id':jid+'__'+stage,'group':gid,'stage':stage,'order':i,'title':title,'summary':summary,'details':details,'status':'planned' if stage in ('reference','media') else 'draft'})
  for a,b in zip(stages,stages[1:]):edges.append({'id':jid+'__'+a['id']+'_'+b['id'],'from':jid+'__'+a['id'],'to':jid+'__'+b['id'],'label':'支撑下一步'})
 d={'version':'1.8.0','title':'制作素材总览','source_packages_sha256':digest(packages),'groups':list(groups.values()),'stages':stages,'nodes':nodes,'edges':edges};safe_write(out,d);return {'output':str(out),'cards':len(nodes),'media_generated':False}
def project(packages,out,font=None):
 data=read(packages);shots=data.get('shots',[])
 if not shots:raise ValueError('Expected authored shot packages')
 index(shots,'shots');out=Path(out)
 if out.exists():raise ValueError('Choose a fresh project-board directory')
 fresh(out/'manifest.json');scenes={}
 for shot in shots:scenes.setdefault(shot['director_context']['id'],[]).append(shot)
 overview=[];pages=[];relations=[];markdown=['# 全片素材导航','按场景和镜头顺序进入分板；详细画布每页最多8镜，避免把整部长片压在一张巨图中。']
 for sid,items in scenes.items():
  for offset in range(0,len(items),8):
   number=len(pages)+1;key=f'page-{number:03}';subset=items[offset:offset+8];page_root=out/'boards'/key;page_root.mkdir(parents=True);part=page_root/'planning-snapshot.json';safe_write(part,{'source_packages_sha256':digest(packages),'shots':subset,'scope':'Planning cards only; reference path strings are source-package metadata, not relocated generation inputs'});spec=page_root/'spec.json';from_bridge(part,spec);bundle=page_root/'board';export_bundle(spec,bundle,font=font);rel=(bundle/'board.canvas').relative_to(out).as_posix();label=sid+f' · 镜头 {offset+1}—{offset+len(subset)}';pages.append({'id':key,'scene':sid,'jobs':[s['id'] for s in subset],'canvas':rel,'index':(bundle/'index.md').relative_to(out).as_posix()})
   overview.append({'id':key,'type':'text','x':60+((number-1)%3)*500,'y':180+((number-1)//3)*260,'width':400,'height':200,'text':'## '+label+'\n\n[打开详细画布]('+rel+')\n\n[文字目录]('+pages[-1]['index']+')\n\n'+', '.join(pages[-1]['jobs'])})
   if number>1:relations.append({'id':'next-'+key,'fromNode':pages[-2]['id'],'toNode':key,'label':'阅读顺序','toEnd':'arrow'})
   markdown.append('- ['+label+']('+rel+') · [文字目录]('+pages[-1]['index']+')')
 safe_write(out/'overview.canvas',{'nodes':[{'id':'title','type':'text','x':60,'y':20,'width':1300,'height':100,'text':'# 全片素材导航\n分场景、分镜头段落；参考与生成状态仍需实际核验。'},*overview],'edges':relations});safe_write(out/'pages.json',{'pages':pages,'source_sha256':digest(packages),'all_job_ids':[s['id'] for s in shots],'native_app_tested':False});(out/'index.md').write_bytes(('\n\n'.join(markdown)+'\n').encode('utf-8'));safe_write(out/'manifest.json',{'source_sha256':digest(packages),'files':[{'path':p.relative_to(out).as_posix(),'sha256':digest(p)} for p in sorted(out.rglob('*')) if p.is_file()],'media_generated':False,'native_app_tested':False});return {'output':str(out),'pages':len(pages),'jobs':len(shots),'native_app_tested':False,'media_generated':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['from-bridge','layout','build','project']);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--previous',type=Path);p.add_argument('--font',type=Path);p.add_argument('--scenes',nargs='+');a=p.parse_args()
 try:
  if a.command=='from-bridge':r=from_bridge(a.source,a.out,a.scenes)
  elif a.command=='project':r=project(a.source,a.out,a.font)
  elif a.command=='layout':r=layout(a.source,a.previous);safe_write(a.out,r)
  else:r=export_bundle(a.source,a.out,a.previous,a.font)
  print(json.dumps(r if a.command!='layout' else {'cards':len(r['cards']),'warnings':r['warnings']},ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
