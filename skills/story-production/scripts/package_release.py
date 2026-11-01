#!/usr/bin/env python3
"""Bundle a generated output folder using its manifest; never publish or upload it."""
import argparse,hashlib,json,zipfile,html,re
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path);parser.add_argument('--zip',required=True,type=Path);args=parser.parse_args()
    root=args.output.resolve();target=args.zip.resolve()
    if target.is_relative_to(root):parser.error('Place ZIP outside the output folder to prevent self-inclusion')
    if target.exists():parser.error('ZIP already exists; choose a new versioned filename')
    manifest_path=root/'manifest.json'
    if not manifest_path.is_file():parser.error('No manifest.json; build the project before packaging')
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'));records=manifest.get('files',[])
    if not isinstance(records,list):parser.error('Invalid files list in manifest')
    approved=set()
    for record in records:
        relative=record.get('path') if isinstance(record,dict) else record
        if not isinstance(relative,str):parser.error('Invalid manifest path')
        p=(root/relative).resolve()
        if not p.is_relative_to(root) or not p.is_file() or (root/relative).is_symlink():parser.error('Unsafe or missing manifest file: '+relative)
        approved.add(relative)
    # Optional exports must have receipts tied to the current source, not only familiar filenames.
    directories=[root]+list((root/'episodes').glob('E[0-9][0-9][0-9]') if (root/'episodes').exists() else [])
    for directory in directories:
        for receipt_name in ['pdf-export.json','xlsx-export.json']:
            receipt_path=directory/receipt_name
            if not receipt_path.is_file():continue
            if receipt_path.is_symlink():parser.error('Unsafe exporter receipt')
            receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
            for name,expected in receipt.get('source_dependencies',{}).items():
                p=(directory/name).resolve()
                if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:parser.error('Stale export; rebuild '+receipt_name)
            for item in receipt.get('files',[]):
                p=(directory/item['path']).resolve()
                if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:parser.error('Missing or modified export: '+item['path'])
                approved.add(p.relative_to(root).as_posix())
            approved.add(receipt_path.relative_to(root).as_posix())
    # Expose optional formats only after they exist. Do not invent download links.
    download_page='<!doctype html><html lang="zh"><meta charset="utf-8"><title>全部交付文件</title><body style="font:16px/1.8 system-ui;padding:5vw"><h1>全部交付文件</h1><p><a href="index.html">返回阅读入口</a></p><ul>'+''.join('<li><a href="'+html.escape(name,quote=True)+'">'+html.escape(name)+'</a></li>' for name in sorted(approved))+'</ul></body></html>'
    downloads=root/'downloads.html'
    if downloads.is_symlink():parser.error('Refusing symlink downloads.html')
    downloads.write_text(download_page,encoding='utf-8');approved.add('downloads.html')
    index=root/'index.html'
    if index.is_file():
        value=index.read_text(encoding='utf-8');value=re.sub(r'<!-- EXPORT_LINKS_BEGIN -->.*?<!-- EXPORT_LINKS_END -->','',value,flags=re.S)
        links='<!-- EXPORT_LINKS_BEGIN --><section style="padding:20px;text-align:center"><a href="downloads.html">查看全部交付文件（含已生成PDF / Excel）</a></section><!-- EXPORT_LINKS_END -->'
        anchor='</body>' if '</body>' in value else '</html>';value=value.replace(anchor,links+anchor,1);index.write_text(value,encoding='utf-8')
    updated=[]
    for name in sorted(approved):
        p=root/name;updated.append({'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    manifest['files']=updated;manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
        for name in sorted(approved|{'manifest.json'}):archive.write(root/name,name)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip():raise RuntimeError('ZIP CRC check failed')
    print(json.dumps({'zip':str(target),'files':len(approved)+1,'bytes':target.stat().st_size}))
if __name__=='__main__':main()
