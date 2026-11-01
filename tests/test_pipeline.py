"""Behavioral tests for the portable film compiler. No network or paid services."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "story-production"
CLI = SKILL / "scripts" / "film_pipeline.py"
EXAMPLE = SKILL / "assets" / "example-film.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


class ScriptInventory(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(dict(attrs))


class FilmPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="story-production-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "film.json"
        self.data = load(EXAMPLE)
        self.write_source(self.data)

    def tearDown(self):
        self.temp.cleanup()

    def write_source(self, data):
        self.source.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def run_cli(self, *args, ok=True):
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(CLI), *map(str, args)],
            cwd=self.root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
        )
        if ok:
            self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        else:
            self.assertNotEqual(proc.returncode, 0, "Invalid input was accepted")
            self.assertTrue((proc.stdout + proc.stderr).strip(), "Failure needs a usable diagnostic")
        return proc

    def build(self, data=None, directory="build"):
        if data is not None:
            self.write_source(data)
        out = self.root / directory
        self.run_cli("build", self.source, "--out", out)
        return out, load(out / "shot-plan.json")

    def reject(self, mutate):
        data = copy.deepcopy(self.data)
        mutate(data)
        self.write_source(data)
        self.run_cli("validate", self.source, ok=False)

    def test_example_is_a_complete_short_and_validates(self):
        self.assertEqual(self.data["project"]["format"], "short")
        self.assertEqual(len(self.data["scenes"]), 3)
        self.assertGreaterEqual(sum(row[0] for sc in self.data["scenes"] for row in sc["shots"]), 90)
        report = self.root / "report.json"
        self.run_cli("validate", self.source, "--report", report)
        self.assertTrue(report.is_file())

    def test_build_is_complete_and_does_not_mutate_source(self):
        before = self.source.read_bytes()
        out, package = self.build()
        expected = {
            "screenplay.md", "director-guide.md", "shot-plan.json", "assets.json",
            "shots.csv", "dialogue.csv", "subtitles.srt", "edit-markers.csv",
            "generation.csv", "asset-references.csv", "sound-cues.csv",
            "recurring-audio.csv", "index.html", "validation.json", "manifest.json",
        }
        self.assertTrue(expected.issubset({p.name for p in out.iterdir()}))
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(len(package["scenes"]), 3)
        self.assertEqual(len(package["shots"]), 12)
        self.assertEqual(package["meta"]["story_seconds"], 110)
        self.assertEqual(package["meta"]["credits_seconds"], 12)
        self.assertEqual(package["meta"]["total_seconds"], 122)
        self.assertNotIn(str(self.root), (out / "shot-plan.json").read_text(encoding="utf-8"))
        self.assertNotIn(str(REPO), (out / "index.html").read_text(encoding="utf-8"))

    def test_timeline_and_generation_cover_exactly_the_story(self):
        _, package = self.build()
        shots, clips = package["shots"], package["clips"]
        fps = package["meta"]["fps"]
        self.assertEqual(shots[0]["first_frame"], 0)
        self.assertEqual(shots[-1]["end_frame_exclusive"], 110 * fps)
        for previous, following in zip(shots, shots[1:]):
            self.assertEqual(previous["end_frame_exclusive"], following["first_frame"])
            self.assertEqual(previous["end_sec"], following["start_sec"])
        for shot in shots:
            self.assertEqual(shot["end_frame_exclusive"] - shot["first_frame"], shot["duration_sec"] * fps)
            owned = [clip for clip in clips if clip["shot"] == shot["id"]]
            if shot["pure_post"]:
                self.assertEqual(owned, [])
                self.assertEqual(shot["generation_units"], 0)
            else:
                self.assertTrue(owned)
                self.assertEqual(sum(x["clip_duration_sec"] for x in owned), shot["duration_sec"])
                self.assertTrue(all(0 < x["clip_duration_sec"] <= 8 for x in owned))
                for a, b in zip(owned, owned[1:]):
                    self.assertEqual(a["global_out_sec"], b["global_in_sec"])
        video = sum(x["clip_duration_sec"] for x in clips)
        post = sum(x["duration_sec"] for x in shots if x["pure_post"])
        self.assertEqual(video + post, package["meta"]["story_seconds"])

    def test_configured_fps_is_used_in_all_frame_counts(self):
        for fps in (25, 30):
            with self.subTest(fps=fps):
                data = copy.deepcopy(self.data)
                data["project"]["fps"] = fps
                _, package = self.build(data, directory=f"fps-{fps}")
                self.assertEqual(package["meta"]["fps"], fps)
                for shot in package["shots"]:
                    self.assertEqual(shot["first_frame"], round(shot["start_sec"] * fps))
                    self.assertEqual(shot["end_frame_exclusive"], round(shot["end_sec"] * fps))

    def test_partial_costume_override_merges_with_scene(self):
        _, package = self.build()
        shot = next(x for x in package["shots"] if x["id"] == "S02_002")
        self.assertIn("浅灰工作衬衫", shot["prompt"])
        self.assertIn("深绿工作围裙", shot["prompt"])
        self.assertNotIn("米色针织外套", shot["prompt"])
        self.assertIn("昨天的社区修理铺", shot["prompt"])

    def test_offscreen_voice_is_not_added_to_visible_assets(self):
        _, package = self.build()
        shot = next(x for x in package["shots"] if x["id"] == "S01_002")
        self.assertIn("C01", shot["asset_ids"])
        self.assertNotIn("C02", shot["asset_ids"])
        self.assertIn("C02", shot["voice_asset_ids"])

    def test_recurring_audio_has_an_explicit_single_source(self):
        out, package = self.build()
        by_id = {s["id"]: s for s in package["shots"]}
        cue = self.data["recurring_audio_cues"][0]
        for name in ("heard_shot", "source_shot"):
            shot = by_id[cue[name]]
            self.assertIn(cue["text"], [d["text"] for d in shot["dialogue"]])
            self.assertGreaterEqual(shot["duration_sec"], cue["duration_sec"])
        text = (out / "recurring-audio.csv").read_text(encoding="utf-8-sig")
        for value in (cue["id"], cue["heard_shot"], cue["source_shot"], cue["text"]):
            self.assertIn(value, text)
        self.assertIn(cue["source_shot"], (out / "dialogue.csv").read_text(encoding="utf-8-sig"))
        cue_lines = [d for d in package["dialogues"] if d.get("recurring_audio_id") == cue["id"]]
        self.assertEqual(len(cue_lines), 2)
        self.assertEqual(len({d["suggested_file"] for d in cue_lines}), 1)
        for line in cue_lines:
            self.assertEqual(line["start_sec"], by_id[line["shot"]]["start_sec"])
            self.assertEqual(line["end_sec"] - line["start_sec"], 8)

    def test_frame_aligned_fractional_duration_has_no_rounding_gap(self):
        data = copy.deepcopy(self.data)
        data["project"]["fps"] = 25
        data["scenes"][0]["shots"][0][0] = 8.04
        _, package = self.build(data)
        shots = package["shots"]
        self.assertEqual(shots[0]["end_frame_exclusive"], 201)
        self.assertEqual(shots[0]["out_tc_exclusive"], "00:00:08:01")
        self.assertEqual(shots[1]["first_frame"], 201)
        chunks = [c for c in package["clips"] if c["shot"] == shots[0]["id"]]
        self.assertEqual(sum(c["end_frame_exclusive"] - c["first_frame"] for c in chunks), 201)
        self.assertEqual(shots[-1]["end_frame_exclusive"], 2751)
        self.reject(lambda f: f["scenes"][0]["shots"][0].__setitem__(0, 1.01))

    def test_episode_mode_keeps_same_scene_and_shot_contract(self):
        data = copy.deepcopy(self.data)
        data["project"]["format"] = "episode"
        _, package = self.build(data)
        self.assertEqual(package["meta"]["format"], "episode")
        self.assertEqual(len(package["shots"]), 12)
        self.assertEqual(package["meta"]["story_seconds"], 110)

    def test_srt_stays_in_shots_and_uses_at_most_two_lines(self):
        out, package = self.build()
        by_id = {s["id"]: s for s in package["shots"]}
        for line in package["dialogues"]:
            owner = by_id[line["shot"]]
            self.assertLessEqual(owner["start_sec"], line["start_sec"])
            self.assertLess(line["start_sec"], line["end_sec"])
            self.assertLessEqual(line["end_sec"], owner["end_sec"])
        content = (out / "subtitles.srt").read_text(encoding="utf-8-sig").strip()
        blocks = re.split(r"\r?\n\s*\r?\n", content)
        previous_end = 0
        for number, block in enumerate(blocks, 1):
            lines = block.splitlines()
            self.assertEqual(int(lines[0]), number)
            self.assertIn(len(lines), (3, 4))
            match = re.fullmatch(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})", lines[1])
            self.assertIsNotNone(match)
            n = list(map(int, match.groups()))
            start = ((n[0] * 60 + n[1]) * 60 + n[2]) * 1000 + n[3]
            end = ((n[4] * 60 + n[5]) * 60 + n[6]) * 1000 + n[7]
            self.assertGreaterEqual(start, previous_end)
            self.assertGreater(end, start)
            self.assertLessEqual(end, 110_000)
            previous_end = end

    def test_invalid_assets_locations_and_wardrobes_are_rejected(self):
        cases = {
            "unknown visible asset": lambda f: f["scenes"][0]["shots"][0][10].append("UNKNOWN"),
            "unknown base location": lambda f: f["scenes"][0].update(location_id="UNKNOWN"),
            "unknown override location": lambda f: f["scenes"][1]["shot_overrides"]["2"].update(location_id="UNKNOWN"),
            "missing costume": lambda f: f["scenes"][0]["costumes"].pop("C01"),
            "unknown costume stage": lambda f: f["scenes"][0]["costumes"].update(C01="UNKNOWN"),
            "unknown override stage": lambda f: f["scenes"][1]["shot_overrides"]["2"]["costumes"].update(C02="UNKNOWN"),
            "override beyond scene": lambda f: f["scenes"][0].update(shot_overrides={"99": {"location_id": "L02"}}),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                self.reject(mutate)

    def test_duplicate_identifiers_and_bad_durations_are_rejected(self):
        cases = {
            "duplicate character": lambda f: f["characters"].append(copy.deepcopy(f["characters"][0])),
            "duplicate prop": lambda f: f["props"].append(copy.deepcopy(f["props"][0])),
            "cross-type duplicate": lambda f: f["props"][0].update(id="C01"),
            "duplicate scene": lambda f: f["scenes"][1].update(n=1),
            "zero duration": lambda f: f["scenes"][0]["shots"][0].__setitem__(0, 0),
            "negative duration": lambda f: f["scenes"][0]["shots"][0].__setitem__(0, -1),
            "boolean duration": lambda f: f["scenes"][0]["shots"][0].__setitem__(0, True),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                self.reject(mutate)

    def test_invalid_audio_references_and_timing_are_rejected(self):
        cases = {
            "missing source": lambda f: f["recurring_audio_cues"][0].update(source_shot="S99_001"),
            "wrong spoken text": lambda f: f["recurring_audio_cues"][0].update(text="另一个没有说过的句子。"),
            "exceeds shot": lambda f: f["recurring_audio_cues"][0].update(duration_sec=9),
            "negative offset": lambda f: f["recurring_audio_cues"][0].update(local_in_sec=-1),
            "duplicate cue": lambda f: f["recurring_audio_cues"].append(copy.deepcopy(f["recurring_audio_cues"][0])),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                self.reject(mutate)

    def test_nonempty_output_refuses_implicit_overwrite(self):
        out = self.root / "existing"
        out.mkdir()
        sentinel = out / "my-notes.txt"
        sentinel.write_text("keep me", encoding="utf-8")
        self.run_cli("build", self.source, "--out", out, ok=False)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep me")
        self.assertFalse((out / "shot-plan.json").exists())
        self.run_cli("build", self.source, "--out", out, "--overwrite")
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep me")

    def test_owned_output_symlink_does_not_write_outside_destination(self):
        out = self.root / "linked-output"
        out.mkdir()
        external = self.root / "external.txt"
        external.write_text("must remain unchanged", encoding="utf-8")
        try:
            os.symlink(external, out / "index.html")
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Symlink creation unavailable on this host: {exc}")
        self.run_cli("build", self.source, "--out", out, "--overwrite", ok=False)
        self.assertEqual(external.read_text(encoding="utf-8"), "must remain unchanged")

    def test_build_cannot_overwrite_its_own_authoritative_source(self):
        out = self.root / "source-collision"
        out.mkdir()
        source = out / "shot-plan.json"
        before = self.source.read_bytes()
        source.write_bytes(before)
        self.run_cli("build", source, "--out", out, "--overwrite", ok=False)
        self.assertEqual(source.read_bytes(), before)

    def test_csv_text_cannot_be_interpreted_as_a_formula(self):
        data = copy.deepcopy(self.data)
        payload = '=HYPERLINK("https://example.invalid","sample")'
        data["scenes"][0]["shots"][2][5] = [["简宁", payload]]
        out, _ = self.build(data)
        with (out / "dialogue.csv").open(encoding="utf-8-sig", newline="") as stream:
            cells = [cell for row in csv.reader(stream) for cell in row]
        self.assertNotIn(payload, cells, "Raw formula text must be escaped for spreadsheet CSV imports")
        self.assertIn("'" + payload, cells)

    def test_authored_text_cannot_break_out_of_embedded_json(self):
        base_out, _ = self.build(directory="safe")
        safe = ScriptInventory()
        safe.feed((base_out / "index.html").read_text(encoding="utf-8"))
        data = copy.deepcopy(self.data)
        payload = '</script><script id="unexpected-script">globalThis.pwned=true</script>'
        data["logline"] = payload
        out, package = self.build(data, directory="escaped")
        html = (out / "index.html").read_text(encoding="utf-8")
        parsed = ScriptInventory()
        parsed.feed(html)
        self.assertEqual(parsed.scripts, safe.scripts)
        self.assertNotIn(payload, html)
        self.assertEqual(package["creative"]["logline"], payload, "Escaping output must not alter source meaning")

    def test_builds_are_deterministic_across_output_directories(self):
        a, _ = self.build(directory="first")
        b, _ = self.build(directory="second")
        hashes = lambda path: {
            p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()
        }
        self.assertEqual(hashes(a), hashes(b))

    def test_init_is_an_incomplete_scaffold_not_a_finished_film(self):
        project = self.root / "new-project"
        self.run_cli("init", "--theme", "雨夜归家", "--project", project, "--format", "short", "--minutes", "2")
        created = project / "film.json"
        self.assertTrue(created.is_file())
        scaffold = load(created)
        self.assertFalse(scaffold.get("scenes"), "init must not fabricate finished scenes")
        self.run_cli("validate", created, ok=False)


if __name__ == "__main__":
    unittest.main()
