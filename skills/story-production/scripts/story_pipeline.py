#!/usr/bin/env python3
"""Validate and export authored novels and episodic series; no text/media generation API."""
from __future__ import annotations
import argparse, csv, hashlib, html, json, re, sys
from pathlib import Path
from typing import Any

def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict): raise ValueError('Input must be a JSON object')
    return value

def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def safe_csv(value: Any) -> Any:
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')): return "'" + value
    return value

def write_csv(path: Path, header: list, rows: list) -> None:
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream); writer.writerow(header)
        writer.writerows([[safe_csv(v) for v in row] for row in rows])

def contained(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative.strip(): raise ValueError('Source path is empty')
    value = Path(relative)
    if value.is_absolute() or re.match(r'^[A-Za-z]:', relative): raise ValueError('Use a project-relative source path')
    result = (root / value).resolve()
    if not result.is_relative_to(root.resolve()): raise ValueError('Source path escapes project directory')
    return result

def content_count(body: str) -> dict:
    return {'cjk_characters': len(re.findall(r'[\u4e00-\u9fff]', body)),
            'latin_words': len(re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", body)), 'characters': len(body)}

def validate(data: dict, source: Path) -> dict:
    errors, warnings = [], []
    kind = data.get('kind')
    if kind not in ('novel', 'series'): errors.append('kind must be novel or series')
    for key in ('title', 'slug', 'theme', 'logline', 'synopsis'):
        if not isinstance(data.get(key), str) or not data[key].strip(): errors.append(f'{key} is required')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', str(data.get('slug', ''))): errors.append('slug must be lowercase letters, digits and hyphens')
    if data.get('authoring_status') != 'complete': errors.append('authoring_status must be complete before final export')
    project = data.get('project', {})
    if not isinstance(project, dict): errors.append('project must be an object'); project = {}
    asset_maps = {}
    for category in ('characters', 'props', 'locations'):
        entries = data.get(category, [])
        if not isinstance(entries, list): errors.append(f'{category} must be a list'); entries = []
        mapping = {}
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or not entry.get('name'):
                errors.append(f'{category} entry requires id and name'); continue
            if entry['id'] in mapping or any(entry['id'] in m for m in asset_maps.values()): errors.append('Duplicate asset ID: ' + entry['id'])
            mapping[entry['id']] = entry
        asset_maps[category] = mapping
    if not isinstance(data.get('world_rules'), list): errors.append('world_rules must be a list')
    if not isinstance(data.get('continuity_audit'), list): errors.append('continuity_audit must be a list')
    result = {'kind': kind, 'errors': errors, 'warnings': warnings, 'counts': {}}
    if kind == 'novel':
        chapters = data.get('chapters', [])
        if not isinstance(chapters, list): errors.append('chapters must be a list'); chapters = []
        planned = project.get('planned_chapters')
        if not isinstance(planned, int) or isinstance(planned, bool) or planned < 1: errors.append('project.planned_chapters must be a positive integer')
        if len(chapters) != planned: errors.append(f'Chapter coverage: authored {len(chapters)}, planned {planned}')
        combined = []
        for index, chapter in enumerate(chapters, 1):
            prefix = f'Chapter {index}'
            if not isinstance(chapter, dict): errors.append(prefix + ' must be an object'); continue
            if chapter.get('n') != index or isinstance(chapter.get('n'), bool): errors.append(prefix + ' number must be sequential')
            for key in ('title', 'story_time', 'pov', 'goal', 'body', 'ending_hook'):
                if not isinstance(chapter.get(key), str) or not chapter[key].strip(): errors.append(prefix + f' missing {key}')
            body = chapter.get('body', '')
            if isinstance(body, str):
                combined.append(body)
                if re.search(r'待补|待续写|正文略|TODO|\[INSERT', body, re.I): errors.append(prefix + ' contains unfinished authoring placeholder')
                if len(body) < 200: warnings.append(prefix + ' is very brief; confirm it is prose, not an outline')
            for key, category in [('character_ids', 'characters'), ('prop_ids', 'props'), ('location_ids', 'locations')]:
                ids = chapter.get(key, [])
                if not isinstance(ids, list): errors.append(prefix + f' {key} must be a list'); continue
                for asset_id in ids:
                    if asset_id not in asset_maps[category]: errors.append(prefix + f' unknown {category} ID {asset_id}')
        result['counts'] = {'chapters': len(chapters), 'planned_chapters': planned, **content_count('\n'.join(combined))}
        target = project.get('target_words')
        if isinstance(target, (float, int)) and target > 0:
            actual = result['counts']['cjk_characters'] + result['counts']['latin_words']
            if actual < target * .7: warnings.append(f'Authored text ({actual} CJK characters + Latin words) is below 70% of target {target}; review scope before calling the novel complete')
    elif kind == 'series':
        import film_pipeline
        episodes = data.get('episodes', [])
        if not isinstance(episodes, list): errors.append('episodes must be a list'); episodes = []
        planned = project.get('planned_episodes')
        if not isinstance(planned, int) or isinstance(planned, bool) or planned < 1: errors.append('project.planned_episodes must be positive integer')
        if len(episodes) != planned: errors.append(f'Episode coverage: authored {len(episodes)}, planned {planned}')
        episode_data = {}; source_paths = set(); total_scenes = 0
        for index, episode in enumerate(episodes, 1):
            if not isinstance(episode, dict): errors.append(f'Episode {index} must be an object'); continue
            if episode.get('n') != index or isinstance(episode.get('n'), bool): errors.append(f'Episode {index} number must be sequential')
            if episode.get('status') != 'complete': errors.append(f'Episode {index} is not complete')
            if not episode.get('title') or not episode.get('summary'): errors.append(f'Episode {index} needs title and summary')
            try:
                path = contained(source.parent, episode.get('source'))
                if path in source_paths: errors.append(f'Episode {index} repeats another episode source')
                source_paths.add(path); film = read(path); episode_data[index] = film
                report = film_pipeline.validate_film(film)
                errors.extend(f'Episode {index}: {e}' for e in report.get('errors', []))
                warnings.extend(f'Episode {index}: {w}' for w in report.get('warnings', []))
                total_scenes += len(film.get('scenes', []))
                for category, shared in asset_maps.items():
                    for asset in film.get(category, []):
                        if asset.get('id') not in shared: errors.append(f'Episode {index}: {asset.get("id")} absent from season bible'); continue
                        canonical = shared[asset['id']]
                        for field in {'characters': ('name', 'appearance', 'voice'), 'props': ('name', 'design'), 'locations': ('name', 'geography', 'look')}[category]:
                            if field in canonical and asset.get(field) != canonical[field]: errors.append(f'Episode {index}: shared identity {asset["id"]}.{field} differs from season bible')
                        for stage, clothes in asset.get('costumes', {}).items():
                            if stage not in canonical.get('costumes', {}) or canonical['costumes'][stage] != clothes: errors.append(f'Episode {index}: costume {asset["id"]}.{stage} is absent or inconsistent in bible')
            except (OSError, ValueError, TypeError) as exc: errors.append(f'Episode {index}: {exc}')
        all_assets = {key for mapping in asset_maps.values() for key in mapping}
        states = {}; events = data.get('continuity_events', [])
        for state in data.get('asset_states', []):
            if not isinstance(state, dict) or not state.get('id') or state.get('asset_id') not in all_assets: errors.append('Invalid asset state'); continue
            if state['id'] in states: errors.append('Duplicate state ID: ' + state['id'])
            states[state['id']] = state
        current = {}; previous = (0, 0)
        for event in events:
            if not isinstance(event, dict): errors.append('continuity event must be object'); continue
            episode, scene = event.get('episode'), event.get('scene')
            if not isinstance(episode, int) or not isinstance(scene, int) or isinstance(episode, bool) or isinstance(scene, bool): errors.append('Event episode/scene must be integers'); continue
            at = (episode, scene)
            if at < previous: errors.append('continuity_events must be in story presentation order')
            previous = at
            film = episode_data.get(episode, {})
            if scene < 1 or scene > len(film.get('scenes', [])): errors.append(f'Event references missing E{episode} scene {scene}')
            aid = event.get('asset_id'); begin, end = event.get('from_state'), event.get('to_state')
            if aid not in all_assets: errors.append(f'Event unknown asset {aid}')
            for sid in (begin, end):
                if sid not in states or states[sid].get('asset_id') != aid: errors.append(f'Event invalid state {sid} for {aid}')
            if aid in current and current[aid] != begin: errors.append(f'State jump at E{episode} S{scene}: {aid} expected {current[aid]}, got {begin}')
            current[aid] = end
            if not event.get('reason'): errors.append('Each state transition requires a reason')
        for mapping in data.get('adaptation_map', []):
            if not isinstance(mapping, dict): errors.append('adaptation_map entry must be an object'); continue
            film = episode_data.get(mapping.get('episode'), {})
            for n in mapping.get('scenes', []):
                if not isinstance(n, int) or isinstance(n, bool) or n < 1 or n > len(film.get('scenes', [])): errors.append('Adaptation map references missing scene')
            if not mapping.get('change') or not mapping.get('reason'): errors.append('Adaptation changes require change and reason')
        result['counts'] = {'episodes': len(episodes), 'planned_episodes': planned, 'scenes': total_scenes, 'state_transitions': len(events)}
    result['valid'] = not errors
    return result

STYLE = 'body{font:17px/1.9 system-ui,sans-serif;background:#f4f0e7;color:#203039;max-width:1050px;margin:auto;padding:35px}a{color:#8c4b35}article,section{background:#fffdf8;padding:24px;margin:20px 0;border:1px solid #ddd7ca;border-radius:8px}h1{font-size:34px}pre{white-space:pre-wrap;font:inherit}small{color:#607078}table{border-collapse:collapse;width:100%}td,th{padding:9px;text-align:left;border-bottom:1px solid #ddd}details{margin:10px 0}nav{display:flex;gap:15px;flex-wrap:wrap}'
def page(title: str, body: str) -> str:
    return '<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+STYLE+'</style><h1>'+html.escape(title)+'</h1>'+body+'</html>'

def manifest(out: Path, source: Path, kind: str) -> None:
    data=read(source)
    names={'index.html','validation.json','continuity.csv'}
    if kind=='novel':
        names.update(['novel-book.md','novel-plan.json','chapters.csv'])
        names.update(f"chapters/C{c['n']:03}.md" for c in data['chapters'])
    else:
        names.update(['season-guide.md','season-plan.json','episodes.csv','asset-reuse.csv','adaptation.csv'])
        for ep in data['episodes']:
            epdir=out/'episodes'/f"E{ep['n']:03}";prefix=epdir.relative_to(out).as_posix()+'/'
            epmanifest=read(epdir/'manifest.json');names.add(prefix+'manifest.json')
            names.update(prefix+(r['path'] if isinstance(r,dict) else r) for r in epmanifest['files'])
    records = [{'path': name, 'bytes': (out/name).stat().st_size, 'sha256': hashlib.sha256((out/name).read_bytes()).hexdigest()} for name in sorted(names)]
    write_json(out/'manifest.json', {'generated_by':'story-production','kind': kind, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'files': records, 'media_generated': False})

def build(source: Path, out: Path, overwrite: bool = False) -> dict:
    import film_pipeline
    for part in [out,*out.parents]:
        if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Refusing symlink/junction output path')
    source = source.resolve(); out = out.resolve(); data = read(source); report = validate(data, source)
    if not report['valid']: raise ValueError('\n'.join(report['errors']))
    if source.is_relative_to(out): raise ValueError('Output directory must not contain source manuscript')
    if out.exists() and any(out.iterdir()) and not overwrite: raise ValueError('Output is not empty; use --overwrite for an intentional rebuild')
    if out.exists():
        for child in out.rglob('*'):
            if child.is_symlink() or (hasattr(child,'is_junction') and child.is_junction()):raise ValueError('Refusing output containing links')
    out.mkdir(parents=True, exist_ok=True)
    kind = data['kind']; esc = html.escape
    write_json(out/'validation.json', report)
    if kind == 'novel':
        folder = out/'chapters'; folder.mkdir(exist_ok=True)
        contents = [f"# {data['title']}\n\n{data['logline']}\n\n小说正文；统计来自实际章节，不等同出版定稿。\n"]
        body = '<p>'+esc(data['logline'])+'</p><nav><a href="novel-book.md">全书 Markdown</a><a href="novel-plan.json">章节与设定 JSON</a><a href="chapters.csv">章节表 CSV</a></nav>'
        body += '<p><small>所有章节正文如下。改编时保留本书作为源稿，另建电影或剧集，不用镜头说明替代小说文体。</small></p>'
        rows = []
        for chapter in data['chapters']:
            chunk = f"## 第{chapter['n']}章　{chapter['title']}\n\n{chapter['body']}\n"
            contents.append(chunk); name = f"C{chapter['n']:03}.md"; (folder/name).write_text(chunk,encoding='utf-8')
            body += '<article id="C'+str(chapter['n'])+'"><h2>'+esc(f"第{chapter['n']}章　{chapter['title']}")+'</h2>'+''.join('<p>'+esc(p)+'</p>' for p in chapter['body'].split('\n') if p.strip())+'</article>'
            count = content_count(chapter['body']); rows.append([chapter['n'],chapter['title'],chapter['story_time'],chapter['pov'],chapter['goal'],chapter['ending_hook'],count['cjk_characters'],count['latin_words']])
        (out/'novel-book.md').write_text('\n'.join(contents), encoding='utf-8'); write_json(out/'novel-plan.json',data)
        write_csv(out/'chapters.csv',['章节','标题','故事时间','视角','本章目标','章尾承接','中文字符','拉丁词数'],rows)
    else:
        import film_pipeline
        contents = [f"# {data['title']}\n\n{data['logline']}\n\n{data['synopsis']}\n\n## 整季弧线\n\n{data.get('season_arc','')}\n"]
        body='<p>'+esc(data['logline'])+'</p><nav><a href="season-guide.md">整季总纲</a><a href="season-plan.json">整季数据</a><a href="continuity.csv">跨集连续性</a><a href="asset-reuse.csv">资产复用</a></nav><p><small>逐集时码从零起。全部时长为预剪辑设计；未生成配音或视频。</small></p>'
        rows=[]; use={}
        for episode in data['episodes']:
            n=episode['n']; ep_path=contained(source.parent, episode['source']); ep_out=out/'episodes'/f'E{n:03}'
            film_pipeline.build_package(ep_path,ep_out,overwrite=overwrite)
            compiled=read(ep_out/'shot-plan.json'); m=compiled['meta']
            rows.append([n,episode['title'],m['story_seconds'],len(compiled['scenes']),len(compiled['shots']),episode['summary']])
            body+='<section><h2>'+esc(f"第{n}集　{episode['title']}")+'</h2><p>'+esc(episode['summary'])+'</p><a href="episodes/E'+f'{n:03}'+'/index.html">打开完整剧本与分镜 →</a></section>'
            contents.append(f"\n## 第{n}集　{episode['title']}\n\n{episode['summary']}\n\n设计时长 {m['story_seconds']} 秒；{len(compiled['shots'])} 镜。\n")
            for shot in compiled['shots']:
                for aid in shot['asset_ids']:use.setdefault(aid,set()).add(n)
        (out/'season-guide.md').write_text('\n'.join(contents),encoding='utf-8'); write_json(out/'season-plan.json',data)
        write_csv(out/'episodes.csv',['集数','标题','正片设计秒','场数','镜头数','本集完整剧情'],rows)
        write_csv(out/'asset-reuse.csv',['资产ID','出现集数','复用规则'],[[a,','.join(map(str,sorted(ns))),'固定身份与外观，衣装按整季设定；状态变化查连续性表'] for a,ns in sorted(use.items())])
        write_csv(out/'adaptation.csv',['源章节','集','场','改动','原因'],[[','.join(map(str,m.get('source_chapters',[]))),m.get('episode'),','.join(map(str,m.get('scenes',[]))),m.get('change'),m.get('reason')] for m in data.get('adaptation_map',[])])
    events=data.get('continuity_events',[]) if kind=='series' else data.get('continuity_audit',[])
    write_csv(out/'continuity.csv',['记录','具体内容'],[[i,json.dumps(e,ensure_ascii=False)] for i,e in enumerate(events,1)])
    (out/'index.html').write_text(page(data['title'],body),encoding='utf-8');manifest(out,source,kind)
    return report

def initialize(mode: str, theme: str, project: Path, count: int | None) -> Path:
    if project.exists() and any(project.iterdir()): raise ValueError('Project directory is not empty')
    project.mkdir(parents=True,exist_ok=True)
    number=count if count is not None else (24 if mode=='novel' else 12)
    if number<1:raise ValueError('--count must be positive')
    data={'kind':mode,'slug':'new-story','title':'','theme':theme,'logline':'','synopsis':'','authoring_status':'incomplete','world_rules':[], 'characters':[], 'locations':[], 'props':[], 'structure':[], 'continuity_audit':[]}
    if mode=='novel':data.update(project={'planned_chapters':number,'target_words':number*3000,'language':'zh-CN'},chapters=[])
    else:data.update(project={'planned_episodes':number,'episode_minutes':40,'language':'zh-CN'},season_arc='',asset_states=[],continuity_events=[],episodes=[],adaptation_map=[])
    target=project/(mode+'.json');write_json(target,data)
    write_json(project/'checkpoint.json',{'mode':mode,'theme':theme,'stage':'brief','planned_units':number,'completed_units':[],'next_action':'Write the story bible and complete prose or episode scripts; init creates no story content','media_generated':False})
    return target

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__); commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('init');p.add_argument('--mode',choices=['novel','series'],required=True);p.add_argument('--theme',required=True);p.add_argument('--project',type=Path,required=True);p.add_argument('--count',type=int)
    p=commands.add_parser('validate');p.add_argument('input',type=Path);p.add_argument('--report',type=Path)
    p=commands.add_parser('build');p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--overwrite',action='store_true')
    args=parser.parse_args(argv)
    try:
        if args.command=='init': print(initialize(args.mode,args.theme,args.project,args.count));return 0
        if args.command=='validate':
            report=validate(read(args.input),args.input.resolve())
            if args.report: args.report.parent.mkdir(parents=True,exist_ok=True);write_json(args.report,report)
            print(json.dumps(report,ensure_ascii=False));return 0 if report['valid'] else 1
        report=build(args.input,args.out,args.overwrite);print(json.dumps(report,ensure_ascii=False));return 0
    except (ValueError,OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
        print('Error: '+str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
