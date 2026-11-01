# AI视频提示词、写实排查与模型适配

本版按2026年11月1日可访问的官方仓库固定提交核验，包含7个任务配置、24张原创提示词卡与4份MIT许可的ComfyUI界面工作流。核验的是文档、代码配置和模板结构；没有下载模型权重或运行GPU生成，因此不宣称任何提示词/模型“市面最好”。

## 先解决正确的问题

用户说画面或运镜有AI感时，读取[真实摄影排查](modules/realism-diagnostics.md)。先固定机位，比较起始图、人物小动作、相机移动与后期各自影响。漂亮静帧、强颗粒、随机手抖、过度锐化和一长串电影术语不构成真实性证据。

写实优先用具体可观察条件：单一动机光、连续曝光、合理景深、稳定材质、克制表演、可到达的机位轨迹。用户指定动画或风格化时保留其选择，不强制改写实。

```text
python scripts/video_prompt_tools.py realism --scene "傍晚的小修理铺，一名成年女店员站在木桌旁" --action "她看一眼桌上的信封，轻轻把它推向对面，然后停住" --camera locked --out project/realism-baseline.json
```

基准是未渲染草案。对照版只增加小幅推近或侧跟；其余模型、参考、设置和种子组保持一致。若平台不提供种子等控制，比较的因果可信度降低，要写明。

## 工具与资料

- [项目资料表](../assets/video-projects.json)：11个开源或公开参考项目、固定提交、来源文件、许可边界与核验状态。
- [模型配置](../assets/video-model-profiles.json)：7个具体任务配置。预设帧数是观察到的保守选择，不是最大时长。
- [提示词卡](../assets/video-prompt-cards.json)：24个原创单镜例子，包含文生、图生、首尾帧、微表演、接触、运动、环境、团队与后期衔接。
- [工作流快照](../assets/workflow-snapshots.json)：4个官方模板的来源与哈希；原JSON在`assets/workflows/`，许可文件随包保留。

这些资料不自动安装外部项目。公开权重、开源代码、社区许可和云端服务是不同概念。例如所读HunyuanVideo-1.5许可有地区范围，LTX使用社区许可；Vidu技能仓库未见明确再分发许可证，故只链接不复制。模型使用前按实际地区、用途与最新模型卡核对，不把本包MIT许可套到权重上。

## 已核验任务配置

|配置ID|模式|原生帧率/规划预设|说明|
|---|---|---|---|
|`wan22-t2v-a14b`|T2V|16fps / 81帧|共享配置与4n+1规则；不能按5B的24fps解释|
|`wan22-i2v-a14b`|I2V|16fps / 81帧|输出比例跟输入图，大小参数涉及面积|
|`wan22-ti2v-5b`|T2V、I2V|24fps / 121帧|官方配置，示例1280×704|
|`ltx25-comfy-t2v`|T2V|24fps / 97帧|固定Comfy模板的distilled模型，后续有空间放大|
|`ltx25-comfy-flf`|首尾帧|24fps / 97帧|特定Comfy模板；不能混作Python guided keyframe流程|
|`hunyuan15-t2v-720p`|T2V|24fps / 121帧|官方示例，T2V检查点|
|`hunyuan15-i2v-720p`|I2V|24fps / 121帧|I2V检查点和对应配置|

LTX官方当前写法强调按时序、字面且连贯的一段动作描述，并建议不超过200个英文单词。Wan提供提示扩展流程；Hunyuan区分T2V主体/动作/场景与I2V运动描述。扩展提示不能偷偷增加新人物、换装、剧情或镜头；参考图已经给出的身份不必重复改写。

原生帧率和成片帧率分开。24fps剪辑中使用16fps素材时，应保持真实时长进行转换；直接把16fps素材解释成24fps会变快。超分不等于原生细节，补帧不证明中间动作正确。

## 生成提示词工作包

先由原构建器得到`shot-plan.json`，再运行：

```text
python scripts/video_prompt_tools.py profiles
python scripts/video_prompt_tools.py cards
python scripts/video_prompt_tools.py card listening
python scripts/video_prompt_tools.py build project/output/shot-plan.json --profile wan22-ti2v-5b --mode i2v --out project/video-prompts
```

输出`video-jobs.json`、`prompts.md`、`preflight.json`与清单。它是待审阅的制作规格，不是可直接提交的ComfyUI API JSON，也不会调用任何服务。纯后期镜保留时码而没有视频任务。先用观察到的预设作为分段规划上限；帧网格有官方依据的配置再选择最接近且覆盖本段的合法帧数，其他配置只保留观察到的预设。它们都仍需工作流与画质实测。

所有目标剪辑帧与后期帧合计保持原正片长度，原生尾帧不能默认丢弃。例如首尾帧生成97帧，而目标只有96帧，直接取前96帧会删掉最后参考落点。每条任务有`endpoint_conform`：检查完整首尾状态怎样映射到目标首尾，记录时长比例；偏差超过10%标为需调整分段/合法帧数/真实把手，禁止自动大幅加减速。小偏差也要实际审阅，不能仅凭索引保证动作自然。批准对白不随画面变速，口型与动作重新核对。

缺参考图时明确标待参考。已有文件可以用`--references references.json`：

```json
{
  "S01_001": {"first":"refs/hero-front.png"},
  "S02_004_G01": {"first":"refs/start.png","last":"refs/end.png"}
}
```

路径相对于映射文件所在目录，必须存在且具有PNG/JPEG/WebP签名；这只证明文件存在，不证明视觉正确。长镜第一段可继承整镜首图，最后一段可继承整镜尾图；中间段须独立批准锚点，不把全镜尾图错误塞给第一段。T2V不接受伪装为已施加条件的参考图。

长镜分段不能每段重复完整动作。用`--directives directives.json`补每段真实运动：

```json
{
  "S01_001_G01": {
    "action":"她先将视线移到信封，右手接近但尚未触碰。",
    "first":"她看向门口，双手在身体两侧。",
    "last":"她的右指停在信封边缘。",
    "camera":"三脚架固定机位",
    "positive_prompt":"Optional approved complete prompt in the chosen language.",
    "negative_prompt":"Optional targeted constraints only if the workflow supports a negative field."
  }
}
```

只有一个镜头只需单段时也可覆写最终提示词。保持剧情与资产，模型专用配置查所选管线，不能靠该JSON自动安装未知节点或下载模型。

## A/B测试与真实性记录

```text
python scripts/video_prompt_tools.py benchmark-init --profile wan22-ti2v-5b --cases hesitation listening handoff --out project/prompt-test.json
python scripts/video_prompt_tools.py benchmark-check project/prompt-test.json
```

每例为基准/候选两版、两个匹配种子。未生成时状态是`pending`，分数为`null`。实际测试后记录相对媒体路径、SHA256、工作流指纹、完整设置、提示词、人工观察和0—5分指标。设置应包含模型修订、尺寸、帧数、帧率、采样、引导与参考图哈希；一次只改变要比较的提示变量。

检查器只对齐相同条件的完成记录，并输出逐项候选减基准差值；没有实测时不给总分或赢家。文件存在与哈希一致不证明评分诚实，也不推出全市场排名。实际尝试数量和费用另按用户授权管理。

## 开源项目如何用于解决问题

ComfyUI与官方工作流帮助固定可复现条件；Diffusers可用代码记录参数；WanVideoWrapper为Wan提供另一路实现与专用示例。LTX的Comfy适配器提供控制LoRA与视听流程，具体控制模型/版本须匹配。SeedVR2用于修复与放大，不能把错误的表演、机位或物理因果自动变正确。

ComfyUI界面模板需在匹配版本打开并检查节点、检查点与外部资源，再由该环境导出API格式。模板带的示例文本/文件名不是用户实际素材；本包不分发示例输入媒体或模型权重。
