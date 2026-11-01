#!/usr/bin/env python3
"""Local contact sheets and PCM WAV measurements; no enhancement or perceptual quality claims."""
from pathlib import Path
import argparse,json,math,sys,wave
from creative_tools import safe_write
from delivery_utils import fresh,digest,finite
def contact_sheet(source,output,samples=8):
 try:import av;from PIL import Image,ImageDraw,ImageOps
 except ImportError as e:raise ValueError('Contact sheets require PyAV and Pillow') from e
 from media_qc import inspect_video
 if not isinstance(samples,int) or isinstance(samples,bool) or not 2<=samples<=40:raise ValueError('samples must be 2..40')
 info=inspect_video(source,max_frames=0)
 if not info['valid']:raise ValueError('Cannot sample invalid media: '+'; '.join(info['errors']))
 total=info['sample']['decoded_frames'];indices=sorted({round(i*(total-1)/(samples-1)) for i in range(samples)})
 out=fresh(output,'.png');report_path=fresh(out.with_suffix('.frames.json'));width,height=320,180;cols=min(4,len(indices));rows=math.ceil(len(indices)/cols);canvas=Image.new('RGB',(cols*width,rows*(height+26)),(20,23,29));draw=ImageDraw.Draw(canvas);selected=[]
 with av.open(str(source)) as container:
  for n,frame in enumerate(container.decode(video=0)):
   if n not in indices:continue
   i=len(selected);x=(i%cols)*width;y=(i//cols)*(height+26);im=ImageOps.contain(frame.to_image(),(width,height));canvas.paste(im,(x+(width-im.width)//2,y+(height-im.height)//2))
   seconds=float(frame.pts*frame.time_base) if frame.pts is not None and frame.time_base is not None else None
   label=f'frame {n} | {seconds:.3f}s' if seconds is not None else f'frame {n} | timestamp unknown';draw.text((x+7,y+height+6),label,fill=(230,230,230));selected.append({'frame':n,'timestamp_seconds':seconds})
 if len(selected)!=len(indices):raise ValueError('Decoded media changed or samples were missing')
 canvas.save(out);r={'source_name':Path(source).name,'source_sha256':info['sha256'],'decoded_frames':total,'selected_frames':selected,'output':out.name,'limits':'Evenly sampled actual frames for manual review; does not validate motion between frames, audio or realism.'};safe_write(report_path,r);return r
def audio_qc(source,target_lufs=None):
 try:import numpy as np;import pyloudnorm as pyln
 except ImportError as e:raise ValueError('Audio measurement requires NumPy and pyloudnorm') from e
 if target_lufs is not None:finite(target_lufs,'target_lufs')
 with wave.open(str(source),'rb') as f:
  channels=f.getnchannels();rate=f.getframerate();frames=f.getnframes();width=f.getsampwidth()
  if f.getcomptype()!='NONE' or width!=2 or channels not in (1,2):raise ValueError('This checker accepts PCM16 mono/stereo WAV only; explicitly convert other media first')
  raw=f.readframes(frames)
 if frames==0 or len(raw)!=frames*channels*2:raise ValueError('Empty or truncated PCM data')
 pcm=np.frombuffer(raw,dtype='<i2').reshape(-1,channels);data=pcm.astype(np.float64)/32768.;peak=float(np.max(np.abs(data)));rms=float(np.sqrt(np.mean(data*data)));warnings=[];duration=frames/rate;loudness=None
 if duration>=.4 and peak>0:
  measured=float(pyln.Meter(rate).integrated_loudness(data[:,0] if channels==1 else data))
  if math.isfinite(measured):loudness=measured
  else:warnings.append('Gated loudness is undefined for this signal')
 else:warnings.append('Integrated loudness unavailable: silent signal or shorter than the 400ms gating block')
 clipped=int(np.count_nonzero((pcm==32767)|(pcm==-32768)))
 if clipped:warnings.append('Samples reach a PCM rail; inspect possible clipping before any gain increase')
 gain=target_lufs-loudness if target_lufs is not None and loudness is not None else None
 projected_peak=(20*math.log10(peak)+gain) if gain is not None and peak else None
 if projected_peak is not None and projected_peak>=0:warnings.append('Target gain would reach/exceed 0 dBFS sample peak; do not apply it blindly')
 return {'source_name':Path(source).name,'source_sha256':digest(source),'sample_rate':rate,'channels':channels,'sample_frames':frames,'duration_sec':duration,'sample_peak_dbfs':20*math.log10(peak) if peak else None,'rms_dbfs':20*math.log10(rms) if rms else None,'dc_offset_by_channel':np.mean(data,axis=0).tolist(),'samples_at_pcm_rails':clipped,'integrated_lufs':loudness,'requested_target_lufs':target_lufs,'suggested_gain_db':gain,'projected_sample_peak_dbfs':projected_peak,'warnings':warnings,'audio_modified':False,'limits':'Full PCM sample measurement and BS.1770 integrated loudness; no true-peak oversampling, LRA, surround/channel-layout validation, dialogue intelligibility or music-rights claim.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['contact','audio']);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--samples',type=int,default=8);p.add_argument('--target-lufs',type=float);a=p.parse_args()
 try:
  if a.command=='contact':r=contact_sheet(a.source,a.out,a.samples)
  else:r=audio_qc(a.source,a.target_lufs);safe_write(a.out,r)
  print(json.dumps(r,ensure_ascii=False,allow_nan=False));return 0
 except (ValueError,OSError,KeyError,TypeError,wave.Error) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
