#!/usr/bin/env python3
"""Conform one source's SRT through retained picture ranges; no invented words or speech alignment."""
from pathlib import Path
import argparse,json,math,re,sys
from fractions import Fraction
from creative_tools import read,safe_write
from delivery_utils import fresh,digest
from edit_decisions import validate
from subtitle_tools import check_srt,parse_time,stamp
def conform(edit_path,srt_path,source_id):
 d=read(edit_path);r=validate(edit_path,False)
 if source_id not in d['sources'] or d['sources'][source_id]['kind']!='video':raise ValueError('Choose a video source ID whose original timeline matches this SRT')
 text=Path(srt_path).read_text(encoding='utf-8-sig');quality=check_srt(text)
 if not quality['valid']:raise ValueError('Source SRT invalid: '+'; '.join(quality['errors']))
 fps=r['fps'];cues=[];warnings=[];events=[];seen=set()
 for block in re.split(r'\n\s*\n',text.strip()):
  lines=block.strip().splitlines();a,b=(parse_time(t) for t in lines[1].split(' --> '));cues.append((int(lines[0]),Fraction(str(a))*fps,Fraction(str(b))*fps,'\n'.join(lines[2:])))
 for cut in r['picture']:
  if cut['source']!=source_id:continue
  for n,start,end,words in cues:
   a=max(start,cut['in_frame']);b=min(end,cut['out_frame'])
   if b<=a:continue
   first=math.ceil(a);last=math.floor(b)
   if last<=first:warnings.append(f'Cue {n}: sub-frame retained fragment omitted');continue
   first+=cut['timeline_in_frame']-cut['in_frame'];last+=cut['timeline_in_frame']-cut['in_frame'];trimmed=a!=start or b!=end
   if trimmed:warnings.append(f'Cue {n} intersects a cut; unchanged wording requires manual review against retained speech')
   events.append({'original_cue':n,'cut_id':cut['id'],'in_frame':first,'out_frame':last,'text':words,'trimmed':trimmed});seen.add(n)
 events.sort(key=lambda x:(x['in_frame'],x['out_frame'],x['original_cue']))
 result='\n'.join(f'{i}\n{stamp(c["in_frame"]/fps)} --> {stamp(c["out_frame"]/fps)}\n{c["text"]}\n' for i,c in enumerate(events,1))
 dropped=[c[0] for c in cues if c[0] not in seen]
 return result,{'edit_sha256':digest(edit_path),'source_srt_sha256':digest(srt_path),'source_id':source_id,'fps':fps,'events':events,'dropped_original_cues':dropped,'warnings':warnings+quality['warnings'],'status':'timing-conformed; review cut-word boundaries' if events else 'no-retained-cues; no SRT produced','limits':'Maps one source SRT through picture cuts only. J/L audio cues, replacement dialogue, speed changes and semantic word timing require separate alignment.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('edit',type=Path);p.add_argument('srt',type=Path);p.add_argument('--source',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  text,r=conform(a.edit,a.srt,a.source);out=fresh(a.out,'.srt');report=fresh(out.with_suffix('.conform.json'))
  if text:out.write_text(text,encoding='utf-8-sig')
  safe_write(report,r);print(json.dumps(r,ensure_ascii=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
