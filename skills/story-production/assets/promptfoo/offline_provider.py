"""Promptfoo Python provider contract. Fully offline: no network/model/media calls."""
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('local_prompt_contract',Path(__file__).with_name('prompt_contract.py'))
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
def call_api(prompt,options,context):
 result=contract.check(prompt)
 return {'output':'PASS' if result['valid'] else 'FAIL','metadata':{'issues':result['issues'],'scope':result['scope'],'model_called':False,'media_generated':False}}
