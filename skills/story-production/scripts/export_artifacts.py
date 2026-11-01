#!/usr/bin/env python3
"""Export authored production packages to readable PDFs (requires reportlab)."""
from __future__ import annotations
import argparse,html,json,os,sys,hashlib
from pathlib import Path

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def export(folder: Path,font_path: str | None=None) -> list[Path]:
    try:
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,KeepTogether,HRFlowable
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.pagesizes import A4,landscape
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError as exc:raise RuntimeError('Install reportlab for PDF export. Core Markdown/HTML/CSV outputs remain usable.') from exc
    folder=folder.resolve();names=['shot-plan.json','novel-plan.json','season-plan.json'];found=next((folder/n for n in names if (folder/n).is_file()),None)
    if not found:raise ValueError('No shot-plan.json, novel-plan.json or season-plan.json in output directory')
    data=read(found);chinese=any('\u4e00'<=c<='\u9fff' for c in json.dumps(data,ensure_ascii=False))
    candidates=[font_path,os.environ.get('STORY_PRODUCTION_FONT'),os.path.join(os.environ.get('WINDIR','C:/Windows'),'Fonts','simsun.ttc'),'/System/Library/Fonts/STHeiti Light.ttc','/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc']
    font=next((p for p in candidates if p and Path(p).is_file()),None)
    family='Helvetica'
    if font:
        try:pdfmetrics.registerFont(TTFont('StoryFont',font,subfontIndex=0));family='StoryFont'
        except Exception as exc:raise ValueError('Font is not a supported TrueType font. Supply a licensed CJK TTF/TTC with --font. '+str(exc)) from exc
    elif chinese:raise ValueError('No Chinese font found. Supply --font PATH to a licensed CJK TTF/TTC; refusing missing-glyph PDF.')
    styles={
        'title':ParagraphStyle('title',fontName=family,fontSize=26,leading=36,spaceAfter=22),
        'head':ParagraphStyle('head',fontName=family,fontSize=14,leading=22,spaceBefore=12,spaceAfter=10,keepWithNext=True,wordWrap='CJK'),
        'body':ParagraphStyle('body',fontName=family,fontSize=11,leading=18,spaceAfter=8,wordWrap='CJK',allowWidows=0,allowOrphans=0),
        'dialogue':ParagraphStyle('dialogue',fontName=family,fontSize=11,leading=18,spaceAfter=9,leftIndent=40,rightIndent=32,wordWrap='CJK'),
        'small':ParagraphStyle('small',fontName=family,fontSize=9.5,leading=15,spaceAfter=5,wordWrap='CJK'),
    }
    def P(s,style='body'):return Paragraph(html.escape(str(s)).replace('\n','<br/>'),styles[style])
    def footer(canvas,doc):
        w,h=doc.pagesize;canvas.setFont(family,8);canvas.setFillColorRGB(.35,.35,.35);canvas.drawRightString(w-40,23,str(doc.page))
    def save(name,flow,wide=False):
        target=folder/name
        if target.is_symlink():raise ValueError('Refusing symlink output: '+name)
        doc=SimpleDocTemplate(str(target),pagesize=landscape(A4) if wide else A4,leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=40,title=title,author='Story production development draft')
        doc.build(flow,onFirstPage=footer,onLaterPages=footer);return target
    paths=[]
    if found.name=='novel-plan.json':
        title=data['title'];flow=[P(title,'title'),P('完整章节创作稿；统计与编辑判断分开。'),PageBreak()]
        for c in data['chapters']:
            flow.append(P(f"第{c['n']}章　{c['title']}",'head'))
            flow.extend(P(p) for p in c['body'].split('\n') if p.strip())
        paths.append(save('novel-book.pdf',flow))
    elif found.name=='season-plan.json':
        title=data['title'];flow=[P(title,'title'),P(data['logline']),P(data['synopsis']),P(data.get('season_arc',''))]
        for ep in data['episodes']:
            flow.extend([P(f"第{ep['n']}集　{ep['title']}",'head'),P(ep['summary'])])
        paths.append(save('season-guide.pdf',flow))
        for ep in data['episodes']:paths+=export(folder/'episodes'/f"E{ep['n']:03}",font_path)
    else:
        meta=data['meta'];title=meta['title'];shots=data['shots'];scenes=data['scenes'];by={s['scene']:[] for s in scenes}
        for s in shots:by[s['scene']].append(s)
        flow=[P(title,'title'),P('完整电影/单集剧本 · 创作稿'),P(meta.get('logline','')),P('时码为预剪辑设计，未证明配音、动态预演或锁片已完成。'),PageBreak()]
        for sc in scenes:
            flow.append(P(f"{sc['scene']:02}　{sc['heading']}",'head'))
            for s in by[sc['scene']]:
                flow.append(P(s['picture']))
                for d in s['dialogue']:flow.append(P(d['speaker']+'：'+d['text'],'dialogue'))
        paths.append(save('screenplay.pdf',flow))
        flow=[P(title+' · 全片分镜','title'),P(f"{len(scenes)}场 / {len(shots)}镜 / {meta['fps']}fps / 正片设计{meta['story_seconds']}秒"),P('出点不含该帧。首尾帧为文字设计，未生成图像；完整生成提示词见JSON和工作台。'),PageBreak()]
        for sc in scenes:
            flow.append(P(f"{sc['scene']:02}　{sc['heading']}",'head'))
            for key,label in [('intent','目的'),('space','空间'),('axis','轴线'),('light','灯光'),('continuity','连续')]:flow.append(P(label+'：'+str(sc.get(key,'')),'small'))
            for s in by[sc['scene']]:
                block=[P(f"{s['id']}　{s['in_tc']} → {s['out_tc_exclusive']}　{s['duration_sec']}秒　{s['size']} / {s['lens_mm_equiv']}mm / {s['camera']}",'head'),P(s['picture'],'small')]
                block+=[P(d['speaker']+'：'+d['text'],'small') for d in s['dialogue']]
                block += [P('首：'+s['first_anchor']+'\n尾：'+s['last_anchor'],'small'),P('声音：'+s['sound']+'\n剪辑：'+s['transition'],'small'),P('连续与制作：'+s['special'],'small'),HRFlowable(width='100%',thickness=.4,color='#bbbbbb')]
                flow.append(KeepTogether(block))
        paths.append(save('storyboard.pdf',flow,True))
    dependencies={found.relative_to(folder).as_posix():hashlib.sha256(found.read_bytes()).hexdigest()}
    if found.name=='season-plan.json':
        for ep in data['episodes']:
            dep=folder/'episodes'/f"E{ep['n']:03}"/'shot-plan.json';dependencies[dep.relative_to(folder).as_posix()]=hashlib.sha256(dep.read_bytes()).hexdigest()
    receipt={'exporter':'story-production-pdf','source_dependencies':dependencies,'files':[{'path':p.relative_to(folder).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}
    (folder/'pdf-export.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return paths

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('--font');args=p.parse_args()
    try:
        files=export(args.output,args.font);print(json.dumps({'pdfs':[str(f) for f in files],'status':'exported; render and visually verify before delivery'},ensure_ascii=False));return 0
    except (RuntimeError,ValueError,OSError) as exc:print('Error: '+str(exc),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
