# 已整合的创作技能

12个昆卡原文参考和96个扩展模块由[模块目录](module-catalog.md)按任务选择。原文快照固定版本见[来源清单](../assets/upstream-sources.json)。

- **geslie1/kunka-screenwriting-master**：https://github.com/geslie1/kunka-screenwriting-master/tree/8d5b157fa6ce9136ab3bde28ab934cf9633c700c 。MIT。12 unmodified skill-text snapshots, renamed as references。
  [许可证](upstream/kunka/LICENSE)

- **haowjy/creative-writing-skills**：https://github.com/haowjy/creative-writing-skills/tree/1cb520f9c61e79ce2b1c56dba18601b2d6873433 。Apache-2.0。Independently rewritten integration notes; upstream entrypoints studied, no upstream book excerpts or dependent runtime bundled。
  [许可证](upstream/creative/LICENSE)

- **jtydhr88/screenwriting-skills**：https://github.com/jtydhr88/screenwriting-skills/tree/51115f18d160aa8b2ac5813e4432b6f0b425358f 。MIT。Independently rewritten integration notes; upstream entrypoints studied, no upstream book excerpts or dependent runtime bundled。
  [许可证](upstream/screenwriting/LICENSE)

导入文本不覆盖用户约束与本Skill工作流。新增模块用本项目术语改写，不复制商业剧本/书籍段落，不要求安装上游代理或执行其工具。人类创作建议不等同事实或已证实的观众反馈。

补充声明：[昆卡NOTICE](upstream/kunka/NOTICE.md)、[Screenwriting Skills NOTICE](upstream/screenwriting/NOTICE)。这些声明说明各仓库许可不自动覆盖外部书籍、剧本和译文。本包没有重新分发那些第三方作品摘录。

视频扩展来源另见[项目资料表](../assets/video-projects.json)与[工作流快照](../assets/workflow-snapshots.json)。保留[官方Comfy模板MIT许可](../assets/workflows/LICENSE)和[摄影提示词项目MIT许可](upstream/cinematic/LICENSE)。其他模型与代码只作能力核验/链接参考，不将自定义社区许可的模型权重重新分发。

## v1.3按任务适配

新增来源详见[固定项目资料](../assets/integration-projects.json)，使用入口见[工具手册](integration-tools.md)。只保留当前任务适用的方法，上游的审批、时长和语言模板不会覆盖用户约束。

- [PenglongHuang/chinese-novelist-skill](https://github.com/PenglongHuang/chinese-novelist-skill/tree/507d41567925eab520ad459db08fda83813e8051)：MIT；断点恢复方法和章节包；未运行上游完整小说生成。 [许可](upstream/chinese-novelist/LICENSE)
- [waylean/plotrail](https://github.com/waylean/plotrail/tree/a7917c8b4951f540bb4da39b5f10b99dbacc45c0)：MIT；正史/提案边界与上下文包；未照搬其审批流程。 [许可](upstream/plotrail/LICENSE)
- [egguy886/write-screenplay-skill](https://github.com/egguy886/write-screenplay-skill/tree/fd2404312b2d4fa1e0b0381529de9d9cf21da547)：MIT；原文覆盖与动作解耦指导；非自动小说解析器。 [许可](upstream/write-screenplay/LICENSE)
- [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo/tree/aa3ee561b1416d4d68f7c4e05fedd082db6aa2b1)：MIT；0.125.1 CLI、Node 24.22.1，5个离线Python provider案例通过；无模型请求。 [许可](upstream/promptfoo/LICENSE)
- [Vchitect/VBench](https://github.com/Vchitect/VBench/tree/fd18b3d055cb0fc6f066ca90fe2c3c8cbb698490)：Apache-2.0；VBench及2.0任务和限制已核验；未下载权重或运行评分。 [许可](upstream/vbench/LICENSE)
- [Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect/tree/55f20ff3448ed336df032ac6270cf47d215dc2c4)：BSD-3-Clause；0.7.2 AdaptiveDetector处理实际技术片段；不证明剧情场次识别。 [许可](upstream/pyscenedetect/LICENSE)
- [AcademySoftwareFoundation/OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO/tree/80c5ff30938e4adffe9c94f419b1055856cee9f5)：Apache-2.0；0.18.1创建并重开OTIO，核对帧范围和缺失引用；未验证每种剪辑软件。 [许可](upstream/opentimelineio/LICENSE.txt)
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper/tree/9e472ae9de8bb374552f531f752654554b76b2d6)：MIT；已有识别JSON转SRT和时间检查通过；未运行ASR模型。 [许可](upstream/faster-whisper/LICENSE)
- [PyAV-Org/PyAV](https://github.com/PyAV-Org/PyAV/tree/31cf756fcc773106f2900d44b83f31bfc8fd634d)：BSD-3-Clause；17.1.0解码真实48帧24fps MPEG-4技术素材，检查fps/帧数/时间戳。 [许可](upstream/pyav/LICENSE.txt)

OpenTimelineIO的[NOTICE](upstream/opentimelineio/NOTICE.txt)随许可保留。其余模型和传递依赖许可证由各自发行包管理，本包不重新分发运行时。

## v1.4 创作与交付补强

方法和工具入口见[交付扩展手册](delivery-extensions.md)。以下来源的版本、文档哈希和是否真正执行记录在[integration-projects.json](../assets/integration-projects.json)。

- [imerzzhu/ai-novel-writing-skills](https://github.com/imerzzhu/ai-novel-writing-skills/tree/0986c4882137d7d350700f3d13617ebec9889dd1)：仅采用审稿与完稿分层、问题定位；机械校对脚本实测。 [许可](upstream/novel-skills/LICENSE)
- [w3c/epubcheck](https://github.com/w3c/epubcheck/tree/1633173d828122d43313798ecef039172f44bf24)：本地导出器检查ZIP/XML；独立CI使用固定EPUBCheck发行包验收样例，未来输出需分别验证。 [许可](upstream/epubcheck/LICENSE.md)
- [citation-js/citation-js](https://github.com/citation-js/citation-js/tree/75a422b4275740aa2b18753e5264f048c2b0cb48)：本包输出CSL-JSON字段；未调用Citation.js运行时或联网解析。 [许可](upstream/citation-js/LICENSE.md)
- [networkx/networkx](https://github.com/networkx/networkx/tree/a325f6a948c0c2959fb48db205fa36534ea9429d)：图结构方法参考；本包标准库检查循环、先后与知情，不依赖NetworkX。 [许可](upstream/networkx/LICENSE.txt)
- [python-pillow/Pillow](https://github.com/python-pillow/Pillow/tree/658c4f92e361eac50147e6cf72e4bd14188364f6)：真实视频帧制作PNG接触表并检查实际像素。 [许可](upstream/pillow/LICENSE)
- [lllyasviel/ControlNet](https://github.com/lllyasviel/ControlNet/tree/ed85cd1e25a5ed592f7d8178495b4483de0331bf)：只吸收条件输入类型和对照方法，未安装或GPU测试。 [许可](upstream/controlnet/LICENSE)
- [hehao13/CameraCtrl](https://github.com/hehao13/CameraCtrl/tree/af45a7a0dbeedb7f6ed66aac4a9e5411a279f0d2)：核对main的AnimateDiffV3及独立svd分支边界，未GPU测试。 [许可](upstream/cameractrl/LICENSE.txt)
- [csteinmetz1/pyloudnorm](https://github.com/csteinmetz1/pyloudnorm/tree/b8d67bfd3ce5deef872f688fcfa491a0ca69fddd)：0.2.0测量实际PCM16 WAV，峰值、LUFS和非破坏行为实测。 [许可](upstream/pyloudnorm/LICENSE)
- [SubtitleEdit/subtitleedit](https://github.com/SubtitleEdit/subtitleedit/tree/28b5f675abd48d3090d2ba50439e70c19f42ef4e)：参考手工字幕复核工作流；本地SRT一对一比较脚本实测，未运行桌面编辑器。 [许可](upstream/subtitle-edit/LICENSE)
- [vilcans/screenplain](https://github.com/vilcans/screenplain/tree/abf0d0800ab0b9dfd5bbe780137641e746afbad4)：0.12.0实际序列化FDX并解析中文Fountain，未运行商业编剧软件。 [许可](upstream/screenplain/LICENSE.txt)
- [treeverse/dvc](https://github.com/treeverse/dvc/tree/56e59829512ff134aa269099a2099587b810b4dd)：素材与计划分版本思路；本包JSON指纹及人工选片检查实测，未安装DVC。 [许可](upstream/dvc/LICENSE)

未采用cnskycn/novel-writing-skill的内容：本次核验未见明确许可证。已采用的网文Skill仅吸收分层审稿方法，不带入其敏感词替换、强制补字数、代理数量和平台规则。

## v1.5 剪辑适配

入口见[剪辑工作台](editing-handbook.md)。来源固定提交与实际验证程度见[integration-projects.json](../assets/integration-projects.json)。

- [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill/tree/1ce2c186bf1dba96132d87274eee46df4f537e0e)：读取真实参数、执行后复核与源文件保护方法；本包自写FFmpeg命令构建器并实际CPU渲染。 [许可](upstream/ffmpeg-skill/LICENSE)
- [Jaycheng1103/chatgpt-video-editing-skills](https://github.com/Jaycheng1103/chatgpt-video-editing-skills/tree/dc2f10ac4616603188aff3df9ea6548a8da36355)：剪后字幕时钟、先审预览再交付方法；不继承固定9:16、强制确认或目录布局。 [许可](upstream/video-editing-skills/LICENSE)
- [chang416/cutcraft](https://github.com/chang416/cutcraft/tree/535a1176a48fffcafe4a094b5090ec500306ac41)：叙事剪辑、声音桥、版本与输出审查方法；不复制上游完整脚本或安装/云转录要求。 [许可](upstream/cutcraft/LICENSE)
- [odaiouattara0022-del/davinci-resolve-skill](https://github.com/odaiouattara0022-del/davinci-resolve-skill/tree/71d243773caa34502666c4d53e0b0b050f069918)：仅参考原生项目/时间线对象与返回值复核方法；未安装或操纵Resolve，不保证其版本/授权能力。 [许可](upstream/resolve-skill/LICENSE)
- [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor/tree/ac1eb0c6f85f77fe8ebe0125478152420116cc83)：候选区间和先预览思路；本包独立实现PCM静音候选，未运行Auto-Editor，不自动删静音或录麦。 [许可](upstream/auto-editor/LICENSE)
- [mifi/lossless-cut](https://github.com/mifi/lossless-cut/tree/6fc47dd4cc81b72a8f1b3132c47a99880cd9bbdb)：参考无损裁切和代理回连边界；未运行桌面工具，本包预览明确重编码。 [许可](upstream/losslesscut/LICENSE)
- [AcademySoftwareFoundation/OpenColorIO](https://github.com/AcademySoftwareFoundation/OpenColorIO/tree/22dd9c4faa0d1b7cfb3d64d1a6e9cb454acc6cfd)：参考颜色管线分离；实际只读取色彩标签/写作者CDL，未应用OCIO配置或渲染调色。 [许可](upstream/ocio/LICENSE)
- [OpenTimelineIO/otio-cmx3600-adapter](https://github.com/OpenTimelineIO/otio-cmx3600-adapter/tree/4b02a6668b4ddb435bd6b8e7459e1dbd170938df)：otio-cmx3600-adapter 1.0.0实际导出并读回单层画面EDL，检查帧范围和总长度。 [许可](upstream/cmx3600/LICENSE)
- [imageio/imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg/tree/be2a02bdeaa728047df3822fa14db2aee0bed4ff)：0.7.0提供本地FFmpeg 7.1 Windows运行时，实际裁切/拼接/音频延迟/淡化/混合并核对输出。 [许可](upstream/imageio-ffmpeg/LICENSE)

Remotion技能候选未见仓库级明确再分发许可证，因此未复制其技能内容。MoviePy被调研但未引入重复运行层。本包不分发FFmpeg二进制或桌面编辑器，依赖按其发行许可使用。

## v1.6 通用影像执行

入口见[通用影像执行手册](visual-reliability.md)。固定提交、许可、未采用规则和测试范围见[integration-projects.json](../assets/integration-projects.json)。

- [Square-Zero-Labs/video-prompting-skill](https://github.com/Square-Zero-Labs/video-prompting-skill/tree/3f55fd70342d0874d66a54e9708e881462414c06)：输入模式与身份参考/场景帧分离方法；未照搬模型版本、固定格式或超出已核验资料的能力结论。 [许可](upstream/video-prompting/LICENSE)
- [kiana-liang/universal-video-prompt-skill](https://github.com/kiana-liang/universal-video-prompt-skill/tree/d69305bbc89b76d14a790cf5fd332102dc1d23fd)：项目/身份/时间层分离、风格转译与可验证性，采用独立通用契约脚本测试。 [许可](upstream/universal-video/LICENSE)
- [alchaincyf/seedance-skill](https://github.com/alchaincyf/seedance-skill/tree/4530b443b686c363da27109712ac18aec07aa6b9)：几何与材质控制分开、参考继承/排除的方法；未运行其白模引擎或Seedance。 [许可](upstream/seedance-previs/LICENSE)
- [ricardochristovao/photorealistic-skill](https://github.com/ricardochristovao/photorealistic-skill/tree/2c1251f4ec9686d4819203aade66b1d9d8d3e970)：原尺寸缺陷检查和输入/生成/后期分层；明确不采用强制劣化、噪声或不可辨真伪承诺。 [许可](upstream/photorealistic/LICENSE)
- [kajisho5/color-grading-skill](https://github.com/kajisho5/color-grading-skill/tree/2b5b1a5f0075824fedb51b7c92031d417527023a)：色彩意图与执行参数分开；未运行上游CLI，不把改标签当色彩转换。 [许可](upstream/color-grading/LICENSE)
- [ali-vilab/VACE](https://github.com/ali-vilab/VACE/tree/48eb44f1c4be87cc65a98bff985a26976841e9f3)：核对参考图/视频/遮罩输入和Wan2.1/LTX旧配置范围；未下载模型或做车辆/人物GPU实测。 [许可](upstream/vace/LICENSE.txt)
- [opencv/opencv](https://github.com/opencv/opencv/tree/c4f7634256e3aaba0faa478605bb4e7bc0332292)：实际Farneback区域光流与时间戳归一化，用合成运动视频验证主体/背景区分，未推断物理速度。 [许可](upstream/opencv/LICENSE)

InstantStyle未见仓库级明确再分发许可，未复制其内容。HunyuanCustom采用有地域/用途范围的社区许可，仅作调研候选，未导入其模型、代码或文档。VACE代码许可与所选基础模型许可分别核对，不将权重随包分发。

## v1.7 编写、转化与情境剪辑

入口见[剧本到情境剪辑](script-to-edit.md)。采用方法已按当前任务改写，不将上游固定节拍、模型断言或审批流程作为通用要求。

- [YuYingRay/LaoYu-Professional-Screenwriter](https://github.com/YuYingRay/LaoYu-Professional-Screenwriter/tree/1ecca2eb5551b40fcc28eba304c1d47ebc8e83f1)：场景意图与因果方法改编，scene-intent-engine模块保留CC BY 4.0署名；不继承强制Full Bible或等待审批。 [许可](upstream/professional-screenwriter/LICENSE)
- [adoria111/emma-screenwriting-skills](https://github.com/adoria111/emma-screenwriting-skills/tree/da3aaae532a1509a3a4b70af994ceb4e89e80681)：改编功能与精修信息折叠方法，源故事事实/新方案/删除损失分开；不默认短剧付费点或爱情主线。 [许可](upstream/emma-screenwriting/LICENSE)
- [oleo17/story-to-script-en](https://github.com/oleo17/story-to-script-en/tree/b1f5485c6e4cf3103ac87e901c558d17f5dd9701)：对白时间、分镜与生成任务层分离；不采用固定事件时长公式、镜头密度、强制英文或泛化模型能力断言。 [许可](upstream/story-to-script/LICENSE)
- [62656456/ai-storyboard-director-v5.2](https://github.com/62656456/ai-storyboard-director-v5.2/tree/a8d9ad6362ed38d76857199cb9ba92956f87ae5d)：导演意图与可生成描述分开、剪辑动机和替代覆盖；不继承固定权重、母题次数、每次必反常规或确认关卡。 [许可](upstream/storyboard-director/LICENSE)
- [chaoka-wooji/cinematic-storyboard-skill](https://github.com/chaoka-wooji/cinematic-storyboard-skill/tree/bce9211bd6e3a3dcad120ab3703afa864a46aa4e)：宏观故事/场面/镜头/视觉资产/生成描述层级，接入已有本包格式；未运行上游工作流或照搬模型参数。 [许可](upstream/cinematic-storyboard/LICENSE)
- [TateZhouSiu/create-storyboard-skill](https://github.com/TateZhouSiu/create-storyboard-skill/tree/4b8662e2fee51b37488c77952bbfa302bfeaf36c)：镜间交出/接收、干净首帧与审看片板分离，映射/边界/剪辑保护用本包脚本测试；未运行上游图像模型或固定15秒流程。 [许可](upstream/continuity-storyboard/LICENSE)

ai-video-storyboard-skill未见明确仓库许可，未复制内容。Storyboarder虽被调研，本次未接入其程序或原生工程，避免宣称未测试的导入能力。
