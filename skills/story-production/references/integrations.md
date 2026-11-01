# 已整合的创作技能

12个昆卡原文参考和57个扩展模块由[模块目录](module-catalog.md)按任务选择。原文快照固定版本见[来源清单](../assets/upstream-sources.json)。

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
