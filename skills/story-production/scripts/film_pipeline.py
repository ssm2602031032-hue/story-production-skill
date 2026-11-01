#!/usr/bin/env python3
"""Offline authoring validation and production-package export. Python 3.10+."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import html
import io
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERSION = "1.0"
OWNED = {
    "screenplay.md", "director-guide.md", "shot-plan.json", "assets.json",
    "shots.csv", "dialogue.csv", "subtitles.srt", "edit-markers.csv",
    "generation.csv", "asset-references.csv", "sound-cues.csv",
    "recurring-audio.csv", "index.html", "validation.json", "manifest.json",
}
DEFAULTS = {"format": "feature", "language": "zh-CN", "fps": 24,
            "aspect_ratio": "2.39:1", "target_minutes": 100,
            "credits_seconds": 120, "max_clip_seconds": 8}
TEXT_FIELDS = ("title", "slug", "genre", "logline", "theme", "synopsis")
SCENE_FIELDS = ("heading", "story_day", "location_id", "intent", "space",
                "axis", "light", "performance", "sound", "continuity")
OVERRIDE_KEYS = {"location_id", "space", "axis", "light", "continuity", "costumes"}
NEGATIVE = ("保持批准的人物身份、年龄、服装、左右方向与物体数量；无多余肢体、"
            "穿透、瞬移、乱码、水印。画外或录音人物不因说话自动入画。")


class FilmError(ValueError):
    """An actionable input or export error, without a traceback in the CLI."""


def read_json(path: Path | str):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FilmError(f"Cannot read JSON {Path(path).name}: {exc}") from exc


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def frames(seconds, fps):
    if not number(seconds):
        raise FilmError("Time must be a finite number, not a boolean or string")
    value = Decimal(str(seconds)) * fps
    rounded = value.to_integral_value()
    if abs(value - rounded) > Decimal("0.00001"):
        raise FilmError(f"{seconds} seconds is not aligned to {fps} fps")
    return int(rounded)


def seconds(frame, fps):
    return round(frame / fps, 9)


def tc(frame, fps):
    return f"{frame // (3600 * fps):02}:{frame // (60 * fps) % 60:02}:{frame // fps % 60:02}:{frame % fps:02}"


def srt_stamp(frame, fps):
    ms = round(frame * 1000 / fps)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def cjk(text):
    return len(re.findall(r"[\u3400-\u9fff]", text))


def spoken_seconds(text):
    other = re.sub(r"[\u3400-\u9fff]", " ", text)
    words = len(re.findall(r"\b[\w'-]+\b", other, flags=re.UNICODE))
    return max(0.6, cjk(text) / 4.1 + words / 2.5 + 0.25)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def costume_stages(character):
    value = character.get("costumes", {})
    return value if isinstance(value, dict) else {}


def project_options(data):
    return {**DEFAULTS, **data.get("project", {})}


def validate_film(data):
    """Return structured errors/warnings. Does not mutate the input or write files."""
    errors, warnings = [], []
    report = {"valid": False, "errors": errors, "warnings": warnings, "stats": {}}
    if not isinstance(data, dict):
        errors.append("Root must be a JSON object")
        return report
    if data.get("authoring_status") == "incomplete":
        errors.append("Authoring is marked incomplete; finish the screenplay before building")
    elif data.get("authoring_status") not in (None, "complete"):
        errors.append("authoring_status must be complete or incomplete")
    for key in TEXT_FIELDS:
        if not nonempty(data.get(key)):
            errors.append(f"{key}: a nonempty string is required")
    if nonempty(data.get("slug")) and not re.fullmatch(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", data["slug"]):
        errors.append("slug: use lowercase ASCII letters/digits separated by hyphens or underscores")
    if not isinstance(data.get("project", {}), dict):
        errors.append("project must be an object")
        return report
    options = project_options(data)
    fps = options["fps"]
    if type(fps) is not int or fps not in (24, 25, 30):
        errors.append("project.fps must be one of the integer rates 24, 25, 30 (non-drop-frame)")
        return report
    if options["format"] not in ("feature", "short", "episode"):
        errors.append("project.format must be feature, short or episode")
    for key in ("language", "aspect_ratio"):
        if not nonempty(options[key]):
            errors.append(f"project.{key} must be a nonempty string")
    for key in ("target_minutes", "credits_seconds", "max_clip_seconds"):
        v = options[key]
        if not number(v) or v < 0 or (key != "credits_seconds" and v == 0):
            errors.append(f"project.{key} must be a finite {'nonnegative' if key == 'credits_seconds' else 'positive'} number")
        elif key != "target_minutes":
            try:
                n = frames(v, fps)
                if key == "max_clip_seconds" and n < 1:
                    errors.append("project.max_clip_seconds must contain at least one frame")
            except FilmError as exc:
                errors.append(f"project.{key}: {exc}")
    for key in ("world_rules", "structure", "continuity_audit"):
        if not isinstance(data.get(key), list):
            errors.append(f"{key} must be a list")
    if isinstance(data.get("world_rules"), list) and any(not nonempty(s) for s in data["world_rules"]):
        errors.append("world_rules entries must be nonempty strings")
    for key, fields in (("structure", ("scenes", "cause", "payoff")),
                        ("continuity_audit", ("thread", "setup", "payoff", "result"))):
        if isinstance(data.get(key), list):
            for i, item in enumerate(data[key]):
                if not isinstance(item, dict) or any(not nonempty(item.get(f)) for f in fields):
                    errors.append(f"{key}[{i}]: required strings {', '.join(fields)}")
    production = data.get("production")
    if not isinstance(production, dict):
        errors.append("production must be an object")
    else:
        for key in ("palette", "camera", "sound", "music", "ai_workflow"):
            if not nonempty(production.get(key)):
                errors.append(f"production.{key}: a nonempty string is required")
        if not isinstance(production.get("priority_tests"), list) or any(not nonempty(x) for x in production.get("priority_tests", [])):
            errors.append("production.priority_tests must be a list of strings")
    asset_ids, chars, locations = set(), {}, {}
    for key in ("characters", "props", "locations"):
        entries = data.get(key)
        if not isinstance(entries, list):
            errors.append(f"{key} must be a list")
            continue
        for i, item in enumerate(entries):
            where = f"{key}[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{where} must be an object")
                continue
            aid = item.get("id")
            if not nonempty(aid) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", aid):
                errors.append(f"{where}.id: a portable identifier is required")
                continue
            if aid in asset_ids:
                errors.append(f"Duplicate asset ID: {aid}")
            asset_ids.add(aid)
            required = {"characters": ("name", "appearance", "voice", "want", "need", "arc"),
                        "props": ("name", "design", "flow"),
                        "locations": ("name", "geography", "look")}[key]
            for field in required:
                if not nonempty(item.get(field)):
                    errors.append(f"{where}.{field}: a nonempty string is required")
            if key == "characters":
                chars[aid] = item
                if not number(item.get("age")) or item.get("age", -1) < 0:
                    errors.append(f"{where}.age must be a nonnegative number")
                costumes = item.get("costumes")
                if not isinstance(costumes, dict) or not costumes or any(not nonempty(k) or not nonempty(v) for k, v in costumes.items()):
                    errors.append(f"{where}.costumes must map stage IDs to nonempty descriptions")
            elif key == "locations":
                locations[aid] = item
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes must contain the completed scenes; an empty scaffold is not a screenplay")
        return report
    shots, total_frames, body_chars, utterances = {}, 0, 0, 0
    seen_scene_numbers = set()
    for expected, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            errors.append(f"scenes[{expected - 1}] must be an object")
            continue
        n = scene.get("n")
        if type(n) is not int or n != expected:
            errors.append(f"Scene {expected}: n must be {expected}; scene numbers must be unique and consecutive")
        if isinstance(n, (int, str)):
            if n in seen_scene_numbers:
                errors.append(f"Duplicate scene number: {n}")
            seen_scene_numbers.add(n)
        for field in SCENE_FIELDS:
            if not nonempty(scene.get(field)):
                errors.append(f"Scene {expected}.{field}: a nonempty string is required")
        if not isinstance(scene.get("location_id"), str) or scene.get("location_id") not in locations:
            errors.append(f"Scene {expected}: unknown location_id {scene.get('location_id')!r}")
        costumes = scene.get("costumes")
        if not isinstance(costumes, dict):
            errors.append(f"Scene {expected}.costumes must be an object")
            costumes = {}
        for aid, stage in costumes.items():
            if aid not in chars or not isinstance(stage, str) or stage not in costume_stages(chars[aid]):
                errors.append(f"Scene {expected}: invalid costume mapping {aid}={stage}")
        rows = scene.get("shots")
        if not isinstance(rows, list) or not rows:
            errors.append(f"Scene {expected}.shots must be a nonempty list")
            continue
        overrides = scene.get("shot_overrides", {})
        if not isinstance(overrides, dict):
            errors.append(f"Scene {expected}.shot_overrides must be an object")
            overrides = {}
        for key, override in overrides.items():
            if not isinstance(key, str) or not key.isdigit() or str(int(key)) != key or not 1 <= int(key) <= len(rows):
                errors.append(f"Scene {expected}: invalid shot override key {key!r}")
            if not isinstance(override, dict):
                errors.append(f"Scene {expected}: override {key} must be an object")
                continue
            if set(override) - OVERRIDE_KEYS:
                errors.append(f"Scene {expected}: override {key} has unsupported fields {sorted(set(override) - OVERRIDE_KEYS)}")
            for field, value in override.items():
                if field == "costumes":
                    if not isinstance(value, dict):
                        errors.append(f"Scene {expected}: override {key}.costumes must be an object")
                    else:
                        for aid, stage in value.items():
                            if aid not in chars or not isinstance(stage, str) or stage not in costume_stages(chars[aid]):
                                errors.append(f"Scene {expected}: override {key} invalid costume {aid}={stage}")
                elif not nonempty(value):
                    errors.append(f"Scene {expected}: override {key}.{field} must be a nonempty string")
            if "location_id" in override and (not isinstance(override["location_id"], str) or override["location_id"] not in locations):
                errors.append(f"Scene {expected}: override {key} has unknown location")
        for j, row in enumerate(rows, 1):
            sid = f"S{expected:02}_{j:03}"
            if not isinstance(row, list) or len(row) != 12:
                errors.append(f"{sid}: expected a 12-element shot array")
                continue
            duration, size, lens, camera, picture, dialogue, sound, cut, first, last, visible, special = row
            try:
                count = frames(duration, fps)
                if count <= 0:
                    raise FilmError("shot duration must be positive")
            except FilmError as exc:
                errors.append(f"{sid}: {exc}")
                count = 0
            if not number(lens) or lens < 0:
                errors.append(f"{sid}: lens must be a nonnegative number")
            for name, value in (("size", size), ("camera", camera), ("picture", picture),
                                ("sound", sound), ("transition", cut), ("first_anchor", first),
                                ("last_anchor", last), ("special", special)):
                if not nonempty(value):
                    errors.append(f"{sid}.{name}: a nonempty string is required")
            if isinstance(picture, str):
                body_chars += cjk(picture)
            if first == last and isinstance(camera, str) and not any(x in camera.lower() for x in ("固定", "静", "static", "locked")):
                warnings.append(f"{sid}: moving shot has identical first/last anchors; review the intended change")
            if not isinstance(visible, list) or any(not isinstance(x, str) for x in visible):
                errors.append(f"{sid}.visible: use a list of asset IDs")
                visible = []
            elif len(visible) != len(set(visible)):
                errors.append(f"{sid}: duplicate visible asset ID")
            override = overrides.get(str(j), {})
            override = override if isinstance(override, dict) else {}
            extra_costumes = override.get("costumes", {})
            effective_costumes = {**costumes, **(extra_costumes if isinstance(extra_costumes, dict) else {})}
            for aid in visible:
                if aid not in asset_ids or aid in locations:
                    errors.append(f"{sid}: unknown/nonvisual character or prop asset {aid}")
                stage = effective_costumes.get(aid)
                if aid in chars and (not isinstance(stage, str) or stage not in costume_stages(chars[aid])):
                    errors.append(f"{sid}: visible character {aid} needs a valid costume stage")
            valid_dialogue = isinstance(dialogue, list)
            if valid_dialogue:
                valid_dialogue = all(isinstance(x, list) and len(x) == 2 and all(nonempty(y) for y in x) for x in dialogue)
            if not valid_dialogue:
                errors.append(f"{sid}.dialogue: use [[speaker, actual words], ...], or []")
                dialogue = []
            utterances += len(dialogue)
            body_chars += sum(cjk(x[1]) for x in dialogue)
            if len(dialogue) > count:
                errors.append(f"{sid}: there are more utterances than available frames")
            if count and sum(spoken_seconds(x[1]) for x in dialogue) > count / fps:
                warnings.append(f"{sid}: dialogue is dense for the provisional duration; record performance and revise timing")
            if count and duration > 30:
                warnings.append(f"{sid}: long take requires performance/continuation testing")
            shots[sid] = {"row": row, "frames": count, "dialogue": dialogue}
            total_frames += count
    cues = data.get("recurring_audio_cues", [])
    cue_ids, intervals = set(), {}
    if not isinstance(cues, list):
        errors.append("recurring_audio_cues must be a list")
        cues = []
    for i, cue in enumerate(cues):
        where = f"recurring_audio_cues[{i}]"
        if not isinstance(cue, dict):
            errors.append(f"{where}: expected an object")
            continue
        cid = cue.get("id")
        if not nonempty(cid) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", cid):
            errors.append(f"{where}.id: a portable ID is required")
        elif cid in cue_ids:
            errors.append(f"Duplicate recurring audio ID: {cid}")
        cue_ids.add(cid) if isinstance(cid, str) else None
        if not nonempty(cue.get("text")):
            errors.append(f"{where}.text is required")
        try:
            start = frames(cue.get("local_in_sec", 0), fps)
            length = frames(cue.get("duration_sec"), fps)
            if start < 0 or length <= 0:
                raise FilmError("audio local_in_sec must be nonnegative and duration positive")
        except FilmError as exc:
            errors.append(f"{where}: {exc}")
            continue
        if cue.get("heard_shot") == cue.get("source_shot"):
            errors.append(f"{where}: source and heard shots must be distinct")
        for key in ("heard_shot", "source_shot"):
            sid = cue.get(key)
            if not isinstance(sid, str) or sid not in shots:
                errors.append(f"{where}.{key}: unknown shot {sid!r}")
                continue
            shot = shots[sid]
            if start + length > shot["frames"]:
                errors.append(f"{where}: audio does not fit {sid}")
            if sum(line[1] == cue.get("text") for line in shot["dialogue"]) != 1:
                errors.append(f"{where}: exact audio text must occur once in {sid}")
            for a, b, other in intervals.get(sid, []):
                if start < b and a < start + length:
                    errors.append(f"{where}: overlaps {other} in {sid}")
            intervals.setdefault(sid, []).append((start, start + length, str(cid)))
    for sid, occupied in intervals.items():
        unused = shots[sid]["frames"] - sum(b - a for a, b, _ in occupied)
        unreserved = len(shots[sid]["dialogue"]) - len(occupied)
        if unused < unreserved:
            errors.append(f"{sid}: recurring audio leaves no frames for other dialogue")
        fixed = []
        for cue in cues:
            if isinstance(cue, dict) and sid in (cue.get("heard_shot"), cue.get("source_shot")) and number(cue.get("duration_sec")):
                matches = [i for i, line in enumerate(shots[sid]["dialogue"]) if line[1] == cue.get("text")]
                if len(matches) == 1:
                    try:
                        a = frames(cue.get("local_in_sec", 0), fps)
                        fixed.append((matches[0], a, a+frames(cue["duration_sec"], fps)))
                    except FilmError:
                        pass
        prior_index, prior_end = -1, 0
        for index, a, b in sorted(fixed):
            if a < prior_end or a-prior_end < index-prior_index-1:
                errors.append(f"{sid}: recurring audio timing conflicts with the written dialogue order")
            prior_index, prior_end = index, b
        if shots[sid]["frames"]-prior_end < len(shots[sid]["dialogue"])-prior_index-1:
            errors.append(f"{sid}: no time after recurring audio for the remaining written dialogue")
    actual_minutes = total_frames / fps / 60
    if number(options["target_minutes"]) and options["target_minutes"] > 0:
        target = options["target_minutes"]
        if actual_minutes < target * .8 or actual_minutes > target * 1.2:
            warnings.append(f"Actual designed runtime is {actual_minutes:.2f} min versus target {target:g}; resolve scope explicitly, never pad footage")
    if options["format"] == "feature" and (len(scenes) < 25 or total_frames < 60 * 60 * fps):
        warnings.append("Feature profile has limited coverage/runtime; review whether the full agreed story is actually written")
    report["stats"] = {"scene_count": len(scenes), "shot_count": len(shots),
                       "story_frames": total_frames, "story_seconds": seconds(total_frames, fps),
                       "fps": fps, "dialogue_count": utterances, "body_cjk_chars": body_chars}
    report["valid"] = not errors
    return report


def is_post(row):
    return row[2] == 0 or "纯后期" in row[11] or "pure post" in row[11].lower()


def offscreen(speaker):
    return any(x in speaker.lower() for x in ("画外", "录音", "未来声", "电话", "旁白", "voice-over", "offscreen", "recording", "(v.o.)", "(o.s.)"))


def voice_schedule(lines, duration_frames, fps, cue_for_shot):
    """Reserve reusable audio exactly, preserving the written dialogue sequence."""
    fixed, result = [], {}
    for index, line in enumerate(lines):
        cue = next((c for c in cue_for_shot if c["text"] == line["text"]), None)
        if cue:
            a = frames(cue.get("local_in_sec", 0), fps)
            b = a + frames(cue["duration_sec"], fps)
            result[index] = (a, b, cue)
            fixed.append((index, a, b))
    prior_index, prior_end = -1, 0
    for fixed_index, fixed_start, fixed_end in sorted(fixed) + [(len(lines), duration_frames, duration_frames)]:
        ordinary = list(range(prior_index+1, fixed_index))
        available = fixed_start-prior_end
        if available < len(ordinary):
            raise FilmError("Recurring audio conflicts with written dialogue order")
        desired = [max(1, math.ceil(spoken_seconds(lines[i]["text"])*fps)) for i in ordinary]
        lead = min(round(.35*fps), max(0, available-sum(desired))) if prior_end == 0 else 0
        cursor = prior_end + lead
        scale = min(1, (available-lead)/max(1, sum(desired)))
        for order, (index, wanted) in enumerate(zip(ordinary, desired)):
            remaining = len(ordinary)-order-1
            length = min(max(1, int(wanted*scale)), fixed_start-cursor-remaining)
            result[index] = (cursor, cursor+length, None)
            cursor += length
        prior_index, prior_end = fixed_index, fixed_end
    return result


def compile_film(data, source_sha256=""):
    report = validate_film(data)
    if not report["valid"]:
        raise FilmError("Invalid screenplay:\n" + "\n".join(report["errors"]))
    data = copy.deepcopy(data)
    options = project_options(data)
    fps, max_clip = options["fps"], frames(options["max_clip_seconds"], options["fps"])
    chars = {a["id"]: a for a in data["characters"]}
    props = {a["id"]: a for a in data["props"]}
    locations = {a["id"]: a for a in data["locations"]}
    assets = {**chars, **props}
    cues = data.get("recurring_audio_cues", [])
    source_rows = {f"S{sc['n']:02}_{j:03}": row for sc in data["scenes"] for j, row in enumerate(sc["shots"], 1)}
    cue_map = {}
    for cue in cues:
        for key in ("source_shot", "heard_shot"):
            cue_map.setdefault(cue[key], []).append(cue)
    shots, scenes, dialogue, clips = [], [], [], []
    cursor = 0
    for scene in data["scenes"]:
        n, start, utterances = scene["n"], cursor, 0
        for j, row in enumerate(scene["shots"], 1):
            duration, size, lens, camera, picture, say, sound, cut, first, last, visible, special = row
            sid = f"S{n:02}_{j:03}"
            count = frames(duration, fps)
            override = scene.get("shot_overrides", {}).get(str(j), {})
            location = locations[override.get("location_id", scene["location_id"])]
            wardrobe = {**scene["costumes"], **override.get("costumes", {})}
            effective = {key: override.get(key, scene[key]) for key in ("space", "axis", "light", "continuity")}
            lines = [{"speaker": speaker, "text": text, "kind": "原创剧本", "unit": j,
                      "direction": "画外/独立音轨" if offscreen(speaker) else "现场对白"} for speaker, text in say]
            for line in lines:
                cue = next((c for c in cue_map.get(sid, []) if c["text"] == line["text"]), None)
                if cue and sid == cue["heard_shot"]:
                    line["direction"] = "复用来源原声；听者不做口型"
                    line["voice_source_shot"] = cue["source_shot"]
                    line["voice_source_speaker"] = next(x[0] for x in source_rows[cue["source_shot"]][5] if x[1] == cue["text"])
            voice_ids = [a["id"] for a in data["characters"] if any(a["name"] in d.get("voice_source_speaker", d["speaker"]) for d in lines)]
            pure = is_post(row)
            if pure:
                strategy = "纯后期镜：人工文字、静帧、淡变或批准旧素材合成；保留成片时间，不提交AI视频。"
            elif lines and all(offscreen(d["speaker"]) or d.get("voice_source_shot") for d in lines):
                strategy = "声音全部独立制作或复用；可见人物只做所写反应，不对画外声音做口型。"
            elif lines:
                strategy = "先录完整表演；仅现场可见说话者匹配口型，录音与画外声不驱动听者嘴部。"
            else:
                strategy = "批准首帧后制作单一主要行动；复杂人、物、水火接触分层，按尾帧校验衔接。"
            locks = []
            for aid in visible:
                a = assets[aid]
                if aid in chars:
                    locks.append(f"{aid} {a['name']}：{a['appearance']}；衣装{wardrobe[aid]}：{a['costumes'][wardrobe[aid]]}")
                else:
                    locks.append(f"{aid} {a['name']}：{a['design']}")
            prompt = "\n".join([
                f"原创电影画面；画幅{options['aspect_ratio']}；{fps}fps运动观感。仅生成画面，音声另制；准确文字后期贴合。",
                "只呈现列出的可见身份与部位；画外人不自动入镜。",
                "可见资产：" + ("、".join(visible) or "批准环境与明确群众参考"), *locks,
                f"所属场：{scene['heading']}。本镜地点：{location['name']}。故事时间：{scene['story_day']}。",
                "环境：" + location["look"], "空间：" + effective["space"], "轴线：" + effective["axis"],
                "灯光：" + effective["light"], f"{size}；全画幅等效{lens}mm；摄影机：{camera}。",
                f"设计可用时长{duration}秒。首帧：{first}", "动作与表演：" + picture,
                "尾帧：" + last, "连续：" + effective["continuity"], "限制：" + special, "方法：" + strategy,
            ])
            if pure:
                prompt = "后期任务，不提交新视频生成。\n" + picture + "\n" + special
            shot = {"id": sid, "scene": n, "scene_heading": scene["heading"], "index": j,
                    "duration_sec": seconds(count, fps), "duration_frames": count,
                    "start_sec": seconds(cursor, fps), "end_sec": seconds(cursor+count, fps),
                    "in_tc": tc(cursor, fps), "out_tc_exclusive": tc(cursor+count, fps),
                    "first_frame": cursor, "end_frame_exclusive": cursor+count,
                    "size": size, "lens_mm_equiv": lens, "camera": camera, "picture": picture,
                    "source_refs": [j], "source_ref": f"scenes[{n-1}].shots[{j-1}]", "say_refs": [j] if lines else [],
                    "dialogue": lines, "sound": sound, "transition": cut, "special": special,
                    "first_anchor": first, "last_anchor": last, "asset_ids": visible,
                    "voice_asset_ids": voice_ids, "stage": scene["story_day"], "strategy": strategy,
                    "prompt": prompt, "image_prompt": prompt + "\n本次仅制作静态首帧，不能把多个时刻拼成一图。",
                    "negative_prompt": NEGATIVE, "pure_post": pure, "effective_location": location["name"],
                    **{"effective_"+k: v for k, v in effective.items()}}
            segments = 0 if pure else math.ceil(count / max_clip)
            shot["generation_units"] = segments
            local = 0
            for k in range(segments):
                length = count // segments + (1 if k < count % segments else 0)
                cid = f"{sid}_G{k+1:02}"
                fr = first if k == 0 else f"沿用{sid}_G{k:02}批准尾帧，不重置动作、衣装或位置"
                lr = last if k == segments-1 else "在自然连续动作中间止帧；中间锚点需低清动态预演批准"
                clips.append({"id": cid, "shot": sid, "scene": n, "part": k+1, "parts": segments,
                              "clip_duration_sec": seconds(length, fps), "clip_duration_frames": length,
                              "shot_local_in_sec": seconds(local, fps), "shot_local_out_sec": seconds(local+length, fps),
                              "global_in_sec": seconds(cursor+local, fps), "global_out_sec": seconds(cursor+local+length, fps),
                              "first_frame": cursor+local, "end_frame_exclusive": cursor+local+length,
                              "first_rule": fr, "last_rule": lr, "status": "未生成；待资产和动态预演批准",
                              "prompt": prompt + f"\n只制作第{k+1}/{segments}段，镜内{seconds(local, fps)}—{seconds(local+length, fps)}秒。首：{fr}。尾：{lr}。不重演整镜。"})
                local += length
            schedule = voice_schedule(lines, count, fps, cue_map.get(sid, []))
            for k, line in enumerate(lines):
                a, b, cue = schedule[k]
                did = f"{sid}_D{k+1:02}"
                filename = f"{data['slug']}_{cue['id']}_master.wav" if cue else f"{data['slug']}_{did}_v001.wav"
                rule = (f"先制作来源{cue['source_shot']}，在{cue['heard_shot']}原样复用同一完整音频，不重录。" if cue else "暂定区间；先录完整表演再校准")
                dialogue.append({**line, "id": did, "scene": n, "shot": sid,
                                 "start_sec": seconds(cursor+a, fps), "end_sec": seconds(cursor+b, fps),
                                 "first_frame": cursor+a, "end_frame_exclusive": cursor+b,
                                 "planned_cjk_per_sec": round(cjk(line["text"])/max((b-a)/fps, .001), 3),
                                 "note": rule, "suggested_file": filename, "recurring_audio_id": cue["id"] if cue else None})
            shots.append(shot)
            cursor += count
            utterances += len(lines)
        scenes.append({**{k: v for k, v in scene.items() if k not in ("n", "shots")}, "scene": n,
                       "budget_sec": seconds(cursor-start, fps), "start_sec": seconds(start, fps),
                       "end_sec": seconds(cursor, fps), "in_tc": tc(start, fps), "out_tc_exclusive": tc(cursor, fps),
                       "first_frame": start, "end_frame_exclusive": cursor,
                       "shot_count": len(scene["shots"]), "dialogue_count": utterances,
                       "added_line_count": 0, "source_unit_count": len(scene["shots"]),
                       "look": locations[scene["location_id"]]["look"], "method": data["production"]["ai_workflow"]})
    dialogue.sort(key=lambda d: (d["first_frame"], d["id"]))
    credit_frames = frames(options["credits_seconds"], fps)
    meta = {**report["stats"], **options, "title": data["title"], "slug": data["slug"], "genre": data["genre"],
            "logline": data["logline"], "source_sha256": source_sha256, "schema_version": VERSION,
            "total_story_frames": cursor, "credits_seconds": seconds(credit_frames, fps),
            "total_seconds": seconds(cursor+credit_frames, fps), "source_units": len(shots),
            "original_dialogue_spoken": len(dialogue), "added_dialogue_count": 0, "generation_units": len(clips),
            "status": "完整输入的制作设计；时间为预剪辑值，未生成媒体、未配音或锁片"}
    return {"meta": meta, "creative": {k: v for k, v in data.items() if k != "scenes"},
            "assets": {"characters": data["characters"], "props": data["props"], "locations": data["locations"], "vehicles": [],
                       "status": "文字资产设定；参考图尚未生成"}, "scenes": scenes, "shots": shots,
            "clips": clips, "dialogues": dialogue, "added_dialogues": [],
            "credits": {"id": "CRED_001", "duration_sec": seconds(credit_frames, fps),
                        "start_sec": seconds(cursor, fps), "end_sec": seconds(cursor+credit_frames, fps),
                        "in_tc": tc(cursor, fps), "out_tc_exclusive": tc(cursor+credit_frames, fps),
                        "picture": "纯后期演职员字幕规划，名单按实际参与者填写，不捏造署名。"}}


def json_text(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def csv_text(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    def safe(v):
        # User-authored strings are data, never spreadsheet formulas.
        if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
            return "'" + v
        return v
    writer.writerow(headers)
    writer.writerows([[safe(v) for v in row] for row in rows])
    return "\ufeff" + stream.getvalue()


def subtitle_lines(text, limit=36):
    def width(t):
        return sum(2 if "\u3400" <= c <= "\u9fff" else 1 for c in t)
    result, rest = [], " ".join(text.split())
    while width(rest) > limit:
        current, end = 0, 0
        for i, c in enumerate(rest):
            current += 2 if "\u3400" <= c <= "\u9fff" else 1
            if current > limit:
                break
            end = i+1
        split = end
        for k in range(end-1, max(0, end//2)-1, -1):
            if rest[k] in "，。！？；、：,.!?; ":
                split = k+1
                break
        result.append(rest[:split].strip())
        rest = rest[split:].strip()
    if rest:
        result.append(rest)
    return result or [""]


def subtitles(package):
    result, index = [], 1
    fps = package["meta"]["fps"]
    for d in package["dialogues"]:
        lines = subtitle_lines(d["text"])
        chunks = ["\n".join(lines[k:k+2]) for k in range(0, len(lines), 2)]
        weights = [max(1, len(x.replace("\n", ""))) for x in chunks]
        span = d["end_frame_exclusive"]-d["first_frame"]
        if len(chunks) > span:
            raise FilmError(f"{d['id']}: subtitle fragments exceed available frames; extend dialogue time")
        used, cumulative = 0, 0
        for k, (chunk, weight) in enumerate(zip(chunks, weights)):
            cumulative += weight
            end = span if k == len(chunks)-1 else max(used+1, min(span-(len(chunks)-k-1), round(span*cumulative/sum(weights))))
            a, b = d["first_frame"]+used, d["first_frame"]+end
            result.append(f"{index}\n{srt_stamp(a, fps)} --> {srt_stamp(b, fps)}\n{chunk}\n")
            used, index = end, index+1
    return "\ufeff" + "\n".join(result)


def screenplay(package):
    m, creative = package["meta"], package["creative"]
    out = [f"# {m['title']}", "完整剧本 / 拍前设计", creative["genre"], creative["logline"],
           "所有时长为预剪辑设计，须以实际表演和动态预演校准。", "## 人物"]
    for a in creative["characters"]:
        out.append(f"**{a['name']}，{a['age']}岁**。{a['want']} {a['arc']}")
    for sc in package["scenes"]:
        out.extend([f"## {sc['scene']:02} {sc['heading']}", sc["story_day"]])
        for shot in (s for s in package["shots"] if s["scene"] == sc["scene"]):
            out.append(shot["picture"])
            for d in shot["dialogue"]:
                out.append(f"**{d['speaker']}**\n\n{d['text']}")
    out.append("（全片完）")
    return "\n\n".join(out) + "\n"


def director_guide(package, notes=""):
    c, m = package["creative"], package["meta"]
    out = [f"# {m['title']} · 导演与AI制作总纲", notes.strip(), "## 核心故事", c["theme"], c["synopsis"], "## 世界规则"]
    out.extend("- " + x for x in c["world_rules"])
    out.append("## 结构与回收")
    for x in c["structure"]:
        out.append(f"**{x['scenes']}**：{x['cause']}\n\n回收：{x['payoff']}")
    out.append("## 制作设计")
    for k, label in (("palette", "色彩"), ("camera", "摄影"), ("sound", "声音"), ("music", "配乐"), ("ai_workflow", "AI方法")):
        out.append(f"**{label}**：{c['production'][k]}")
    out.append("优先预演：\n" + "\n".join("- " + x for x in c["production"]["priority_tests"]))
    out.append("## 连续性审查")
    for x in c["continuity_audit"]:
        out.append(f"**{x['thread']}**：{x['setup']} → {x['payoff']}。{x['result']}")
    out.extend(["## 版本与制作次序", f"{m['scene_count']}场、{m['shot_count']}镜、{m['story_seconds']}秒正片设计，片尾另计{m['credits_seconds']}秒。",
                "先批准角色/场景参考，再录对白并做低清动态预演。校准节奏后生成关键镜，再分批制作与合成。",
                f"采用{m['fps']}fps、画幅{m['aspect_ratio']}。镜头出点不含该帧；生成单元最多{m['max_clip_seconds']}秒只是拆分建议，实际需按模型能力调整。",
                "首尾帧是文字锚点，不是已绘图像。当前没有生成图像、视频、配音、音乐或影院发行母版。",
                "修改剧本、镜长、人物或衣装后，应从权威输入重新构建所有导出，不能只修改某个字幕或提示词快照。"])
    return "\n\n".join(x for x in out if x) + "\n"


def output_texts(package, report, notes):
    shots, voices, scenes, clips = (package[k] for k in ("shots", "dialogues", "scenes", "clips"))
    fps, slug = package["meta"]["fps"], package["meta"]["slug"]
    shot_map = {s["id"]: s for s in shots}
    chars = package["assets"]["characters"]
    out = {"screenplay.md": screenplay(package), "director-guide.md": director_guide(package, notes),
           "shot-plan.json": json_text(package), "assets.json": json_text(package["assets"]),
           "validation.json": json_text(report), "subtitles.srt": subtitles(package)}
    out["shots.csv"] = csv_text(["shot_id", "scene", "in_tc", "out_tc_exclusive", "duration_sec", "size", "lens_mm", "camera", "picture", "dialogue", "sound", "transition", "first_anchor", "last_anchor", "visible_assets", "voice_assets", "special", "source_ref"],
        [[s["id"], s["scene"], s["in_tc"], s["out_tc_exclusive"], s["duration_sec"], s["size"], s["lens_mm_equiv"], s["camera"], s["picture"], "\n".join(d["speaker"]+"："+d["text"] for d in s["dialogue"]), s["sound"], s["transition"], s["first_anchor"], s["last_anchor"], " ".join(s["asset_ids"]), " ".join(s["voice_asset_ids"]), s["special"], s["source_ref"]] for s in shots])
    rows = []
    for d in voices:
        char = next((a for a in chars if a["name"] in d.get("voice_source_speaker", d["speaker"])), None)
        rows.append([d["id"], d["shot"], d["speaker"], d["start_sec"], d["end_sec"], d["first_frame"], d["end_frame_exclusive"], d["text"], char["voice"] if char else "按本片独立声音角色设定", d["note"], d["suggested_file"], shot_map[d["shot"]]["sound"]])
    out["dialogue.csv"] = csv_text(["dialogue_id", "shot_id", "speaker", "start_sec", "end_sec_exclusive", "first_frame", "end_frame_exclusive", "text", "voice_identity", "recording_or_reuse", "suggested_file", "sound_space"], rows)
    out["edit-markers.csv"] = csv_text(["shot_id", "start_sec", "end_sec_exclusive", "first_frame", "end_frame_exclusive", "fps", "picture"], [[s["id"], s["start_sec"], s["end_sec"], s["first_frame"], s["end_frame_exclusive"], fps, s["picture"]] for s in shots])
    out["generation.csv"] = csv_text(["unit", "shot", "start_sec", "end_sec_exclusive", "duration_sec", "first_frame", "end_frame_exclusive", "first_rule", "last_rule", "prompt", "status", "suggested_file"], [[c["id"], c["shot"], c["global_in_sec"], c["global_out_sec"], c["clip_duration_sec"], c["first_frame"], c["end_frame_exclusive"], c["first_rule"], c["last_rule"], c["prompt"], c["status"], f"{slug}_{c['id']}_v001.mov"] for c in clips])
    refs = []
    for a in chars:
        for stage, clothing in a["costumes"].items():
            refs.append([f"{a['id']}_{stage}", "character", a["name"], stage, f"{a['appearance']}；{clothing}", "各视角单独制作：正面、左右侧、四分之三、背面、全身", f"原创人物参考：{a['appearance']}。衣装：{clothing}。中性背景，同一身份自然比例；无多个时刻拼图。", "未生成"])
    for key in ("props", "locations"):
        for a in package["assets"][key]:
            detail = a.get("design", a.get("look", "")) + ("；" + a["geography"] if "geography" in a else "")
            refs.append([a["id"], key, a["name"], "fixed", detail, "主视角、左右侧与结构细节，场景另做无人全景", "原创电影参考：" + detail + "。准确文字后期排版，不新增人物或随机标识。", "未生成"])
    out["asset-references.csv"] = csv_text(["reference_id", "type", "name", "stage", "design_lock", "views", "prompt", "status"], refs)
    out["sound-cues.csv"] = csv_text(["scene", "heading", "in_tc", "out_tc_exclusive", "space", "shot_sound_design", "music_basis"], [[s["scene"], s["heading"], s["in_tc"], s["out_tc_exclusive"], s["sound"], " / ".join(dict.fromkeys(x["sound"] for x in shots if x["scene"] == s["scene"])), package["creative"]["production"]["music"]] for s in scenes])
    recurring = []
    for c in package["creative"].get("recurring_audio_cues", []):
        recurring.append([c["id"], c["text"], c["source_shot"], c.get("source_story_time", ""), c["heard_shot"], c.get("heard_story_time", ""), c.get("local_in_sec", 0), c["duration_sec"], f"{slug}_{c['id']}_master.wav", c.get("notes", ""), "先制作真实来源，回放复用同一完整音频，不重新TTS"])
    # Always emit the table header so obsolete rows cannot survive an overwrite.
    out["recurring-audio.csv"] = csv_text(["cue_id", "exact_text", "source_shot", "source_story_time", "heard_shot", "heard_story_time", "local_in_sec", "duration_sec", "master_file", "notes", "rule"], recurring)
    template = Path(__file__).resolve().parent.parent / "assets" / "workbench-template.html"
    if not template.is_file():
        raise FilmError("Missing bundled assets/workbench-template.html")
    links = [{"path": name, "label": name} for name in sorted(out)]
    payload = {"package": package, "notes": out["director-guide.md"], "files": links}
    embedded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    replacements = {"TITLE": html.escape(package["meta"]["title"]), "DATA": embedded}
    out["index.html"] = re.sub(r"__(TITLE|DATA)__", lambda m: replacements[m.group(1)], template.read_text(encoding="utf-8"))
    return out


def reject_linked_output(path):
    """Check before resolve(), which would otherwise hide a linked ancestor."""
    absolute = Path(path).absolute()
    for entry in [absolute, *absolute.parents]:
        if entry.is_symlink() or (hasattr(entry, "is_junction") and entry.is_junction()):
            raise FilmError("Output path must not contain symlinks or directory junctions")


def build_package(input_path, out, notes_path=None, overwrite=False):
    reject_linked_output(out)
    source, dest = Path(input_path).resolve(), Path(out).resolve()
    data = read_json(source)
    report = validate_film(data)
    if not report["valid"]:
        raise FilmError("Invalid screenplay:\n" + "\n".join(report["errors"]))
    if dest.exists() and not dest.is_dir():
        raise FilmError("Output must be a directory")
    if dest.exists() and any(dest.iterdir()) and not overwrite:
        raise FilmError("Output directory is not empty; choose a new directory or use --overwrite for owned files only")
    for name in OWNED:
        target = dest / name
        if target.resolve() == source:
            raise FilmError("Output would overwrite the authoritative input; choose a separate output directory")
        if notes_path and target.resolve() == Path(notes_path).resolve():
            raise FilmError("Output would overwrite the authoring notes; choose a separate output directory")
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise FilmError(f"Refusing to overwrite non-regular output entry: {name}")
    notes = ""
    if notes_path:
        try:
            notes = Path(notes_path).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise FilmError(f"Cannot read notes: {exc}") from exc
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    package = compile_film(data, sha)
    texts = output_texts(package, report, notes)
    manifest = {"schema_version": VERSION, "source_sha256": sha, "media_generated": False,
                "validation": {"errors": len(report["errors"]), "warnings": len(report["warnings"])},
                "files": [{"path": name, "bytes": len(text.encode("utf-8")), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()} for name, text in sorted(texts.items())],
                "optional_artifacts": "PDF/XLSX are created separately by the bundled artifact exporters; this manifest covers core outputs only."}
    texts["manifest.json"] = json_text(manifest)
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in texts.items():
        (dest / name).write_text(content, encoding="utf-8", newline="")
    return {"title": package["meta"]["title"], "files": len(texts), "stats": report["stats"],
            "warnings": report["warnings"], "media_generated": False}


def init_project(theme, path, kind, minutes):
    reject_linked_output(path)
    dest = Path(path).resolve()
    if not nonempty(theme) or not number(minutes) or minutes <= 0:
        raise FilmError("Theme must be nonempty and minutes must be positive")
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        raise FilmError("Project directory must be new or empty; init never overwrites authoring work")
    slug = re.sub(r"[^a-z0-9]+", "-", dest.name.lower()).strip("-") or "new-story"
    data = {"schema_version": VERSION, "authoring_status": "incomplete", "slug": slug, "title": "",
            "genre": "", "logline": "", "theme": theme, "synopsis": "", "world_rules": [],
            "characters": [], "props": [], "locations": [], "structure": [],
            "production": {"palette": "", "camera": "", "sound": "", "music": "", "ai_workflow": "", "priority_tests": []},
            "continuity_audit": [], "recurring_audio_cues": [], "scenes": [],
            "project": {**DEFAULTS, "format": kind, "target_minutes": minutes,
                        "credits_seconds": 120 if kind == "feature" else 30}}
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "film.json").write_text(json_text(data), encoding="utf-8")
    (dest / "progress.json").write_text(json_text({"status": "incomplete", "theme": theme,
         "format": kind, "planned_minutes": minutes, "completed_scenes": 0,
         "next_step": "Write the original story, complete scenes and actual dialogue before production export."}), encoding="utf-8")
    return {"status": "incomplete", "files": ["film.json", "progress.json"],
            "message": "Scaffold only. No screenplay or media has been generated."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create an explicitly incomplete authoring scaffold")
    init.add_argument("--theme", required=True)
    init.add_argument("--project", required=True)
    init.add_argument("--format", choices=("feature", "short", "episode"), default="feature")
    init.add_argument("--minutes", type=float, default=None)
    val = sub.add_parser("validate", help="Validate an authored film.json")
    val.add_argument("input")
    val.add_argument("--report")
    build = sub.add_parser("build", help="Build an offline production package from completed authoring")
    build.add_argument("input")
    build.add_argument("--out", required=True)
    build.add_argument("--notes")
    build.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            minutes = args.minutes if args.minutes is not None else {"feature": 100, "short": 10, "episode": 40}[args.format]
            result = init_project(args.theme, args.project, args.format, minutes)
        elif args.command == "validate":
            result = validate_film(read_json(args.input))
            if args.report:
                target = Path(args.report)
                if target.resolve() == Path(args.input).resolve():
                    raise FilmError("Report must not overwrite the source input")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json_text(result), encoding="utf-8")
            print(json_text(result), end="")
            return 0 if result["valid"] else 2
        else:
            result = build_package(args.input, args.out, args.notes, args.overwrite)
        print(json_text(result), end="")
        return 0
    except (FilmError, OSError, InvalidOperation) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
