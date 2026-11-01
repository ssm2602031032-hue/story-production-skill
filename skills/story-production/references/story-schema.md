# 小说、全季剧集与改编数据

小说和剧集各有独立权威源，不以电影镜头表冒充小说全文，也不以一集剧本冒充全季。下列字段保留类型差异；共同的ID、人物与世界规则仍可用于改编。

## 小说：novel.json

```json
{
  "kind": "novel",
  "slug": "project-slug",
  "title": "作品名",
  "theme": "主题",
  "logline": "一句话故事",
  "synopsis": "含真实结局的完整摘要",
  "world_rules": [],
  "characters": [],
  "locations": [],
  "props": [],
  "structure": [],
  "continuity_audit": [],
  "authoring_status": "incomplete",
  "project": {
    "planned_chapters": 24,
    "target_words": 80000,
    "language": "zh-CN"
  },
  "chapters": []
}
```

人物至少有稳定`id,name,arc`，可增加外形、语言、目标和关系。地点及道具至少有`id,name`并记录实际世界状态。统计分列中文字符与拉丁字母词。当前`target_words`只是规模报警用预算，脚本以“中文字符数 + 拉丁字母词数”近似比较；这不是统一的语言学词数，也不以达到预算证明正文完整。

章节元素：

```json
{
  "n": 1,
  "title": "章名",
  "story_time": "第1天夜，或明确的时间跨度",
  "pov": "稳定叙述视角及必要说明",
  "goal": "本章的行动与变化",
  "body": "完整章节正文，含实际场景、内心、行动和对白。",
  "ending_hook": "真实结尾的悬念、变化或余韵",
  "character_ids": ["C01"],
  "location_ids": ["L01"],
  "prop_ids": ["P01"]
}
```

章节按阅读顺序从1连续编号。`body`必须是真正正文，`goal`和`ending_hook`不是其替代品。引用的资产ID必须存在。

完成时`authoring_status`改为`complete`，并确保计划章节全部完成。若创作中有合理的增删章，明确更新规划及原因，不悄悄降低目标以让检查变绿。原用户承诺的故事范围仍然需要满足。

## 全季剧集：series.json

```json
{
  "kind": "series",
  "slug": "series-slug",
  "title": "剧名",
  "theme": "主题",
  "logline": "整季主线",
  "synopsis": "含季终结果的完整摘要",
  "authoring_status": "incomplete",
  "world_rules": [],
  "characters": [],
  "props": [],
  "locations": [],
  "season_arc": "全季升级、主要人物弧与季终决定",
  "continuity_audit": [],
  "asset_states": [],
  "continuity_events": [],
  "episodes": [],
  "adaptation_map": [],
  "project": {
    "planned_episodes": 12,
    "episode_minutes": 40,
    "language": "zh-CN"
  }
}
```

`episodes`条目：

```json
{
  "n": 1,
  "title": "集名",
  "source": "episodes/E001/film.json",
  "summary": "本集实际起落、结尾与对下一集的后果",
  "status": "complete"
}
```

每个单集源采用[film-schema.md](film-schema.md)，`project.format`设为`episode`。每集有完整对白、场景和镜头；完整季交付不能包含“稍后补完”的集。所有集完成后，全季`authoring_status`设为`complete`。`status`是作者声明，还需实际源文件和内容验证。

`source`是相对于`series.json`所在目录的路径，必须留在该项目根内。不要用绝对路径、`..`越界或符号链接把其他项目、凭据或私人文件带入发布包。

## 跨集资产与状态

共享资产使用全季稳定ID。相同ID的角色身份、外形、声线、道具设计及地点空间在各集一致。新衣装阶段可以增加，但先加入全季设定，再在单集引用；已有阶段的含义不能在另一集变成不同衣服。需要真实形象变化时，在设定中明确阶段和故事原因，镜级覆盖只用于那次呈现。

状态定义：

```json
{
  "id": "P01_DAMAGED",
  "asset_id": "P01",
  "description": "道具P01在某事件后出现的固定损伤"
}
```

状态事件：

```json
{
  "episode": 2,
  "scene": 7,
  "asset_id": "P01",
  "from_state": "P01_INTACT",
  "to_state": "P01_DAMAGED",
  "reason": "该场实际写出的损坏事件"
}
```

两端状态必须已定义、属于同一资产，引用集与场必须存在。脚本按集号、场号的呈现顺序校验事件和连续状态；因此这张表记录当前主时间线的状态推进，倒叙使用历史造型/状态引用，并在`continuity_audit`另列真实发生顺序。不要把回放误记成当前物件重新损坏一次。复杂非线性叙事须人工核对双时间线，当前脚本不会自动推断历史时序。下一次事件的起点不能跳过上一次结果；修复、复制、归还或伤愈需要可成立的过程。

人物知情与伏笔不止是物件状态：在`continuity_audit`记录某人在哪一集通过什么方式得知、作出何种选择、在哪一集回收。全季完成时核对主线承诺，不以“第二季会解释”掩盖本季漏写。

## 小说到剧集的映射

```json
{
  "source_chapters": [3, 4],
  "episode": 2,
  "scenes": [6, 7, 8],
  "change": "合并重复探访，把原著内心判断外化为一次有代价的选择",
  "reason": "保留人物作用，同时让本集因果和视听表达成立"
}
```

引用原章节与目标集场必须真实存在；脚本可检查目标集场，原章节需对照实际原书人工核对。原书没有提供时不能凭空声称已忠实改编；有授权的用户原文也不因使用本Skill而获得公开上传许可。电影改编可在独立映射文档采用同样列结构，省略集号。

## 输出与进度

小说构建通常生成`novel-book.md`、逐章Markdown、`novel-plan.json`、`continuity.csv`、阅读入口和校验清单。剧集构建生成`season-guide.md`、`season-plan.json`、每集电影制作文件、跨集连续性、资产复用与改编表，以及全季阅读入口。

真实完成数量来自源内容和文件检查，不能从`planned_episodes`直接填入“已完成”。恢复创作时，以进度记录和权威源为准；如果两者不一致，先查实际正文，不覆盖已经写好的章节或剧集。
