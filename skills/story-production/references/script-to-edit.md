# 剧本编写、转化、提示词与当前情境剪辑

这里衔接已经写出的小说/剧本、视觉契约、生成任务与剪辑决定。新作品仍需要创作完整正文，不能用本工具的表格代替写戏。已有作品只改指定范围；不默认车型、校园、爱情主线或某个平台的快切公式。

## 写作与转化的四层

1. **戏剧层**：人物此刻想要什么、什么阻止他、采取什么策略、结果怎样改变下一步。描写的是实际选择和后果，不必每场都用强反转。
2. **改编层**：原文哪些事件保留、合并、移位、外化或省略；原文依据与新写决定分别记录。因果前提被删时给出替代，不用字幕或旁白糊过去。
3. **视听层**：用可见行为、空间、物件、对白、画外音或主观声音表达。内心戏不强制全部改成脸部大表情；也不把作者分析塞进可见提示词。
4. **剪辑层**：按当前场景的问题、观众已知信息、动作完成态和反应决定切点。动作片也可以有安静对话，爱情片也可以有紧急行动；整片类型不等于每场同样剪。

## 情境策略库

`assets/scene-edit-policies.json`提供10种策略：dialogue、suspense、comedy、romance、action、exposition、montage、product、documentary、contemplative。每种列出注意中心、切点触发、该保留的部分、常见误剪与声音作用；没有统一镜头秒数或自动留存率保证。

选择依据是这场此刻在做什么。悬疑要保护揭示顺序；喜剧要保留铺垫与反应；动作要看清目标和接触；说明要给信息可读时间；静观要有真实变化。若情境变化，更新该场策略并重新看时长/覆盖需求，不只替换类型标签。

## 从源稿建立映射

源稿使用本包的novel.json、film.json或series.json。锚点分别为C001、S01_001、E001/S01_001等；影视场级锚点不与镜级重复计算。来源带文件哈希，剧集还记录各集文件指纹。命令从Skill目录运行，项目放在用户工作目录。

```text
python scripts/script_bridge.py init project/novel.json --visual project/visual.json --out project/bridge.json
python scripts/script_bridge.py init project/series.json --scope E001/S01_001 E001/S01_002 --visual project/visual.json --out project/selected-bridge.json
```

init只建空骨架和可用锚点，不写正文、不自动判断戏剧节拍。明确局部任务用selected范围；full表示所有源单元都需要记录去向，但一个章节有一条引文不证明章内全部内容都被改编。覆盖率只发现记录缺口，仍须通读原稿和改编稿。

参考完整小样：`assets/example-bridge-source.json`、`assets/example-bridge-visual.json`、`assets/example-script-bridge.json`。它展示一章中的三个镜头和明确省略的开门余波，不是长片或全章逐句改编证明。

### bridge主要字段

|字段|记录什么|工具能核对什么|
|---|---|---|
|source_fingerprint / visual_sha256|当前原文与视觉版本|改稿、分集变化或分镜变化后提示过期|
|scope_mode / scope|全源单元或指定局部|不把漏章漏镜藏成全量完成|
|beats|原文短引、目标/阻力/行动/后果、改编方式、目标镜头、前因|精确引文、缺失目标、因果环、删除前因后的补救说明|
|anchor_omissions|整源单元省略及原因|已省略与已覆盖冲突、无去向的源单元|
|scenes|当前情境、核心问题、变化、视点、剪辑意图|有效情境键与必需的作者决定|
|shot_links|每镜的功能、观众前后知道什么、切点、替代覆盖、保护区间|每个生成镜头有记录，区间不超过镜长|
|boundaries|相邻镜的交出/接收状态、动机、声音桥|每个相邻对恰有一项，不用非相邻镜冒充接续|
|dialogue|原台词依据、实际台词、说话者、镜内/画外/旁白、时段与计时依据|擅改台词未说明、可见说话者缺席、时间越界|
|reveal_order|必须先呈现与后呈现的事件及理由|不能以倒叙的名义无说明地提前消费揭示|

改编方式treatment为preserve/externalize/merge/move/omit。非preserve需要adaptation_note；omit不能宣称有目标镜头。depends_on表示故事前因，未必要求按时间顺序播放；reveal_order才约束必须保留的呈现先后。依赖被省略时，dependency_repair只记录作者补救方案，仍需人工核对它真的在改编稿中成立。

对白spoken_text与quote不同需要change_reason。delivery为visible时绑定speaker_asset，它必须在该视觉镜头里可见；offscreen/voiceover不强迫人物入画。计时basis为estimate/readthrough/recorded，后两者需要具体证据说明，但工具不会凭说明自动验证录音文件。语速高只产生读演提示，不自动加速或删台词。

## 生成分层提示词包

```text
python scripts/script_bridge.py audit project/novel.json --visual project/visual.json --bridge project/bridge.json --out project/bridge-check.json
python scripts/script_bridge.py build project/novel.json --visual project/visual.json --bridge project/bridge.json --out project/scene-production-v1
```

输出包含：

- `director-and-prompts.md`：给作者看的原文依据、场景问题、可见提示词、对白和切点。
- `shot-packages.json`：结构化来源链、视觉条件、独立声音台词、当前情境策略与待验证项。
- `visual-directives.json`：可传入已有video_prompt_tools的`--directives`；仅在当前视觉ID与生成任务ID一致时使用。
- `reference-map.json`及已绑定的`references/`：实际批准参考图会复制并核对哈希，可传入模型工作包的`--references`；缺失参考不会凭空补齐。
- `dialogue-track.json`：准确台词与暂定时间，不伪称已生成配音。
- `source-shot-map.csv`、校验与哈希清单。

可见提示词复用视觉契约的身份、状态、起止动作、机位、光线和材质。对白全文留在单独轨道，可见发声者只作为画面表演提示。支持原生对白的模型还需其真实格式适配；本工具不凭泛化句式保证口型，不能把单独配音声明当成已完成。

参考图绑定继续使用visual_contracts的真实角色与覆盖记录，不重新生成或捏造图片。更短提示词是否合适由模型和场景决定：先保住身份、核心动作、空间和首尾状态，删重复形容而非删必要逻辑。“全面”体现在信息分层完整，不等于每个模型输入一大段导演分析。

## 剪辑是否保住当前场景

在shot_links的protected_windows中标出这次必须保留的动作/线索/反应区间，单位是该视觉job内部的设计秒数，例如：

```json
{"id":"M2","in_sec":0.5,"out_sec":2.5,"reason":"必须看见先握稳再松手，不能让物品瞬移"}
```

这些时刻是设计值；真实生成片段可能偏移。选定take后先看实际素材，把设计事件与take的时间位置对齐，再填写映射。若动作发生时段不同，应修订契约/保护区间并说明原因，不能凭旧计划机械判定。

```text
python scripts/context_edit.py init --visual project/visual.json --bridge project/bridge.json --edit project/edit.json --out project/alignment.json
```

每个clips项对应edit.json的实际画面cut：`id`、`job`、`source_zero_frame`、`evidence`。source_zero_frame表示该job第0帧对应到实际源文件的帧号；只有同fps、1倍速、连续区间映射受支持。init可以从明确的story_ref猜job，但evidence留空，必须检查实际take后填写。未实际看素材时不能写成“已核准”。

```text
python scripts/context_edit.py audit --source project/novel.json --visual project/visual.json --bridge project/bridge.json --edit project/edit.json --alignment project/alignment.json --out project/context-edit-check.json
```

工具检查已声明的帧映射：关键区间有没有被剪掉、倒置或重复，揭示有没有提前，删镜/重排后是否补写了新的交出与接收关系。新的邻接在boundary_decisions填from_cut/to_cut/reason/handoff/receive/audio_note。原顺序不变时沿用既有边界设计。

此审查不解码媒体，media_checked=false；不能把它当最终电影质量认证。它也不自动修改剪辑或渲染音频。实际渲染、音轨、字幕和颜色验收继续使用已有剪辑手册。J/L声桥使声音与画面时序不同，不能仅凭画面区间判断某句对白是否被完整保留。

## 适用边界

这些脚本全为标准库检查，只有视觉契约包含真实参考图时才用已有Pillow验证图像。没有调用语言/视频模型，没有机械生成完整剧本，没有把人工填写的字段当作艺术质量评分。每个机器结论都需结合真实源文、当前视频情境和观看结果。

来源Skill中的固定时长公式、固定生成次数、每场必须反转/每章必须母题三现、所有模型都只能某种动作、强制审批和强制英文不继承。具体作品按用户目标、实际内容、模型能力与测试结果推进。
