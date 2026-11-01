# Story Production Skill

输入一个主题，让创作代理完成**小说全文、长篇电视剧或电影剧本与拍前制作全套**。

它把写作、连续性审校和可执行文件组织成一个可恢复的工作流程。电影与剧集可生成完整剧本、秒级分镜、角色与场景设定、首尾帧文字锚点、AI提示词、声音与字幕任务、阅读工作台和导出文件；小说保留独立的叙述正文，也支持进一步改编。

这是创作与拍前制作Skill。它不包含视频模型，不保证一次生成影院成片，也不会因为调用Skill就自动付费或公开用户作品。

## v1.1 创作技能整合

现在内置 **28个按需调用的创作模块**，不需要逐个安装。12个昆卡技能覆盖构思、人物、结构、场景、对白、连续性、改稿、风格、剧集、改编、格式和提案；16个扩展模块补上题材研究、世界规则、小说文风、喜剧、悬疑、爱情、动作、连载回报、类型混合、角色演练、读者模拟、视觉、声音、长篇记忆、制作约束与编剧室。

模块按当前任务分批加载。只改一句台词时不会默认重写整季；完整作品则按阶段继续完成正文与制作包。可查看[全部模块](skills/story-production/references/module-catalog.md)与[第三方来源及许可证](THIRD_PARTY_NOTICES.md)。整合参考固定于公开提交，日常调用不需要连接上游仓库。

新增请求示例：

```text
$story-production 只润色第三场对白，保留情节和镜长，让两个人的声音更有区别。
$story-production 审查这部穿越小说的规则漏洞和伏笔，不改正文，引用具体章号。
$story-production 把这个点子开发成12集爱情悬疑剧，人物、线索和每集兑现都要完整。
$story-production 给这部电影做视觉与声音方案，说明哪些镜头需要分层生成。
```

## 安装

在支持Skill安装的Codex中输入：

```text
使用 skill-installer，安装 https://github.com/ssm2602031032-hue/story-production-skill/tree/main/skills/story-production
```

也可以下载仓库，将`skills/story-production`文件夹复制到自己的Codex技能目录：

```text
~/.codex/skills/story-production/
```

Windows默认对应用户目录下的`.codex\skills\story-production`。如果设置了`CODEX_HOME`，则使用其`skills`子目录。保留整个Skill文件夹，而不只是复制`SKILL.md`。安装后下一轮对话即可调用；推荐在新会话开始使用，无需重启App。

## 直接使用

只给主题即可启动电影模式：

```text
$story-production
主题：一个总替别人收拾残局的人，第一次决定让真相留下来。
```

明确模式时会采用对应结构：

```text
$story-production 写一部完整小说：一家只在雨夜营业的失物招领处。

$story-production 写一部长篇电视剧：三个不同年代的家族，共同守护一条即将消失的街。

$story-production 做一部校园爱情喜剧电影全套：两个互相嫌弃的人，必须完成同一个毕业项目。

$story-production 把我提供的小说改编成12集电视剧，保留主人公和结局，完成逐集剧本、全季连续性与AI制作包。
```

可补充受众、篇幅、时代、类型、结局倾向、制作限制和已有原稿；不要求先填长问卷。只有主题时默认电影，90—110分钟仅是初始规划；小说约24章、剧集约12集也都可调整。Skill不会以固定场数、重复剧情或拉长空镜来凑目标。

## 交付内容

| 模式 | 主要交付 |
| --- | --- |
| 小说 | 完整章节正文、人物与世界设定、章节索引、连续性记录、HTML阅读入口 |
| 电影/短片 | 完整剧本、导演制作总纲、全片秒级分镜、角色/造型/道具/场景、AI素材队列、对白录音表、暂定字幕与声音Cue |
| 长篇电视剧 | 全季主线与人物弧、每集完整电影schema制作包、共享资产、跨集状态与伏笔账、全季入口 |
| 小说影视改编 | 原书与改编稿分别保留，记录章节到集/场的映射及修改原因 |

核心文件为Markdown、JSON、CSV、SRT和离线HTML。PDF与Excel由可用导出环境生成，最终可打包ZIP。所有秒数都是预剪辑设计，首尾帧是文字锚点；实际录音、动态预演、图片、视频、混音和DCP另有真实制作状态。

## 仓库结构

```text
skills/story-production/
  SKILL.md
  agents/openai.yaml
  references/                # 写作、连续性、制作与数据规范
  scripts/                   # 校验、构建和导出
  assets/                    # 阅读器模板与原创小型示例
tests/
```

仓库提供通用流程和小型验证示例，不包含任何用户长片正文、私人书稿、账号凭据或商业电影剧本。

## 本地运行工具

核心脚本需要Python 3.10+，不需API密钥或网络。以下命令从`skills/story-production`目录运行：

先按实际请求选择方法，或建立带源版本指纹的创作记录：

```text
python scripts/creative_tools.py plan --request "校园爱情喜剧电影全套" --out my-film/creative-plan.json
python scripts/creative_tools.py ledger-init --source my-film/film.json --out my-film/creative-ledger.json
python scripts/creative_tools.py ledger-check my-film/creative-ledger.json --source my-film/film.json
```

计划不生成正文，空记录不代表审校完成。记录中的事实、角色信念、伏笔、已修问题必须对应实际章节或镜头；源稿变化会提示记录过期。字段及小型工作表见[创作记录工具](skills/story-production/references/creative-ledger.md)。仅构思时可跳过尚不存在源文件的后两条命令。

```text
python scripts/film_pipeline.py init --theme "示例主题" --project my-film --format feature --minutes 100
```

`init`仅生成待填写骨架。创作代理完成权威`film.json`后，再执行：

```text
python scripts/film_pipeline.py validate my-film/film.json --report my-film/check.json
python scripts/film_pipeline.py build my-film/film.json --out my-film/output --notes my-film/authored-notes.md
```

小说与剧集的初始化：

```text
python scripts/story_pipeline.py init --mode novel --theme "示例主题" --project my-book --count 24
python scripts/story_pipeline.py init --mode series --theme "示例主题" --project my-series --count 12
```

完成对应权威源后，使用`story_pipeline.py validate INPUT`和`story_pipeline.py build INPUT --out OUTPUT`。完整数据字段见[小说与剧集规范](skills/story-production/references/story-schema.md)及[电影与单集规范](skills/story-production/references/film-schema.md)。

可选导出与打包：

```text
python -m pip install -r scripts/requirements-export.txt
python scripts/export_artifacts.py my-film/output
node scripts/export_workbook.mjs my-film/output
python scripts/package_release.py my-film/output --zip my-film/story-package.zip
```

PDF需要ReportLab、pypdf和可用字体，中文可通过`--font`指定字体文件。Excel需要宿主提供`@oai/artifact-tool`；若不可用，应保留CSV并说明缺少XLSX。仓库不附带该专有运行时或系统字体。更多说明见[工具与导出](skills/story-production/references/tooling.md)。

对剧集根输出目录运行导出器，会生成全季总表/总纲，并继续导出每集的PDF与Excel。打包器按文件清单收集产物，核对可选导出是否对应当前源版本，生成包含全部已完成格式的下载页。请使用新的版本化ZIP文件名。

## 验证示例与测试

`assets/example-film.json`是110秒原创短片，`assets/example-novel.json`是两章小样，`assets/example-series/series.json`是两集微型示例；它们用于验证工作流程，不代表已完成的长篇作品。

从仓库根目录运行：

```text
python -m unittest discover -s tests -v
```

核心测试仅依赖Python标准库。GitHub Actions在Linux与Windows、Python 3.10与3.12上运行相同检查；PDF字体、原生Excel和真实浏览器显示仍需在实际制作环境中验证。

## 检查的作用

工具检查编号、资产与服装引用、镜头/对白时间、重复声音来源、跨集状态、路径和输出文件。创作流程还要求审查人物动机、证据链、世界规则的替代解法和伏笔回收。

机器检查不能判断作品是否足够动人，也不能证明AI镜头已经可用。交付会区分“完整第一稿”“拍前设计”和“已生成媒体”，并如实列出仍待录音、预演或视觉验证的内容。

## English

`story-production` is a reusable Codex skill for developing a theme into a complete novel, television season, or original film preproduction package. It includes writing guidance, continuity audits, structured source formats, offline readers, and deterministic export tools. It prepares production plans and generation queues; it does not render or publish a finished film on its own.
