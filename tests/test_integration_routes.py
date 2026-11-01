"""Integration routes preserve scope and offline provenance remains verifiable."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];S=ROOT/'skills/story-production';sys.path.insert(0,str(S/'scripts'))
from creative_tools import plan,catalog
class IntegrationRouteTests(unittest.TestCase):
 def test_specific_tools_do_not_trigger_full_story_generation(self):
  cases=[('只整理小说第六章的章节上下文','context','novel-context-packs'),('做提示词回归测试','regression','prompt-regression'),('检查视频参数，不改正文','media-qc','technical-media-qc'),('检查字幕SRT','subtitles','subtitle-alignment'),('导出OTIO剪辑工程','editorial','editorial-handoff'),('解释VBench视频指标','metrics','video-metric-reading'),('检测切点','cuts','scene-detection-review')]
  for request,task,mid in cases:
   with self.subTest(request=request):
    p=plan(request);self.assertEqual(p['task'],task);ids={m['id'] for m in p['modules']};self.assertIn(mid,ids);self.assertNotIn('premise',ids)
 def test_context_request_with_continuation_still_writes_prose(self):
  p=plan('续写这部小说下一章，先整理章节契约');self.assertEqual(p['task'],'draft');self.assertIn('novel-context-packs',{m['id'] for m in p['modules']});self.assertIn('scene',{m['id'] for m in p['modules']})
 def test_combined_media_request_preserves_requested_subtitles(self):
  p=plan('检查视频技术参数和字幕，按镜头计划导出OTIO');self.assertTrue({'technical-media-qc','subtitle-alignment','editorial-handoff'}<={m['id'] for m in p['modules']})
 def test_new_sources_have_pinned_files_and_bundled_licenses(self):
  projects=json.loads((S/'assets/integration-projects.json').read_text(encoding='utf-8'))['projects'];ids=set()
  modules={m['id'] for m in catalog()['modules']}
  for project in projects:
   self.assertNotIn(project['id'],ids);ids.add(project['id']);self.assertRegex(project['commit'],r'^[a-f0-9]{40}$');self.assertTrue(set(project['modules'])<=modules);self.assertTrue(project['verification']['details'])
   bundled=[]
   for file in project['files']:
    self.assertIn('/'+project['commit']+'/',file['url']);self.assertRegex(file['sha256'],r'^[a-f0-9]{64}$');self.assertNotIn('local',file)
    if 'bundled_path' in file:
     path=(S/file['bundled_path']).resolve();self.assertTrue(path.is_relative_to(S.resolve()));self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),file['sha256']);bundled.append(path.name)
   self.assertTrue(any(name.startswith('LICENSE') for name in bundled))
if __name__=='__main__':unittest.main()
