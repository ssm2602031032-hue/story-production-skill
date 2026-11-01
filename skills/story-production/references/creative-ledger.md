# 创作记录与任务选择工具

新增工具使用Python标准库，不调用远程模型、不写正文，也不自动安装其他技能。脚本路径以Skill目录为基准，输出放在用户的项目目录。

## 按请求选择模块

```text
python scripts/creative_tools.py catalog
python scripts/creative_tools.py plan --request "写一部校园爱情喜剧电影全套" --out project/creative-plan.json
python scripts/creative_tools.py plan --request "只润色第三场对白，不改剧情" --mode film --task dialogue --scope S03
python scripts/creative_tools.py plan --request "小说改编成12集悬疑剧" --mode series --task adapt --genres mystery
```

`--mode`和`--task`覆盖关键词推断。类型采用`comedy romance mystery thriller action sports fantasy sci-fi historical horror serial revenge`；`--modules`可显式添加[目录](module-catalog.md)中的ID。路由结果是计划，包含理由、建议交付和每组不超过三个模块的阅读批次。先读当前阶段需要的一组，不把所有批次塞入上下文。

专项任务还支持`opening / emotion / antagonist / ensemble / transitions / pacing / short-form / audio / comics / nonfiction / naming / table-read`。例如`--task naming`只产生命名路线；`--task comics`选择漫画分格方法。`mode`仍用于标记既有小说/影视项目背景，专项任务不会因此自动转成一整部电影；广播剧/漫画的专用成品格式需按实际工具另行制作。

这是一套透明关键词规则，不是语义模型。多义、否定或复杂目标应以用户实际意图纠正；未识别不能改写用户请求。局部对白任务不会自动生成整部电影。

## 建立证据关联记录

```text
python scripts/creative_tools.py ledger-init --source project/film.json --out project/creative-ledger.json
python scripts/creative_tools.py ledger-check project/creative-ledger.json --source project/film.json --report project/ledger-check.json
```

也支持`novel.json`、`series.json`。初始化保存源版本指纹和可用定位示例，空记录明确不等于审校完成。项目源变化后，检查会报告记录过期：先阅读变动、确认哪些条目仍成立，再更新指纹，不自动消除冲突。

已填写的小型例子是[example-creative-ledger.json](../assets/example-creative-ledger.json)，对应同目录的[example-film.json](../assets/example-film.json)，其中保留一项真实待制作验证，展示“结构引用有效”与“所有问题解决”并非同一个状态。编辑器若改变换行字节也会使指纹变化，先确认差异再更新。

定位规则：小说`C001`；电影/单集`S01`或`S01_003`；整季`E001`、`E001/S01`或`E001/S01_003`。整季还绑定各集文件指纹，单集修改不会被季清单未变掩盖。

记录分四组：

```json
{
  "facts": [
    {"id":"F01","kind":"canon","entity_id":"C01","statement":"正文已经建立的事实","at":["S01_001"],"quote":"可选：该位置实际存在的原句"},
    {"id":"F02","kind":"belief","holder_id":"C01","statement":"角色相信，但作者尚未认定的解释","at":["S01"]},
    {"id":"F03","kind":"proposal","statement":"待采纳的新设计","at":[]}
  ],
  "promises": [
    {"id":"P01","setup":["S01_001"],"resolution":[],"status":"planned","note":"尚未写到的回收"}
  ],
  "issues": [
    {"id":"I01","kind":"bridge","at":["S01"],"observation":"具体观察","status":"open","fix_at":[],"verification":""}
  ],
  "decisions": [
    {"id":"D01","decision":"提出的修改","reason":"解决何种问题","status":"proposed","affects":[]}
  ]
}
```

上例只是字段说明，需要保留初始化产生的指纹。ID在四组中不得重复，所有引用必须存在；`quote`如填写，必须确实出现在指定位置。`belief`需要已定义的知情角色，不能自动变成全局事实。

伏笔状态为`planned / resolved / open-intentional`。声称已回收必须有`resolution`，有意留白必须写原因。问题类型为`contradiction / bridge / style / production`；状态为`open / fixed / deferred`。声称已修必须提供实际`fix_at`和`verification`。决策为`proposed / adopted / rejected`，采纳需指明影响位置。

工具只检查定位、指纹和状态声明是否自洽，不能机器证明情感动人、角色动机合理或影像可生成。尚未回收与未处理问题作为警告保留，不伪装成已经完成。

## 可复制的小型工作表

按实际需要加入`authored-notes.md`，无需每个项目都造一堆空文件：

| 用途 | 最小字段 |
| --- | --- |
| 人物选择 | 当前目标、资源、知情、可行选项、所选策略、代价 |
| 关系变化 | 两方目标、误读、靠近行动、边界、变化位置 |
| 场景卡 | 谁要什么、空间阻力、策略变化、结果、离场依据 |
| 线索表 | 真实含义、首次出现、误读、知情者、验证、回收 |
| 喜剧段落 | 预期、偏转、升级、反应空隙、后果、回调 |
| 研究记录 | 发现、出处、时期/地域、边界、创作决策 |
| 交接包 | 有效版本、已完成范围、当前事实、未决问题、下一步 |

已有正文与导出器继续使用原来的`film.json / novel.json / series.json`，本记录为旁路工作资料，不强迫旧项目迁移schema。
