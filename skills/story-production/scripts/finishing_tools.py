#!/usr/bin/env python3
"""Read-only silence/color reports, authored ASC-CDL XML and bounded final-file checks."""
from pathlib import Path
import argparse,array,json,math,sys,wave,xml.etree.ElementTree as ET
from creative_tools import read,safe_write
from delivery_utils import digest,finite,fresh
from media_qc import inspect_video
from edit_decisions import validate
def silence(source,threshold_db=-40,min_sec=.4,window_ms=20):
 finite(threshold_db,'threshold_db');finite(min_sec,'min_sec',.001)
 if not -120<=threshold_db<=0:raise ValueError('threshold must be -120..0 dBFS')
 if not isinstance(window_ms,int) or isinstance(window_ms,bool) or not 1<=window_ms<=100:raise ValueError('window_ms must be 1..100')
 intervals=[];start=None;offset=0;level=10**(threshold_db/20)
 with wave.open(str(source),'rb') as f:
  rate,channels=f.getframerate(),f.getnchannels();total=f.getnframes()
  if f.getsampwidth()!=2 or channels not in (1,2) or f.getcomptype()!='NONE':raise ValueError('Use PCM16 mono/stereo WAV')
  if not total:raise ValueError('Empty WAV has no silence intervals to inspect')
  window=max(1,round(rate*window_ms/1000))
  while raw:=f.readframes(window):
   samples=array.array('h');samples.frombytes(raw)
   if sys.byteorder!='little':samples.byteswap()
   count=len(samples)//channels
   if not count or len(samples)%channels:raise ValueError('Incomplete WAV sample frame')
   quiet=max(math.sqrt(sum((v/32768.)**2 for v in samples[ch::channels])/count) for ch in range(channels))<=level
   if quiet and start is None:start=offset
   if not quiet and start is not None:
    if (offset-start)/rate>=min_sec:intervals.append({'start_sample':start,'end_sample_exclusive':offset,'start_sec':start/rate,'end_sec':offset/rate})
    start=None
   offset+=count
  if offset!=total:raise ValueError('Truncated WAV data')
  if start is not None and (offset-start)/rate>=min_sec:intervals.append({'start_sample':start,'end_sample_exclusive':offset,'start_sec':start/rate,'end_sec':offset/rate})
 return {'source_sha256':digest(source),'sample_rate':rate,'threshold_dbfs':threshold_db,'window_ms':window_ms,'candidates':intervals,'media_modified':False,'limits':'Windowed RMS candidates, not speech recognition. Breaths, reactions, pauses and room tone may be dramatically necessary; no automatic cuts were made.'}
def color_info(source):
 try:import av
 except ImportError as e:raise ValueError('Color metadata inspection needs PyAV') from e
 with av.open(str(source)) as c:
  if not c.streams.video:raise ValueError('No video stream')
  cc=c.streams.video[0].codec_context;tags={k:int(getattr(cc,k,2)) for k in ('color_primaries','color_trc','colorspace','color_range')}
 return {'source_sha256':digest(source),'tags':tags,'hdr_transfer_signaled':tags['color_trc'] in (16,18),'limits':'Header tags are not measured pixel colorimetry. Unknown tags must be resolved from acquisition/workflow records; no grade or color transform applied.'}
def cdl(data,output):
 def triplet(name,positive=False):
  values=data.get(name)
  if not isinstance(values,list) or len(values)!=3:raise ValueError(name+' needs exactly three numbers')
  for v in values:
   finite(v,name)
   if positive and v<=0:raise ValueError(name+' must be positive')
  return ' '.join(format(v,'.12g') for v in values)
 cid=data.get('id')
 if not isinstance(cid,str) or not cid:raise ValueError('CDL id required')
 slope,offset,power=triplet('slope',True),triplet('offset'),triplet('power',True);sat=finite(data.get('saturation'),'saturation',0)
 root=ET.Element('ColorCorrection',{'id':cid});description=ET.SubElement(root,'Description');description.text=data.get('description','Authored CDL values; target color pipeline must be verified');sop=ET.SubElement(root,'SOPNode')
 for key,val in [('Slope',slope),('Offset',offset),('Power',power)]:ET.SubElement(sop,key).text=val
 ET.SubElement(ET.SubElement(root,'SatNode'),'Saturation').text=format(sat,'.12g');out=fresh(output,'.cc');ET.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
 ET.parse(out)
 return {'output':str(out),'applied_to_media':False,'native_editor_import_tested':False,'limits':'Single ASC-CDL correction XML with supplied values; not an OCIO config, 3D LUT, HDR conversion or proof of a matched grade.'}
def final_check(edit,media):
 d=read(edit);r=validate(edit,False);info=inspect_video(media,max_frames=0,expected_fps=r['fps'],expected_frames=r['total_frames'],expected_width=d['width'],expected_height=d['height']);errors=list(info['errors'])
 if bool(info['audio'])!=bool(d['audio']):errors.append('Audio stream presence differs from declared edit cues')
 for stream in info['audio']:
  if stream['sample_rate']!=48000 or stream['channels']!=2:errors.append('Expected 48000 Hz stereo review mix')
 audio_samples=None
 if info['audio']:
  import av
  with av.open(str(media)) as c:audio_samples=sum(frame.samples for frame in c.decode(audio=0))
  expected=r['total_frames']*48000/r['fps']
  if abs(audio_samples-expected)>2048:errors.append('Decoded audio length differs from edit duration beyond AAC padding tolerance')
 return {'valid':not errors,'errors':errors,'warnings':info['warnings'],'edit_sha256':digest(edit),'media':info,'decoded_audio_samples':audio_samples,'audio_length_tolerance_samples':2048,'review_pending':['play every cut boundary','listen to dialogue/music balance and J/L bridges','check actual subtitle/title appearance if separately added','verify final color pipeline in target viewer'],'limits':'Technical review-file check only; does not validate audio content, language, subtitle placement, grading, rights or DCP compliance.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 c=sub.add_parser('silence');c.add_argument('input',type=Path);c.add_argument('--threshold-db',type=float,default=-40);c.add_argument('--min-sec',type=float,default=.4);c.add_argument('--out',type=Path,required=True)
 for name in ('color','cdl'):
  c=sub.add_parser(name);c.add_argument('input',type=Path);c.add_argument('--out',type=Path,required=True)
 c=sub.add_parser('check');c.add_argument('edit',type=Path);c.add_argument('media',type=Path);c.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 try:
  if a.command=='cdl':r=cdl(read(a.input),a.out)
  else:
   r=silence(a.input,a.threshold_db,a.min_sec) if a.command=='silence' else color_info(a.input) if a.command=='color' else final_check(a.edit,a.media);safe_write(a.out,r)
  print(json.dumps(r,ensure_ascii=False));return 0 if r.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError,wave.Error) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
