"""Small deterministic prompt contract checks; not an NLP or visual quality evaluator."""
import re
def check(prompt):
 if not isinstance(prompt,str) or not prompt.strip():return {'valid':False,'issues':['empty_prompt'],'scope':'text-contract-only'}
 t=prompt.lower()
 # Remove bounded, explicit negated camera requests before checking contradictions.
 t=re.sub(r'\b(?:no|without|avoid|do not)\s+(?:(?:any|a|fast|slow|camera|360|degree)\s+){0,3}(?:orbit(?:ing)?|dolly|tracking|zoom(?:ing)?)(?:\s+(?:in|out))?','',t)
 t=re.sub(r'(?:不要|禁止|不做|不叠加)(?:快速|缓慢|相机|镜头)?(?:环绕|推轨|跟拍|变焦)','',t)
 issues=[]
 fixed=any(x in t for x in ('locked-off','static camera','camera remains still','camera is fixed','固定机位','相机固定','三脚架固定'))
 moved=bool(re.search(r'\b(?:orbit|dolly|tracking)\b',t)) or any(x in t for x in ('环绕','推轨','跟拍'))
 if fixed and moved:issues.append('fixed_and_moving_camera')
 if ('shallow depth' in t or '浅景深' in t) and ('everything in focus' in t or '所有景物清晰' in t):issues.append('conflicting_depth_of_field')
 if sum(x in t for x in ('8k','masterpiece','award-winning','hyperrealistic','顶级','最高画质','超级真实'))>=3:issues.append('quality_adjective_stack')
 return {'valid':not issues,'issues':issues,'scope':'bounded text rules only; intentional phases and nuanced negation require human review; no media quality score'}
