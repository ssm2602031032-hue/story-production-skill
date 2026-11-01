"""Novel/season completeness, reuse and packaging boundaries; stdlib only."""
import copy,json,shutil,subprocess,sys,tempfile,unittest,zipfile,hashlib
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];SKILL=REPO/'skills/story-production';SCRIPTS=SKILL/'scripts'
sys.path.insert(0,str(SCRIPTS))
import story_pipeline

class StoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(SKILL/'assets/example-series',self.root/'series')
        self.series=self.root/'series/series.json';self.novel=self.root/'novel.json'
        shutil.copy2(SKILL/'assets/example-novel.json',self.novel)
    def tearDown(self):self.tmp.cleanup()
    def data(self,p):return json.loads(p.read_text(encoding='utf-8'))
    def test_novel_has_full_prose_export_and_real_count(self):
        data=self.data(self.novel);out=self.root/'book';report=story_pipeline.build(self.novel,out)
        self.assertTrue(report['valid']);self.assertEqual(report['counts']['chapters'],2)
        text=(out/'novel-book.md').read_text(encoding='utf-8')
        for ch in data['chapters']:self.assertIn(ch['body'],text)
    def test_missing_chapter_is_not_complete(self):
        d=self.data(self.novel);d['chapters'].pop();self.assertFalse(story_pipeline.validate(d,self.novel)['valid'])
    def test_duplicate_chapter_number_is_invalid(self):
        d=self.data(self.novel);d['chapters'][1]['n']=1;self.assertFalse(story_pipeline.validate(d,self.novel)['valid'])
    def test_novel_escapes_authored_markup(self):
        d=self.data(self.novel);d['chapters'][0]['body']+='\n</article><script>alert(1)</script>'
        self.novel.write_text(json.dumps(d),encoding='utf-8');out=self.root/'book';story_pipeline.build(self.novel,out)
        text=(out/'index.html').read_text(encoding='utf-8');self.assertNotIn('<script>alert',text);self.assertIn('&lt;script&gt;',text)
    def test_series_build_covers_every_episode(self):
        out=self.root/'show';r=story_pipeline.build(self.series,out)
        self.assertEqual(r['counts']['episodes'],2)
        for n in (1,2):self.assertTrue((out/f'episodes/E{n:03}/shot-plan.json').is_file())
        self.assertTrue((out/'asset-reuse.csv').is_file())
    def test_incomplete_episode_and_missing_source_are_rejected(self):
        d=self.data(self.series);d['episodes'][1]['status']='outline';self.assertFalse(story_pipeline.validate(d,self.series)['valid'])
        d=self.data(self.series);d['episodes'][1]['source']='missing.json';self.assertFalse(story_pipeline.validate(d,self.series)['valid'])
    def test_series_asset_identity_drift_is_rejected(self):
        episode=self.series.parent/'episodes/E002/film.json';d=self.data(episode);d['characters'][0]['appearance']='different actor'
        episode.write_text(json.dumps(d),encoding='utf-8');self.assertFalse(story_pipeline.validate(self.data(self.series),self.series)['valid'])
    def test_series_state_jump_is_rejected(self):
        d=self.data(self.series);d['continuity_events'][1]['from_state']='LAMP_INSIDE'
        self.assertFalse(story_pipeline.validate(d,self.series)['valid'])
    def test_episode_source_cannot_escape_root(self):
        d=self.data(self.series);d['episodes'][0]['source']='../novel.json'
        self.assertFalse(story_pipeline.validate(d,self.series)['valid'])
    def test_source_cannot_be_overwritten_as_output(self):
        before=self.novel.read_bytes()
        with self.assertRaises(ValueError):story_pipeline.build(self.novel,self.root,overwrite=True)
        self.assertEqual(before,self.novel.read_bytes())
    def test_overwrite_preserves_unrelated_files_excludes_from_manifest(self):
        out=self.root/'out';story_pipeline.build(self.novel,out);(out/'private-notes.txt').write_text('not part of publication')
        with self.assertRaises(ValueError):story_pipeline.build(self.novel,out)
        story_pipeline.build(self.novel,out,overwrite=True)
        self.assertEqual((out/'private-notes.txt').read_text(),'not part of publication')
        self.assertNotIn('private-notes.txt',[r['path'] for r in self.data(out/'manifest.json')['files']])
    def test_archive_only_includes_manifest_owned_files(self):
        out=self.root/'out';story_pipeline.build(self.novel,out);(out/'unrelated.key').write_text('do not package')
        target=self.root/'book.zip';proc=subprocess.run([sys.executable,str(SCRIPTS/'package_release.py'),str(out),'--zip',str(target)],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stderr)
        with zipfile.ZipFile(target) as z:self.assertNotIn('unrelated.key',z.namelist());self.assertIn('novel-book.md',z.namelist());self.assertIsNone(z.testzip())
    def test_init_does_not_claim_authored_work(self):
        for mode in ('novel','series'):
            p=story_pipeline.initialize(mode,'test',self.root/(mode+'-init'),2)
            self.assertFalse(story_pipeline.validate(self.data(p),p)['valid'])
    def test_archive_rejects_stale_optional_export(self):
        out=self.root/'out';story_pipeline.build(self.novel,out)
        source=out/'novel-plan.json';fake=out/'novel-book.pdf';fake.write_bytes(b'exported test bytes')
        receipt={'source_dependencies':{'novel-plan.json':hashlib.sha256(source.read_bytes()).hexdigest()},'files':[{'path':'novel-book.pdf','sha256':hashlib.sha256(fake.read_bytes()).hexdigest()}]}
        (out/'pdf-export.json').write_text(json.dumps(receipt))
        source.write_text(source.read_text(encoding='utf-8')+'\n',encoding='utf-8')
        proc=subprocess.run([sys.executable,str(SCRIPTS/'package_release.py'),str(out),'--zip',str(self.root/'stale.zip')],capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0);self.assertIn('Stale export',proc.stderr);self.assertFalse((self.root/'stale.zip').exists())

if __name__=='__main__':unittest.main()
