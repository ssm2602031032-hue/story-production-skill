#!/usr/bin/env python3
"""Measure image-plane motion in declared ROIs and export native-pixel detail crops. Does not infer vehicle ground speed or realism."""
from pathlib import Path
import argparse,json,math,sys
from creative_tools import read,safe_write
from delivery_utils import digest,fresh,finite
def roi_box(values,width,height):
 if not isinstance(values,list) or len(values)!=4:raise ValueError('ROI must be normalized [x,y,width,height]')
 x,y,w,h=[finite(v,'ROI',0) for v in values]
 if w<=0 or h<=0 or x+w>1.000001 or y+h>1.000001:raise ValueError('ROI must fit inside the image')
 a,b,c,d=round(x*width),round(y*height),round((x+w)*width),round((y+h)*height)
 if c-a<3 or d-b<3:raise ValueError('ROI is too small after analysis scaling')
 return a,b,c,d
def measure(source,regions,start_frame=0,max_frames=121,analysis_width=320):
 try:import av;import cv2;import numpy as np
 except ImportError as e:raise ValueError('Motion measurement needs PyAV, OpenCV and NumPy') from e
 if not isinstance(regions,dict) or not regions:raise ValueError('Provide named manual ROIs; use full_frame=[0,0,1,1] only for a whole-frame measurement')
 if any(not isinstance(v,int) or isinstance(v,bool) for v in (start_frame,max_frames,analysis_width)) or start_frame<0 or not 2<=max_frames<=1000 or not 64<=analysis_width<=1920:raise ValueError('Invalid bounded frame/analysis settings')
 previous=None;previous_time=None;frames=0;rows=[];warning=[];boxes={};source_size=None
 with av.open(str(source)) as container:
  if not container.streams.video:raise ValueError('No video stream')
  for n,frame in enumerate(container.decode(video=0)):
   if n<start_frame:continue
   if frames>=max_frames:break
   if frame.pts is None or frame.time_base is None:raise ValueError('Actual frame timestamps required')
   timestamp=float(frame.pts*frame.time_base);gray=frame.to_ndarray(format='gray');sh,sw=gray.shape;aw=min(sw,analysis_width);ah=max(1,round(sh*aw/sw));gray=cv2.resize(gray,(aw,ah),interpolation=cv2.INTER_AREA)
   if not boxes:boxes={key:roi_box(values,aw,ah) for key,values in regions.items()};source_size=[sw,sh]
   if previous is not None:
    dt=timestamp-previous_time
    if dt<=0:raise ValueError('Non-increasing timestamps')
    if gray.shape!=previous.shape:raise ValueError('Frame geometry changes during the sample')
    flow=cv2.calcOpticalFlowFarneback(previous,gray,None,.5,3,15,3,5,1.2,0);stats={}
    for key,(x0,y0,x1,y1) in boxes.items():
     f=flow[y0:y1,x0:x1];magnitude=np.linalg.norm(f,axis=2);stats[key]={'median_frame_widths_per_sec':float(np.median(magnitude)/dt/aw),'p90_frame_widths_per_sec':float(np.percentile(magnitude,90)/dt/aw),'median_dx_frame_widths_per_sec':float(np.median(f[:,:,0])/dt/aw),'median_dy_frame_heights_per_sec':float(np.median(f[:,:,1])/dt/ah),'gray_std':float(np.std(previous[y0:y1,x0:x1]))}
    rows.append({'from_frame':n-1,'to_frame':n,'dt_sec':dt,'regions':stats})
   previous=gray;previous_time=timestamp;frames+=1
 if len(rows)<1:raise ValueError('Not enough decoded frames in the selected range')
 summary={key:{'median_frame_widths_per_sec':float(np.median([r['regions'][key]['median_frame_widths_per_sec'] for r in rows])),'p90_frame_widths_per_sec':float(np.median([r['regions'][key]['p90_frame_widths_per_sec'] for r in rows])),'median_dx_frame_widths_per_sec':float(np.median([r['regions'][key]['median_dx_frame_widths_per_sec'] for r in rows]))} for key in regions}
 for key in regions:
  if np.median([r['regions'][key]['gray_std'] for r in rows])<8:warning.append(key+': low image texture; optical flow may be unreliable')
 return {'source_sha256':digest(source),'source_size':source_size,'analysis_size':[aw,ah],'start_frame':start_frame,'decoded_frames':frames,'last_timestamp_sec':previous_time,'method':'OpenCV Farneback dense optical flow','opencv_version':cv2.__version__,'regions':regions,'summary':summary,'pairs':rows,'warnings':warning,'ground_speed_kmh':None,'realism_score':None,'limits':'Image-plane displacement proxies only. Use one continuous shot. Camera tracking, parallax, blur, lighting changes, occlusion, cuts and texture affect results; no physical speed or artistic pass/fail is inferred.'}
def detail_sheet(source,frames,crop,output):
 try:import av;from PIL import Image,ImageDraw
 except ImportError as e:raise ValueError('Detail sheets require PyAV and Pillow') from e
 if not isinstance(frames,list) or not frames or len(frames)>12 or len(set(frames))!=len(frames) or any(not isinstance(n,int) or isinstance(n,bool) or n<0 for n in frames):raise ValueError('Choose 1..12 unique nonnegative frame indices')
 if not isinstance(crop,list) or len(crop)!=4 or any(not isinstance(n,int) or isinstance(n,bool) for n in crop):raise ValueError('crop must be integer pixel x,y,width,height')
 x,y,w,h=crop
 if x<0 or y<0 or w<=0 or h<=0 or w*h*len(frames)>20000000:raise ValueError('Invalid or excessive crop sheet size')
 out=fresh(output,'.png');report=fresh(out.with_suffix('.details.json'));columns=min(3,len(frames));sheet=Image.new('RGB',(columns*w,math.ceil(len(frames)/columns)*(h+28)),(20,23,29));draw=ImageDraw.Draw(sheet);found={}
 with av.open(str(source)) as container:
  for n,frame in enumerate(container.decode(video=0)):
   if n in frames:
    if x+w>frame.width or y+h>frame.height:raise ValueError('Pixel crop leaves the actual image')
    found[n]=(frame.to_image().crop((x,y,x+w,y+h)),float(frame.pts*frame.time_base) if frame.pts is not None and frame.time_base is not None else None)
   if len(found)==len(frames):break
 if len(found)!=len(frames):raise ValueError('Requested frame does not exist')
 for i,n in enumerate(frames):
  col,row=i%columns,i//columns;im,t=found[n];sheet.paste(im,(col*w,row*(h+28)));draw.text((col*w+4,row*(h+28)+h+5),f'frame {n} | '+(f'{t:.3f}s' if t is not None else 'PTS unknown'),fill=(235,235,235))
 sheet.save(out);r={'source_sha256':digest(source),'frames':frames,'crop_pixels':crop,'scale':1,'resized':False,'sharpened':False,'realism_score':None,'limits':'Native decoded pixel crops for manual temporal/material review, with normal decoder RGB conversion; no denoising, added grain or fake detail. Not an identity detector.'};safe_write(report,r);return r
def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 c=sub.add_parser('flow');c.add_argument('source',type=Path);c.add_argument('--regions',type=Path,required=True);c.add_argument('--start-frame',type=int,default=0);c.add_argument('--max-frames',type=int,default=121);c.add_argument('--out',type=Path,required=True)
 c=sub.add_parser('details');c.add_argument('source',type=Path);c.add_argument('--frames',type=int,nargs='+',required=True);c.add_argument('--crop',type=int,nargs=4,required=True);c.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  if a.command=='flow':r=measure(a.source,read(a.regions),a.start_frame,a.max_frames);safe_write(a.out,r)
  else:r=detail_sheet(a.source,a.frames,a.crop,a.out)
  print(json.dumps({k:v for k,v in r.items() if k!='pairs'},ensure_ascii=False,allow_nan=False));return 0
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
