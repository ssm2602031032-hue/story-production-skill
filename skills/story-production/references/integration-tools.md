# 长篇、提示词回归与媒体工具

这些工具按当前任务调用。小说和文本检查只需Python 3.10+；分析实际视频或导出OTIO时才需要可选依赖。所有命令从 `skills/story-production` 目录运行；`project/`替换为用户的实际项目路径，输出不要写进已安装Skill。

## 长篇上下文与改编

输入是本包[小说规范](story-schema.md)的 `novel.json`，不是任意TXT。需要先把已有书稿保持原文导入相应章节结构。章节编号沿用源稿。

```text
python scripts/chapter_context.py project/novel.json --chapter 2 --purpose continue --window 2 --max-chars 16000 --out project/context-C002.json
python scripts/chapter_context.py project/novel.json --chapter 2 --purpose reader --out project/reader-C002.json
```

`continue`只引用前文正文，`revise`含目标章，`reader`不带作者设定、结局规划或事实账。可用 `--ledger project/creative-ledger.json` 带入有效事实账；过期/无效账会排除并警告。作者资料包也会提示“声明完成但章数未齐”的矛盾；地点引用与正文是否相符仍需阅读审查。字符上限只约束所选正文，整章放不下会告警；当前章超限则失败。不会生成小说，也不会把提案变成正史。

写作方法见[章节契约](modules/novel-context-packs.md)。改编时另建事件到集/场的映射，按[改编覆盖](modules/adaptation-beat-transfer.md)保留因果，正文写完再接制作管线，不以覆盖表冒充剧本。

## 提示词离线回归

```text
python scripts/prompt_regression.py --out project/prompt-regression-v1
```

进入导出目录后，用已安装的Promptfoo运行：

```text
promptfoo eval -c promptfooconfig.yaml --no-cache --no-write -o eval-results.json
```

导出包括配置、Python离线provider、独立规则文件和哈希清单，不需要API密钥。`--no-write`不保存到Promptfoo本地评估数据库，`-o`仍保存这次结果。测试涵盖5个文本契约场景；坏提示词正确返回FAIL也算测试通过。导出动作本身不代表已运行Promptfoo。provider内没有网络请求或模型调用。

本次实际运行环境：Promptfoo 0.125.1、Node 24.22.1，5例全部通过。首次临时安装遇到 `@nodable/entities` 缺失；在隔离目录显式补齐该依赖并使用hoisted安装后运行成功。依赖安装仍应以目标环境的官方要求为准，不保证任何版本的临时安装都直接成功。不要为运行本套离线测试自动替换在线provider。

测试和[真实摄影对照](modules/realism-diagnostics.md)分开；[提示词回归模块](modules/prompt-regression.md)说明如何加入项目案例。

## 可选媒体环境

在选定的项目虚拟环境安装，而不修改用户全部项目：

```text
python -m pip install -r scripts/requirements-media.txt
```

仅核对视频参数与OTIO，可按该文件版本范围只安装PyAV和OpenTimelineIO。切点检测另外需要PySceneDetect和OpenCV。Faster Whisper和VBench模型不在此依赖列表，不会自动下载。上游代码、模型和编解码器依赖各有许可，项目资料表不代替其发行许可。

## 检查真实视频

```text
python scripts/media_qc.py project/media/shot01.mp4 --fps 24 --width 1920 --height 1080 --out project/shot01-qc.json
python scripts/media_qc.py project/media/shot01.mp4 --max-frames 0 --fps 24 --detect-cuts --out project/shot01-full-qc.json
```

`--frames`可增加预期总帧数。默认240帧只检查开头，`--max-frames 0`全解码。切点检测会另行处理全片，不受开头采样上限限制。报告含源哈希、实际视频/音轨元数据、解码范围、时间戳和粗略重复/近黑告警；不会评价皮肤、身份、表演或口型。

不能把合法固定机位判作坏冻结，也不能把闪光候选自动当成剧情换场。见[技术检查](modules/technical-media-qc.md)、[切点复核](modules/scene-detection-review.md)和[VBench指标边界](modules/video-metric-reading.md)。

## 已有识别结果与字幕

输入示例 `project/segments.json`，时间单位秒：

```json
{"segments":[{"start":0.25,"end":1.1,"text":"你好。"},{"start":1.3,"end":2.2,"text":"请进。"}]}
```

```text
python scripts/subtitle_tools.py import-asr project/segments.json --out project/recognized.srt
python scripts/subtitle_tools.py check project/recognized.srt --duration 2.5 --report project/subtitle-qc.json
```

只导入已经获得的识别段，按SRT毫秒精度保留区间，同时生成 `.import.json` 说明来源和局限。不运行识别模型、不虚构逐词时间，不宣称与嘴型同步。生成片的录音未完成时继续使用明确标注的暂定字幕。读[字幕校时](modules/subtitle-alignment.md)后再处理真实录音差异。

## 实际OTIO画面时间线

先由 `film_pipeline.py build` 得到项目输出中的 `shot-plan.json`。在 `project/media-map.json` 按镜头ID填写已生成、已选用的媒体：

```json
{"S01_001":{"path":"media/shot01.mp4","source_in_frame":0}}
```

路径相对于映射JSON所在目录；完整工程应列齐计划中的所有镜头。本包当前镜头计划使用整数fps（例如24/25/30），暂不直接导出29.97等分数帧率工程。输入媒体的实际帧率必须匹配剪辑fps；工具不变速，不做帧插值。每段素材全解码并验证所取区间。

```text
python scripts/editorial_export.py project/output/shot-plan.json --media-map project/media-map.json --out project/edit-v1.otio
```

若明确需要缺素材的规划工程：

```text
python scripts/editorial_export.py project/output/shot-plan.json --allow-missing --out project/planning-v1.otio
```

规划工程使用真正MissingReference，标明缺失镜头。工程齐全也只表示画面组装，未混音、调色、渲染或验收创作。重新打开OTIO核对总帧数是已实现的检查；目标剪辑软件的插件导入仍要实际试验。详见[剪辑交接](modules/editorial-handoff.md)。

## 可复现的验证范围

仓库标准库测试覆盖上下文、字幕和离线provider等。安装可选媒体依赖后，用同一测试命令会额外运行实际CPU测试：创建48帧24fps的双色技术片段，真实解码、检测切点、导出并重开OTIO，以及错误fps、帧范围和缺失引用处理。测试素材不是模型生成视频，不作摄影质量样本。

本次测试过PyAV 17.1.0、OpenTimelineIO 0.18.1、PySceneDetect 0.7.2。声明的兼容范围不等于每个中间版本都测试过。未运行GPU视频生成、Faster Whisper识别或VBench评分；这些项目只整合方法、接口和适用边界。

全部新来源、固定commit、文档SHA256、许可和采用内容见[项目资料表](../assets/integration-projects.json)。运行生成/付费API和公开作品仍按当前用户的实际授权执行。
