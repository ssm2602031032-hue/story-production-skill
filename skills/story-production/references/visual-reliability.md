# 通用AI影像：一致性、运动、材质与风格执行

用于人物/车辆/动物/服装/产品/道具/空间前后漂移、动作缺少速度或重量、画面油腻、风格词没有变成所需观感，以及动作剪辑不连贯。先定位具体层次，再决定改参考、改动作、改模型控制、改后期还是改剪辑。没有实际样片时只能提出待验证方案，不宣布已经解决画质。

## 通用顺序

1. 建立当前作品的资产约束：哪些身份/几何不变，哪些状态允许随剧情改变。
2. 按当前镜头的可见范围准备场景首帧；身份图、风格图、动作图各自注明继承和排除内容。
3. 把风格转成光线、色彩、反差、材质、光学、机位、剪辑与声音条件。拍摄条件与人物/物体的动作分开。
4. 写明动作的开始、主要过程、结束与切镜原因，核对人物知情、物件交接和空间方向。
5. 在具体模型中按真实支持的输入方式制作小样。先分离问题，再扩大到整段；不凭同种子或资产ID认为模型已经锁定身份。
6. 用完整片段、原尺寸细节和邻镜对照复核，实际结果没有生成时评分保持空白。

普通小说文风或非写实绘画任务不强行套用本模块。用户主动选择慢动作、油画、塑料玩具或夸张动画时，按其意图建立对应目标，不能自动“修回实拍”。

## 一致性：项目内不变量与状态

`invariants`记录当前任务不能漂移的部分，例如人物面部身份、产品几何、车辆型号、道具数量、建筑相对布局。服装、伤势、持有人、湿润程度、时间和天气可用`states`及实际变化原因表达，不把所有事物永久冻结。

同镜多资产用主`asset`加`supporting_assets`分别绑定。一个人物正确不代表同框人物、手中物品和背景也正确。场景首帧的`covers_assets`记录实际审看过的可见资产范围；未覆盖的同框资产会保持待准备。该字段是人工记录，不是图像识别认证。

`visibility`按视角选择要写进提示词的不变量；全量身份仍保留在记录中。手部特写不要求生成脸，产品局部不要求把背面结构翻到正面。高速模糊、遮挡和光照变化不要求每帧RGB或可见细节完全相同，应检查基础身份和合理变化。

图像参考只有文件哈希和人工批准记录都齐全时才绑定。身份多视图可以用于制作单个场景首帧，但不应直接把整张多格转面板当I2V开场。第一帧、最后一帧还要属于同一主体与可解释的状态；首尾正确不保证中段没有形变。

## 动作：世界运动、机位运动与播放速度分开

主体在屏幕中不动，可能是摄影机正在跟拍；背景运动很快，也可能只是快速摇镜。先声明期待的动作和机位关系，再选择近景掠过、远近视差、接触、重心变化、形变与停下后的稳定等可见证据。

奔跑、追逐、挥手、倒水和微表演需要不同证据，不把快速运动规则强加给静物。明显的高速实时动作不应同时要求慢动作回放。真实时长、模型原生fps与剪辑fps要分别记录；不要靠随意改速掩盖运动生成问题。

如果作者明确提供世界距离与时间，工具可检验其与声明速度是否矛盾；未标定的画面光流不能换算成km/h或m/s。舞蹈、车辆轮辐等也可能出现采样混叠，单帧运动方向不是完整物理证据。

## 材质：分层排查“油、塑料、蜡、过锐”

先看未经超分、补帧、锐化、降噪、磨皮或风格化处理的原输出，再对比每一步。区分参考图本来就过度修饰、生成阶段纹理随帧游走、后期抹平与边缘光晕。强运动模糊或真实浅景深不自动等于油腻。

材质要有差别：皮肤、织物、橡胶、金属、玻璃、陶瓷和湿地不能全都同样发亮。黑漆可以真实反光，静物也可以光滑；目标是与材质、光源和镜头条件一致。不要把“所有输出必须加颗粒、JPEG损失和柔化”当成真实感配方。

原尺寸细节板不加锐化、降噪或噪点。对脸、衣料、字形、物件边缘、接触处和背景纹理按实际帧检查。画面经过大幅缩放的接触表适合构图审查，不足以判断细节油腻程度。

## 风格：先作可见决定，再压成模型提示词

风格名称只是入口。需要在当前主体与场景中具体选择lighting、palette、contrast、texture、optics、camera_behavior、editing、sound。五张`assets/visual-style-cards.json`是起点；新风格可直接填写这些字段，不局限于预设。不要把上一种题材的服装、布景、运镜或笑点节奏整套搬来。

具体镜头只执行自身camera字段。项目级camera_behavior可能列出多种允许机位，它作为导演约束保留，不被全文塞进每个生成提示词。编辑和声音说明也单独交付，不把剪辑效果当成视频模型已经执行的动作。

可以用每镜`style_overrides`调整lighting/palette/contrast/texture/optics，适应内外景和时段。风格变化不应偷偷改人物、车型、产品颜色、持物或动作时长。字段检查不能自动理解所有自然语言冲突，作者仍需通读编译后的实际提示词。

## 可运行的通用契约

示例按需要选一个：

- `assets/example-multiasset-visual-contract.json`：人物、衣装、道具交接与场景，共三镜。
- `assets/example-product-visual-contract.json`：静态产品与材质，一镜。
- `assets/example-visual-contract.json`：车辆运动与方向连续性，六镜；仅作其中一种测试，不是默认题材。

复制到用户项目修改后运行，命令相对于Skill目录：

```text
python scripts/visual_contracts.py audit project/visual.json --out project/visual-audit.json
python scripts/visual_contracts.py build project/visual.json --out project/visual-v1
```

输出有单镜提示词、不可变身份记录、可见特征、首尾帧任务、剪辑/声音说明，以及未运行的测试记录。参考未准备好时，仍可完成策划，但`ready_for_reference_conditioned_attempt`为false；不能说人物或道具已被视觉锁定。

参考字段示例，路径相对于契约文件。哈希要从实际文件计算，不能填示例字符串冒充：

```json
{"id":"SCENE_START","role":"first_frame","view":"wide","path":"refs/scene-start.png","sha256":"实际文件的SHA256","approved":true,"approval_note":"已检查两人、伞与门窗布局","covers_assets":["C01","C02","P01","L01"],"inherit":"该场景的主体、构图和光线","exclude":"无关文字、拼版边框和其他造型"}
```

在对应镜头填写`conditioning:{"first":"SCENE_START"}`。普通I2V只绑定真实场景首帧；FLF模式还需对应last_frame。identity/style/motion角色的静态参考不能悄悄充当首帧。此契约的参考文件只接受PNG/JPEG/WebP，真正的运动视频、遮罩视频与多参考模型输入由具体工作流处理。

与现有模型任务连接时，可加 `--base-jobs project/model-output/video-jobs.json`检查镜头ID、生成模式与分配时长。产生的`directives.json`可传入原有video_prompt_tools的`--directives`，`reference-map.json`可传入`--references`。实际已批准关键帧会复制到独立输出包以保持路径可携带；没有的参考不会凭空出现。更换模型仍要复核该模型的输入角色、限制和参数，不能把通用文字当API请求。

## 单因素与整套风格比较

例如`candidate.json`内容为`{"value":"织物保留稳定纤维与褶皱，皮肤只有自然局部反光，金属反射随同一环境连续变化"}`：

```text
python scripts/visual_contracts.py ab project/visual.json --factor style.texture --candidate project/candidate.json --out project/texture-ab.json
```

支持style.lighting/palette/contrast/texture/optics，或用`--factor speed_cues --shot 镜头ID`只更改单镜运动证据列表。身份、参考文件、动作、机位和时长不动；执行时还要固定模型版本、工作流、生成参数、后期和模型支持的匹配种子组。工具不运行生成，不预填得分或赢家。

完整风格A/B可以同时改变多个美术条件，但只能说明整套方案的差异，不能把结果归因于一个词。只看一个最好种子或漂亮静帧，不足以证明稳定改善。

## 实际视频的辅助检查

区域JSON例如`{"subject":[0.35,0.3,0.3,0.4],"near_background":[0,0.75,1,0.2],"far_background":[0,0,1,0.2]}`，数值为0—1归一化x/y/宽/高；应依据真实画面手动调整，不能把示例区域当自动目标检测。

```text
python scripts/motion_probe.py flow project/clip.mp4 --regions project/regions.json --start-frame 0 --max-frames 121 --out project/motion.json
python scripts/motion_probe.py details project/clip.mp4 --frames 0 12 24 --crop 100 80 320 240 --out project/native-details.png
```

flow用实际时间戳和OpenCV光流，输出主体/背景的图像位移指标，不输出真实地面速度或真实感分数。仅在单个连续镜内测量；低纹理、模糊、遮挡、切镜和曝光变化都会影响结果。details按真实解码像素裁剪，不重采样；crop是像素坐标，必须在实际画面内。

这些工具不能替代人对身份、材质和表演的观察。需Pillow/PyAV/OpenCV/NumPy的部分可从既有requirements-media和requirements-delivery按需安装，不下载模型。

## 参考控制项目如何选

VACE提供特定基础模型下的参考图、视频与遮罩组合路线；固定文档涉及Wan2.1和旧版LTX配置，不能自动当作Wan2.2/LTX-2通用控制器。白模预演方法可让空间轨迹与提示词来自同一决定，但白模自身不负责真实材质。若模型缺乏身份/运动控制，选择支持对应条件的实际工作流或调整覆盖镜头；不要用越来越长的提示词掩盖缺失控制。

源Skill关于“照片不可辨真伪”、强制劣化、固定采访/审批或某模型一定支持某模式的说法不直接继承。具体使用前以官方版本和实际接口为准。来源和未执行范围见[integration-projects.json](../assets/integration-projects.json)。
