#!/usr/bin/env python3
"""Export an offline Promptfoo contract suite; does not install/run Promptfoo or call providers."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from creative_tools import safe_write
SKILL=Path(__file__).resolve().parents[1]
def export_suite(out):
 out=Path(out)
 for part in [out,*out.parents]:
  if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):raise ValueError('Refusing symlink/junction output')
 if out.exists() and any(out.iterdir()):raise ValueError('Output is not empty')
 out.mkdir(parents=True,exist_ok=True)
 cases=[('fixed_baseline','Static camera. A woman gently places one envelope on the table.','PASS'),('negated_move','Static camera, no orbit. She looks toward the window.','PASS'),('camera_conflict','Static camera and a fast 360 orbit around the woman.','FAIL'),('focus_conflict','Shallow depth of field and everything in focus.','FAIL'),('adjective_stack','8K masterpiece award-winning hyperrealistic.','FAIL')]
 config={'description':'Offline story-production text-contract regression. PASS/FAIL is not a video quality score.','prompts':['{{prompt}}'],'providers':[{'id':'file://offline_provider.py'}],'tests':[{'description':name,'vars':{'prompt':prompt},'assert':[{'type':'equals','value':expected}]} for name,prompt,expected in cases]}
 # JSON is a valid YAML 1.2 document, so no YAML dependency is needed.
 safe_write(out/'promptfooconfig.yaml',config)
 shutil.copy2(SKILL/'assets/promptfoo/offline_provider.py',out/'offline_provider.py');shutil.copy2(SKILL/'scripts/prompt_contract.py',out/'prompt_contract.py')
 note='This suite checks bounded text rules with an offline Python provider. It does not call an LLM or generate a video. Run with an installed Promptfoo CLI: promptfoo eval -c promptfooconfig.yaml. Replace providers only with explicit authorization for their data transmission and costs. A passing suite proves these contract cases, not artistic quality or market superiority.\n'
 (out/'README.txt').write_text(note,encoding='utf-8')
 files=[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()]
 safe_write(out/'manifest.json',{'generator':'story-production-promptfoo-contract','files':files,'model_called':False})
 return {'cases':len(cases),'providers':'offline local Python only','promptfoo_executed':False,'output':str(out)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(export_suite(a.out),ensure_ascii=False));return 0
 except (OSError,ValueError) as e:print('Error: '+str(e),file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
