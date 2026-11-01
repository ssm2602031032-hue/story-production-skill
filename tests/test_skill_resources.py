"""Check public resource links and portable entrypoint references."""
import re,unittest
from pathlib import Path
from urllib.parse import unquote,urlsplit
ROOT=Path(__file__).resolve().parents[1];SKILL=ROOT/'skills/story-production'
class ResourceTests(unittest.TestCase):
 def test_local_markdown_links_resolve_inside_repository(self):
  files=[ROOT/'README.md',ROOT/'THIRD_PARTY_NOTICES.md',SKILL/'SKILL.md',*list((SKILL/'references').rglob('*.md'))]
  for file in files:
   text=file.read_text(encoding='utf-8')
   for raw in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
    raw=raw.strip().split(' "')[0].strip('<>')
    if not raw or raw.startswith('#') or urlsplit(raw).scheme:continue
    target=(file.parent/unquote(raw.split('#')[0])).resolve()
    self.assertTrue(target.is_relative_to(ROOT.resolve()),f'{file}: link escapes repo {raw}')
    self.assertTrue(target.exists(),f'{file}: broken link {raw}')
 def test_no_nested_skill_entrypoints_auto_install_twice(self):
  self.assertEqual([p.relative_to(SKILL).as_posix() for p in SKILL.rglob('SKILL.md')],['SKILL.md'])
 def test_all_copied_upstream_skills_are_catalogued(self):
  import json
  modules=json.loads((SKILL/'assets/creative-modules.json').read_text(encoding='utf-8'))['modules']
  refs={m['reference'] for m in modules}
  snapshots=(SKILL/'references/upstream/kunka').glob('kunka-*.md')
  self.assertTrue(all(p.relative_to(SKILL).as_posix() in refs for p in snapshots))
if __name__=='__main__':unittest.main()
