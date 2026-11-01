"""Small shared helpers for local, versioned delivery artifacts."""
from pathlib import Path
import hashlib,math
def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def fresh(path,suffix=None):
 path=Path(path)
 for part in [path,*path.parents]:
  if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Output cannot traverse a link')
 if path.exists():raise ValueError('Output exists; choose a new versioned path')
 if suffix and path.suffix.lower()!=suffix:raise ValueError('Expected '+suffix+' output')
 path.parent.mkdir(parents=True,exist_ok=True);return path
def finite(value,label,minimum=None):
 if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or (minimum is not None and value<minimum):raise ValueError(label+' must be finite'+(' and >= '+str(minimum) if minimum is not None else ''))
 return value
def index(rows,label):
 if not isinstance(rows,list):raise ValueError(label+' must be a list')
 result={}
 for row in rows:
  if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'] or row['id'] in result:raise ValueError(label+' needs unique nonempty IDs')
  result[row['id']]=row
 return result
