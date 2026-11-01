#!/usr/bin/env python3
"""Validate SRT and import real ASR segments without treating recognition as authoritative dialogue."""
from __future__ import annotations
import argparse,hashlib,json,math,re,sys
from pathlib import Path
from creative_tools import read,safe_write
TIME=re.compile(r'^(\d{2,}):(\d{2}):(\d{2}),(\d{3})$')
def parse_time(t):
 m=TIME.fullmatch(t.strip())
 if not m:raise ValueError('Invalid SRT time: '+t)
 h,mm,s,ms=map(int,m.groups())
 if mm>=60 or s>=60:raise ValueError('Invalid SRT clock fields')
 return h*3600+mm*60+s+ms/1000
def stamp(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
def check_srt(text,duration=None):
 if duration is not None and (not isinstance(duration,(int,float)) or isinstance(duration,bool) or not math.isfinite(duration) or duration<=0):raise ValueError('duration must be a finite positive number')
 errors=[];warnings=[];previous_end=0;events=[]
 for i,block in enumerate(re.split(r'\n\s*\n',text.strip()),1):
  lines=block.strip().splitlines()
  if len(lines)<3 or lines[0]!=str(i) or ' --> ' not in lines[1]:errors.append(f'Event {i}: invalid sequence or layout');continue
  try:a,b=(parse_time(t) for t in lines[1].split(' --> '))
  except ValueError as e:errors.append(f'Event {i}: {e}');continue
  if b<=a:errors.append(f'Event {i}: nonpositive interval')
  if a<previous_end-.001:warnings.append(f'Event {i}: overlaps previous event; confirm intentional simultaneous dialogue')
  if duration is not None and b>duration+.001:errors.append(f'Event {i}: exceeds media duration')
  body=lines[2:];plain=''.join(body)
  if len(body)>2:warnings.append(f'Event {i}: more than two lines')
  if any(sum(2 if '\u4e00'<=c<='\u9fff' else 1 for c in line)>42 for line in body):warnings.append(f'Event {i}: long display line')
  cjk=len(re.findall(r'[\u4e00-\u9fff]',plain))
  if b>a and cjk/(b-a)>6:warnings.append(f'Event {i}: dense Chinese reading speed')
  if not plain.strip():errors.append(f'Event {i}: empty text')
  events.append({'n':i,'start':a,'end':b,'text':'\n'.join(body)});previous_end=max(previous_end,b)
 if not events:errors.append('No valid subtitle events')
 return {'valid':not errors,'events':len(events),'errors':errors,'warnings':warnings,'limits':'Syntax, timing and readability checks only; not speech recognition, forced alignment or lip-sync verification.'}
def import_segments(data):
 rows=data.get('segments')
 if not isinstance(rows,list) or not rows:raise ValueError('Expected a nonempty segments list')
 blocks=[];previous_end=0
 for i,s in enumerate(rows,1):
  if not isinstance(s,dict):raise ValueError('Segment must be object')
  a,b,text=s.get('start'),s.get('end'),s.get('text')
  if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in (a,b)) or a<0 or b<=a:raise ValueError(f'Segment {i}: invalid time')
  if a<previous_end-.001:raise ValueError('Overlapping ASR segments require manual resolution')
  if not isinstance(text,str) or not text.strip():raise ValueError('Segment text is empty')
  # No invented word timing: preserve each supplied segment's actual interval.
  text=text.strip().replace('\r','');text=re.sub(r'\n\s*\n','\n',text)
  blocks.append(f'{i}\n{stamp(a)} --> {stamp(b)}\n{text}\n');previous_end=b
 result='\n'.join(blocks);report=check_srt(result)
 report.update(source_kind='ASR-supplied-segments',dialogue_authority='recognition hypothesis; compare against approved script and actual audio',word_timing_invented=False)
 return result,report
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 c=sub.add_parser('check');c.add_argument('srt',type=Path);c.add_argument('--duration',type=float);c.add_argument('--report',type=Path)
 c=sub.add_parser('import-asr');c.add_argument('input',type=Path);c.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 try:
  if a.command=='check':
   r=check_srt(a.srt.read_text(encoding='utf-8-sig'),a.duration)
   if a.report:safe_write(a.report,r)
  else:
   if a.out.suffix.lower()!='.srt':raise ValueError('Output must be .srt')
   for part in [a.out,*a.out.parents]:
    if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Refusing symlink/junction output')
   report_path=a.out.with_suffix('.import.json')
   if a.out.exists() or report_path.exists():raise ValueError('Output exists; choose a versioned filename')
   text,r=import_segments(read(a.input));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text,encoding='utf-8-sig');r['source_sha256']=hashlib.sha256(a.input.read_bytes()).hexdigest();safe_write(report_path,r)
  print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['valid'] else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
