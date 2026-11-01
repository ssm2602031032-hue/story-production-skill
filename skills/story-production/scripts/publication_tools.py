#!/usr/bin/env python3
"""Export complete authored sources as EPUB 3 or screenplay interchange; never invent missing prose."""
from pathlib import Path
import argparse,collections,datetime,html,io,json,sys,zipfile,xml.etree.ElementTree as ET
from creative_tools import read,safe_write
from delivery_utils import fresh,digest
from story_pipeline import validate
def manuscript_audit(source):
 d=read(source)
 if d.get('kind')!='novel':raise ValueError('Expected novel.json')
 result=validate(d,Path(source));seen={};repeats=[];whitespace=[]
 for ch in d.get('chapters',[]):
  for n,line in enumerate(ch.get('body','').splitlines(),1):
   text=line.strip()
   if text!=line:whitespace.append({'chapter':ch['n'],'line':n})
   if len(text)>=30:
    if text in seen:repeats.append({'first':seen[text],'again':{'chapter':ch['n'],'line':n},'excerpt':text[:80]})
    else:seen[text]={'chapter':ch['n'],'line':n}
 return {'valid':result['valid'],'errors':result['errors'],'warnings':result['warnings'],'repeated_paragraph_candidates':repeats,'outer_whitespace':whitespace,'source_sha256':digest(source),'limits':'Exact repetition and structural checks; refrains may be intentional. Not grammar correction, literary grading or platform eligibility. Source is not modified.'}
def epub(source,output,author=None):
 d=read(source);audit=manuscript_audit(source)
 if not audit['valid']:raise ValueError('Cannot export a complete edition: '+'; '.join(audit['errors']))
 out=fresh(output,'.epub');esc=html.escape;lang=d.get('project',{}).get('language','zh-CN');title=d['title'];identifier='urn:sha256:'+digest(source);now=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
 def xhtml(heading,body):return '<?xml version="1.0" encoding="UTF-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="'+esc(lang,quote=True)+'" xml:lang="'+esc(lang,quote=True)+'"><head><title>'+esc(heading)+'</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body>'+body+'</body></html>'
 chapters=d['chapters'];items=['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>','<item id="css" href="style.css" media-type="text/css"/>'];spine=[];nav=[];files={}
 for ch in chapters:
  cid=f'ch{ch["n"]:03}';name=cid+'.xhtml';heading=ch['title'];items.append(f'<item id="{cid}" href="{name}" media-type="application/xhtml+xml"/>');spine.append(f'<itemref idref="{cid}"/>');nav.append(f'<li><a href="{name}">{esc(heading)}</a></li>')
  body='<h1>'+esc(heading)+'</h1>'+''.join('<p>'+esc(p)+'</p>' for p in ch['body'].splitlines() if p.strip());files['EPUB/'+name]=xhtml(heading,body)
 creator='<dc:creator>'+esc(author)+'</dc:creator>' if author else ''
 files['EPUB/package.opf']='<?xml version="1.0" encoding="UTF-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">'+identifier+'</dc:identifier><dc:title>'+esc(title)+'</dc:title><dc:language>'+esc(lang)+'</dc:language>'+creator+'<meta property="dcterms:modified">'+now+'</meta></metadata><manifest>'+''.join(items)+'</manifest><spine>'+''.join(spine)+'</spine></package>'
 files['EPUB/nav.xhtml']=xhtml(title,'<nav epub:type="toc" id="toc"><h1>'+esc(title)+'</h1><ol>'+''.join(nav)+'</ol></nav>')
 files['EPUB/style.css']='body{line-height:1.7;margin:5%;} p{white-space:pre-wrap;text-indent:2em;} h1{font-size:1.5em;}'
 files['META-INF/container.xml']='<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
 for name,content in files.items():
  if name.endswith(('.xhtml','.opf','.xml')):ET.fromstring(content)
 with zipfile.ZipFile(out,'x') as z:
  z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
  for name,content in files.items():z.writestr(name,content,compress_type=zipfile.ZIP_DEFLATED)
 with zipfile.ZipFile(out) as z:
  if z.testzip():raise ValueError('EPUB ZIP CRC failed')
 return {'output':str(out),'chapters':len(chapters),'source_sha256':digest(source),'epubcheck_run':False,'validation':'ZIP/XML/spine generated locally; run actual EPUBCheck and inspect in a reader before distribution','author_included':bool(author)}
def screenplay(source,output):
 from film_pipeline import validate_film,compile_film
 d=read(source);check=validate_film(d)
 if not check['valid']:raise ValueError('Invalid film source: '+'; '.join(check['errors']))
 package=compile_film(d,digest(source));out=fresh(output)
 if out.suffix.lower() not in ('.fountain','.fdx'):raise ValueError('Choose .fountain or .fdx')
 paragraphs=[]
 for scene in package['scenes']:
  paragraphs.append(('scene',scene['heading']))
  for shot in (s for s in package['shots'] if s['scene']==scene['scene']):
   paragraphs.append(('action',shot['picture']))
   for line in shot['dialogue']:paragraphs.extend([('character',line['speaker']),('dialogue',line['text'])])
 if out.suffix.lower()=='.fountain':
  def literal(s):return s.replace('\\','\\\\').replace('*','\\*').replace('_','\\_').replace('[','\\[').replace(']','\\]')
  lines=['Title: '+literal(d['title']),'']
  for kind,text in paragraphs:
   text=literal(text)
   if kind=='character':lines.append('@'+text)
   else:
    if kind=='scene':text='.'+text
    elif kind=='action':text='!'+text
    lines.extend([text,''])
  out.write_text('\n'.join(lines)+'\n',encoding='utf-8');backend='native Fountain text'
 else:
  try:
   from screenplain.types import Screenplay,Slug,Action,Dialog
   from screenplain.richstring import RichString,Segment
   from screenplain.export.fdx import to_fdx
  except ImportError as e:raise ValueError('FDX requires optional screenplain; no file was exported') from e
  rich=lambda t:RichString(Segment(t,set()));doc=Screenplay(title_page={'Title':[d['title']]});speaker=None
  for kind,text in paragraphs:
   if kind=='scene':doc.append(Slug(rich(text)))
   elif kind=='action':doc.append(Action([rich(t) for t in text.splitlines()]))
   elif kind=='character':speaker=text
   else:
    dialog=Dialog(rich(speaker));dialog.blocks=[(False,rich(t)) for t in text.splitlines()];doc.append(dialog)
  stream=io.StringIO();to_fdx(doc,stream);content=stream.getvalue();ET.fromstring(content);out.write_text(content,encoding='utf-8');backend='screenplain'
 return {'output':str(out),'backend':backend,'paragraphs':len(paragraphs),'source_sha256':digest(source),'limits':'Story text interchange only; does not round-trip shot timing, media links or every editor feature. Native editor import still needs testing.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['audit','epub','screenplay']);p.add_argument('source',type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--author');a=p.parse_args()
 try:
  if a.command=='audit':r=manuscript_audit(a.source);safe_write(a.out,r)
  elif a.command=='epub':r=epub(a.source,a.out,a.author)
  else:r=screenplay(a.source,a.out)
  print(json.dumps(r,ensure_ascii=False));return 0 if r.get('valid',True) else 1
 except (ValueError,OSError,KeyError,TypeError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
