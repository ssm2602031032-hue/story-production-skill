# 素材无限画布：信息架构、布局与交接

用于用户说素材散乱、没有逻辑/层级/设计，或要求把剧本、参考、提示词、候选媒体与剪辑组织到无限画布。先确定画布用途，再排节点：故事时间线、制作阶段板、依赖图、选片比较和模型节点图不能混为一种布局。

## 默认的制作画布

有剧本/镜头的项目采用“场景 × 制作阶段”：场景从上到下，原文与作用、参考与身份、画面与台词、候选素材、审看与修复、剪辑与交付从左到右；同一镜头在各列使用稳定ID。当前脚本支持用户自定义阶段名称与顺序，不把这六列强加给每种任务。

共享资产和参考研究单独成组，不在每个镜头复制一份原图。一个节点只承担一种信息角色。标题简洁、状态明确、摘要可扫读，完整提示词和审看记录保存在可打开的详情。关联线说明“支持/使用/产生/替代/需重做”等关系，不靠相近距离暗示来源或审批。

颜色只承担一致的类别或状态，不给每个节点任意配色。主阅读路线要靠空间顺序、标题和关系标签共同成立。大作品使用总览加分场景/段落画布；不能把所有镜头压到一张超长图再缩小文字。

## 已实现工具

`canvas_board.py`使用Python标准库生成布局、可编辑JSON Canvas文件和Markdown详情；可选Pillow与实际字体生成PNG预览。它不自动上传素材，不生成模型节点或更改ComfyUI连线。

```text
python scripts/canvas_board.py from-bridge project/scene-package/shot-packages.json --out project/canvas-spec.json
python scripts/canvas_board.py from-bridge project/scene-package/shot-packages.json --scenes SC01 --out project/scene01-spec.json
python scripts/canvas_board.py build project/canvas-spec.json --out project/board-v1
```

输入shot-packages来自script_bridge；完整提示词保留在详情，候选媒体初始为“待制作”，不会因为提示词存在就标成已生成/已批准。该导入器只提取参考条件信息，不自动迁移原包中的参考文件；要在画布显示实际媒体，应在规范节点明确填写file与实际sha256。单个详细板最多120卡（六列时20镜），更多内容用下面的project模式。

```text
python scripts/canvas_board.py project project/scene-package/shot-packages.json --out project/all-boards-v1
```

输出`overview.canvas`、`index.md`和场景分板，每页最多8镜；pages.json列出全部job ID与对应页面，避免分页时丢掉镜头。原始源稿/工作包不改。语义排序由已有场景/镜头次序提供，工具不能从未读的文件夹自动判断正确故事顺序。

## 自定义素材规范

输入是本包的制作板规范，不是已有ComfyUI/React Flow/Excalidraw文件：

```json
{
  "title":"单场素材板",
  "groups":[{"id":"SC01","title":"第一场"}],
  "stages":[{"id":"reference","title":"参考"},{"id":"prompt","title":"提示词"}],
  "nodes":[
    {"id":"REF01","group":"SC01","stage":"reference","order":0,"title":"场景光线参考","summary":"侧窗光方向与墙面反射。","details":"完整来源、继承与排除内容。","status":"review"},
    {"id":"PROMPT01","group":"SC01","stage":"prompt","order":0,"title":"镜头01提示词","summary":"人物伸手并接住物件。","details":"在这里保存完整提示词。","status":"draft"}
  ],
  "edges":[{"id":"USE01","from":"REF01","to":"PROMPT01","label":"提供照明依据"}]
}
```

groups/stages数组决定主要顺序，节点order决定本列阅读顺序。status为planned/draft/review/approved/rejected；approved须有review_note。标题限两行、摘要限五行；超过应重写摘要并把完整内容留在details，不默默截掉。`file`可指向相对规范文件的真实媒体，配套sha256；缺失/变化文件报错。`url`只接受明确的HTTP(S)参考链接，工具不打开它。

文件节点的标题和状态与媒体展示区域分开，仍属于同一卡片空间。公开Skill只附原创文字样例；用户截图只在其本地项目按当前任务使用，不随仓库发布。

## 自动排版与人工位置

默认固定网格、卡宽/高、组内留白和阶段列；本地预览的关系线路由避开卡片内部。连线仍保留语义标签，JSON Canvas客户端可自行重绘路径，所以不承诺其原生显示与PNG逐像素相同。

```text
python scripts/canvas_board.py layout project/canvas-spec.json --out project/layout-v1.json
python scripts/canvas_board.py build project/canvas-spec-v2.json --previous project/board-v1/layout.json --out project/board-v2
```

同ID、同场景、同阶段的已有位置会保留；新节点选择空位。`pinned:{"x":60,"y":260}`可手工固定20像素网格上的坐标。固定/保留位置碰撞、跨组重叠、布局过于稀疏或超大时明确报错，不擅自移动用户整理好的区域。新增大量内容可能需分板或重新规划，不假装所有增量都能无代价塞进旧布局。

## 真正的依赖布局：ELK

复杂分支可另做单组依赖视图。可选Node环境中安装`elkjs@0.12.1`后，从该项目环境运行：

```text
node /absolute/path/to/skill/scripts/canvas_elk.cjs dependency-spec.json dependency-v1.canvas
```

该适配器真正调用ELK layered/orthogonal布局，检查节点不重叠，输出`.canvas`和`.routing.json`。后者保留实际折线路径与完整原始规范。JSON Canvas标准没有这些折线控制点字段，原生客户端仍会自行路由。该视图仅接受单组文本卡；固定节点、媒体节点、多场景语义组使用stage-grid，不静默丢弃它们。

ELK和Dagre负责几何布局，不会理解哪个图片是参考、哪个是成品。React Flow可作为将来搭建自定义交互应用的组件层；本包没有把这个静态导出称为已部署的React Flow应用，也没有安装其运行时。Excalidraw、Miro、FigJam、ComfyUI各有自己的数据格式，不能改扩展名冒充原生工程。

## 预览、导入和检查

```text
python scripts/canvas_board.py build project/canvas-spec.json --font /absolute/path/to/CJK-font.ttf --out project/board-with-preview
```

字体由实际环境提供，不随包分发。预览按同一坐标生成，媒体缩略图只用于浏览，不用于原尺寸画质验收。打开PNG检查标签、留白、顺序、缩略图和整体阅读路线；检查JSON Canvas的节点ID、边端点、组边界与相对路径。大图可分场景生成，不以缩小所有字解决密度。

导入时保持整个输出目录（board.canvas、notes/、media/）一起，或把该目录作为支持JSON Canvas客户端的工作根目录。不同应用对相对文件与Markdown链接的解释可能不同，需在目标应用试开。当前已验证文件结构、路线、媒体副本和PNG；未进行Obsidian/Miro/FigJam等原生界面导入验收。

对已有原生工作流的整理：先识别格式和备份新版本，保留执行节点ID、端口、参数、连线以及用户手工分组；当前工具不会接管或自动重写这些原生文件。确认具体应用后再选择正确的适配器。
