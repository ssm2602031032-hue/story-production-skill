"""Optional CI conformance check using a pinned, SHA256-verified official EPUBCheck release."""
from pathlib import Path
import argparse,hashlib,subprocess,sys,urllib.request,zipfile
R=Path(__file__).resolve().parents[1];S=R/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from publication_tools import epub
URL='https://github.com/w3c/epubcheck/releases/download/v5.4.0/epubcheck-5.4.0.zip'
SHA='33350c61038e71dfb3d45a76aed04bf5481e6d5500cb780f6e98db8bbd15a28c'
def main():
 p=argparse.ArgumentParser();p.add_argument('--workdir',type=Path,required=True);a=p.parse_args();root=a.workdir.resolve()
 if root.exists():raise ValueError('Use a fresh temporary directory')
 root.mkdir(parents=True);archive=root/'checker.zip'
 with urllib.request.urlopen(URL,timeout=60) as response:blob=response.read()
 if hashlib.sha256(blob).hexdigest()!=SHA:raise ValueError('Official checker release hash mismatch')
 archive.write_bytes(blob)
 with zipfile.ZipFile(archive) as z:
  for member in z.infolist():
   if not (root/member.filename).resolve().is_relative_to(root):raise ValueError('Unsafe archive path')
  z.extractall(root)
 book=root/'example.epub';epub(S/'assets/example-novel.json',book)
 jars=list(root.glob('epubcheck-*/epubcheck.jar'))
 if len(jars)!=1:raise ValueError('Expected one official checker jar')
 return subprocess.run(['java','-jar',str(jars[0]),str(book)],check=False).returncode
if __name__=='__main__':raise SystemExit(main())
