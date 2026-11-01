# 文件、构建与导出

## 环境与边界

核心脚本使用Python 3.10+标准库，无需API密钥，不调用远程模型。它们构建、验证和整理已经写好的权威源，不会从主题自动补出文学内容。主题到全文的创作由使用Skill的代理完成。

以下命令假定当前目录是本Skill目录。把`project`替换为独立项目路径；路径含空格时加引号。不要在Skill安装目录保存用户作品。

## 初始化

```text
python scripts/film_pipeline.py init --theme "主题" --project project --format feature --minutes 100
python scripts/story_pipeline.py init --mode novel --theme "主题" --project book --count 24
python scripts/story_pipeline.py init --mode series --theme "主题" --project series --count 12
```

初始化只创建待写骨架与规划。此时正文和完成状态尚不成立。短片使用`--format short`；剧集单集采用电影schema中的`project.format: episode`。

## 校验与构建

```text
python scripts/film_pipeline.py validate project/film.json --report project/check.json
python scripts/film_pipeline.py build project/film.json --out project/output --notes project/authored-notes.md

python scripts/story_pipeline.py validate book/novel.json --report book/check.json
python scripts/story_pipeline.py build book/novel.json --out book/output

python scripts/story_pipeline.py validate series/series.json --report series/check.json
python scripts/story_pipeline.py build series/series.json --out series/output
```

已有非空输出目录默认拒绝覆盖。检查其中内容后，使用`--overwrite`更新脚本管理的文件；不删除无关文件。校验失败先修源，不直接修输出蒙混过关。

电影构建输出：

| 文件 | 用途 |
| --- | --- |
| `screenplay.md` | 完整剧本阅读正文 |
| `director-guide.md` | 制作总纲与具体审校信息 |
| `shot-plan.json`, `assets.json` | 完整镜头、素材与资产数据 |
| `shots.csv`, `edit-markers.csv` | 秒级镜头与剪辑标记 |
| `dialogue.csv`, `subtitles.srt` | 录音任务与暂定字幕轴 |
| `generation.csv` | AI生成分段及命名 |
| `asset-references.csv` | 静态参考图任务 |
| `sound-cues.csv` | 场级/镜级声音与音乐方向 |
| `recurring-audio.csv` | 有复用录音时的唯一来源映射 |
| `index.html` | 内嵌数据的离线阅读工作台 |
| `validation.json`, `manifest.json` | 当前版本检查与文件清单 |

小说和全季输出见[story-schema.md](story-schema.md)。剧集构建应验证所有单集源与跨集资产，然后生成全季入口；不能只让清单中的文件名看起来齐全。

## PDF和Excel

在运行环境允许时安装PDF导出依赖，随后导出：

```text
python -m pip install -r scripts/requirements-export.txt
python scripts/export_artifacts.py project/output
node scripts/export_workbook.mjs project/output
```

PDF导出使用ReportLab与pypdf；中文字体由系统发现，也可显式传入可用字体路径：

```text
python scripts/export_artifacts.py project/output --font /path/to/CJK-font.ttf
```

字体许可由实际使用环境决定，仓库不分发用户机器字体。若系统没有对应字形，应提供可用字体后重导，不能接受方框字或静默丢字。

Excel导出使用运行环境提供的`@oai/artifact-tool`。需要可解析的Node模块路径；在支持它的宿主环境中使用已配置运行时，不把其专有依赖复制进仓库。不可用时保留CSV并说明缺少XLSX；不能把CSV改扩展名为`.xlsx`。

电影工作簿按镜头、分场、对白和生成单元组织。小说工作簿提供章节与人物，剧集工作簿提供逐集及跨集状态。镜长调整后后续时码可以重算，但静态SRT、JSON、HTML和生成分段仍需重新构建。

可用宿主技能对PDF或电子表格有额外生成和验收要求时，遵循当前环境的有效要求。此仓库的脚本不覆盖宿主权限或工具约束。

## 打包与检查

```text
python scripts/package_release.py project/output --zip project/story-package.zip
```

先完成所需导出，再打包，以便清单与链接包括最终文件。ZIP放在输出目录外，避免自包含。解压后打开`index.html`，保留相对目录结构。

检查至少包含：

- 权威源没有占位正文；计划与实际完成数量相符。
- 镜/章/集编号与引用可解析，服装和跨集状态有效。
- 镜头、对白和分段时间无越界；纯后期与生成任务合计正确。
- 源、提示词、字幕、表格和阅读工作台属于同一版本。
- PDF抽样渲染清楚，无缺字、重叠或过小正文；表格公式与换时长结果合理。
- 工作台导航、搜索和下载链接可用；ZIP完整性和相对路径正确。

验证报告区分机器检查、人工阅读与实际媒体验证。字速通过不证明对白动人；镜号全覆盖不证明所有镜头可一次生成；脚本运行成功不证明真实浏览器和原生Excel显示已经检查。
