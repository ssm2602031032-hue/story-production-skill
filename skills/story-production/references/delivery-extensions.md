# 从创作到可交接文件

按需使用这些扩展，不要求每次创作都建所有记录。命令相对于本Skill目录；`project/`是用户项目。输出使用新版本路径，源稿不会被这些工具改写。研究事实、事件图和选片记录都由作者依据原文或实际媒体填写，工具不从未读材料自动认定事实。

## 研究资料与剧情记录

`narrative_checks.py evidence INPUT --out REPORT`核对来源ID、事实引用与摘录，并输出 `csl_json` 字段，供Citation.js等书目工具读取。不访问URL，不验证网页真实性，不自动补作者、日期或DOI。

```json
{"sources":[{"id":"R1","title":"现场记录","url":"https://example.org/report","accessed":"2026-11-01","excerpt":"实际读到的摘录。"}],"claims":[{"id":"C1","kind":"fact","statement":"用于剧情的事实","source_ids":["R1"],"used_at":["S03"],"quote":"实际读到的摘录。"}]}
```

上例仅展示字段，不是真实研究结论。`kind`可为fact/inference/fiction；推断另填reason。引文对不上提供的摘录会报错，匹配也不证明来源可信。

`narrative_checks.py graph INPUT --out REPORT`检查声明的先后依赖、循环和人物知情。输入的时间是同一条叙事因果轴上的数值，可用相对分钟；不要混用日期、屏幕时码和穿越后的世界日期。

```json
{"characters":["A","B"],"facts":[{"id":"F1","known_by":["A"]}],"events":[{"id":"N1","unit":"E001/S01","story_time":1,"reveals":[{"fact":"F1","to":["B"]}]},{"id":"N2","unit":"E001/S02","story_time":2,"requires":["N1"],"uses":[{"fact":"F1","by":"B"}]}]}
```

同一时间的获知只有明确依赖路径才算先发生；同场先获知再使用，拆成两个事件。倒叙不要求按事件发生顺序呈现。梦境、假消息、时间闭环应先定义独立语义模型，此检查不自动理解它们。

`narrative_checks.py season INPUT --out REPORT`检查整季/长篇的承诺记录：

```json
{"units":["E001","E002"],"promises":[{"id":"P1","setup":"E001","payoff":"E002","status":"resolved","evidence":"E002/S03具体兑现位置与原文证据"}]}
```

状态为planned/resolved/open-intentional；刻意留白填reason。列表是呈现顺序，不是故事时间。兑现证据需人工回到原文核对，工具不会把摘要或非空字段认证为好剧情。

## 小说完稿与电子书

```text
python scripts/publication_tools.py audit project/novel.json --out project/manuscript-audit.json
python scripts/publication_tools.py epub project/novel.json --out project/book-v1.epub --author "作者提供的署名"
```

audit只做既有结构检查、重复长段候选和行首尾空白报告，不自动改语句或凭敏感词删情节。EPUB包含真实全文、章节目录、书脊顺序、语言和源哈希标识；署名未提供就不填。未齐章或未完成的源稿不能冒充完整书输出。

导出器检查ZIP/XML结构；`epubcheck_run=false`表示本次导出命令没有运行外部EPUBCheck。发行前在实际环境运行官方EPUBCheck，并在阅读器检查目录、中文换行和章节顺序。仓库CI有独立的EPUBCheck步骤；一次样例通过不代表每一本未来输出都通过。

## 标准剧本文本

```text
python scripts/publication_tools.py screenplay project/film.json --out project/film-v1.fountain
python scripts/publication_tools.py screenplay project/film.json --out project/film-v1.fdx
```

Fountain为纯文本，中文人物使用显式角色标记；FDX实际调用Screenplain序列化为XML。保留场景、动作和逐句对白，不含镜头帧时码、媒体链接或完整制片资料，所以必须保留原film.json。可读/可解析不等于已在所有商业编剧软件导入；实际使用的软件仍应试开。此工具不支持任意FDX反向导入。

## 参考素材、选片与费用情景

先写 `registry-input.json` 指向实际文件：

```json
{"references":[{"id":"R1","role":"first-frame","path":"media/reference.png"}],"takes":[{"id":"T1","shot":"S01_001","path":"media/take01.mp4","references":["R1"],"source_in_frame":0}]}
```

```text
python scripts/production_registry.py capture project/registry-input.json --plan project/output/shot-plan.json --out project/registry-v1.json
```

capture实际计算文件与计划的SHA256，所有take均标candidate、选片为空。看完整素材后，作者把选中的take改为approved并填写review_note，再在selected中设置镜头ID到take ID。不是由工具根据漂亮缩略图自动批准。参考角色还可为identity/wardrobe/location/prop/depth/pose/mask/camera/last-frame；控制素材应填workflow_evidence，记录实际工作流支持和坐标约定。

```text
python scripts/production_registry.py check project/registry-v1.json --plan project/output/shot-plan.json --out project/take-check.json --media-map-out project/media-map.json
python scripts/production_registry.py estimate project/video-jobs.json --price-per-second 0.2 --attempts 3 --currency USD --out project/cost-scenario.json
```

指纹不符不能改哈希冒充原先已审素材；重新capture产生新候选记录，再审片。media-map输出应放在媒体的项目祖先目录，以维持安全相对路径。全部选齐才能导出映射，随后用既有editorial_export核对真实fps与帧范围。

费用输入是video_prompt_tools导出的video_jobs，按实际生成的native_duration_sec算，重试次数是用户设定的情景，不是成功率预测。单价为演示值，必须替换为实际服务计费标准；图片、音频、超分、存储、税费及人工另算。工具不会提交任务或收费。

## 画面、声音与翻译字幕

```text
python scripts/media_review.py contact project/media/take01.mp4 --samples 8 --out project/contact-v1.png
python scripts/media_review.py audio project/dialogue.wav --target-lufs -23 --out project/audio-qc.json
python scripts/subtitle_tools.py compare project/original.srt project/translated.srt --report project/localization-check.json
```

接触表来自实际解码帧，含首尾与均匀采样的帧号/时间；旁边的 `.frames.json` 记录媒体哈希。会完整解码计数再取样，长片较耗时。它不能发现未采样瞬间的错误，也不能代替连续播放。

音频检查只接受PCM16单/双声道WAV，测量真实时长、采样峰值、直流偏移、碰到量化上限的采样数和BS.1770积分响度。它不自动调整增益，不测真峰值或环绕布局。-23仅是命令示例，用户实际发行标准优先；无声/短于400ms时不伪造LUFS。任何增益建议要结合峰值和听感。

字幕compare要求一对一字幕条目；比较实际文字变更和时间偏移，不评价译文准确性。拆句合句需要先提供明确映射，不能借错误的条目顺序假装同步。配音和嘴型仍需实际录音预演。

## 可选依赖与验证范围

核心JSON检查、EPUB、Fountain与字幕比较只需Python 3.10+。FDX、图像接触表、音频测量按需安装 `scripts/requirements-delivery.txt` 的对应部分；视频接触表还需 `requirements-media.txt` 的PyAV。未安装依赖时工具会说明缺项，不能改扩展名伪造文件。

已测Screenplain 0.12.0的FDX序列化和中文Fountain解析，真实PCM测试及真实视频帧抽取。ControlNet、CameraCtrl只作控制条件方法参考，未安装模型或GPU实测；NetworkX、DVC、Citation.js不作为本包必需运行时。新增来源、许可证与固定文档哈希见[integration-projects.json](../assets/integration-projects.json)。
