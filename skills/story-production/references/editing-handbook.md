# 剪辑工作台：已有素材到可检查的粗剪

先确认当前任务是写剪辑方案、修改工程，还是实际渲染。用户已经要求剪辑/渲染且素材可用时可直接完成授权范围，不必增加逐步审批。这里不生成AI镜头、不自动上传、不修改源媒体。纯小说任务不加载本手册。

## 能执行到哪里

|任务|本包实际能力|仍需另行处理|
|---|---|---|
|画面粗剪|按实际帧裁切、重排、拼接、完整画幅等比缩放并加边|多画面叠层、溶解、变速、稳定、自动主体裁切|
|声音衔接|独立WAV入出点、相对画面提前/延后、增益、淡入淡出、混合|自动对白理解、降噪、自动音乐压低、最终混音|
|交换工程|实际OTIO画面及独立音轨、CMX3600画面EDL并重开核对|原生Resolve/Premiere工程、全部效果参数往返|
|字幕|按被保留的某个源视频区间重排SRT|语音对齐、自动拆词、J/L配音字幕校时、烧录排版|
|调色交接|读取真实色彩标签，导出作者提供数值的ASC-CDL单校正XML|自动参考图匹配、应用CDL、LUT、Log/HDR转换|
|验收|全解码检查视频帧数/帧率/尺寸、音轨与音频长度|表演、每个切点、口型、字幕位置、影院DCP验收|

当前粗剪器限整数24/25/30/48/50/60fps、方形像素、SDR、每序列合计最多64个画面/音频片段。长片按场或段落生成可审片序列，保留总工程。输入VFR、分数帧率、已知HDR/BT.2020或非方形像素时先做有记录的规整；不能改标签冒充转换。输出H.264/AAC MP4是审片预览，非影院母版。

## 从已有制作包导入画面

所有命令相对于本Skill目录。项目文件、媒体和输出放在用户自己的项目目录。

```text
python scripts/edit_decisions.py from-shots project/output/shot-plan.json --media-map project/media-map.json --scenes 1 2 --width 1280 --height 720 --out project/rough-v1.json
```

先使用上版选片记录确认media-map引用的版本。导入保留选中的source_in_frame、镜长和场号，不把生成任务直接当成可用镜头。它只导入画面，音轨为空；所有画面源内嵌音频明确忽略，需另外提供真实WAV声音。输出JSON要位于媒体文件的项目祖先目录，便于安全相对链接。

## 独立画面与声音的决定文件

最小输入 `project/edit-input.json`：

```json
{
  "title":"第一场粗剪",
  "fps":24,"width":1280,"height":720,
  "embedded_audio_policy":"ignore","color_intent":"sdr-review",
  "sources":{
    "V1":{"kind":"video","path":"media/take01.mp4"},
    "A1":{"kind":"audio","path":"media/dialogue.wav"}
  },
  "picture":[
    {"id":"CUT01","source":"V1","in_frame":0,"out_frame":96,"reason":"在人物作出决定后切走","story_ref":"S01"}
  ],
  "audio":[
    {"id":"DIALOGUE01","source":"A1","in_frame":0,"out_frame":48,"timeline_in_frame":24,"gain_db":-3,"fade_in_frames":1,"fade_out_frames":2}
  ]
}
```

示例要求实际视频至少96帧、音频至少2秒。音频须48kHz PCM16单/双声道WAV；音频in/out也用剪辑fps的帧单位，24fps时1帧对应2000个采样。画面按列表相接，不允许隐式空洞；声音可重叠，必须位于成片范围内。尾帧均为排他边界。增益支持-120至24dB，重叠声音可能削波，工具不会暗中归一化。

```text
python scripts/edit_decisions.py capture project/edit-input.json --out project/edit-v1.json
python scripts/edit_decisions.py validate project/edit-v1.json --out project/edit-v1-check.json
```

capture只记录真实源哈希，不代表审片批准；validate实际读取媒体、核对格式、源范围与音轨位置。素材改变后应重新审看并创建新的决定版本，不能刷新哈希冒用旧决定。

根字段或片段内出现不支持的speed、transition等字段会明确报错，不能默默丢弃效果。输入画面原先带有旋转/非标准显示约定时，先检查实际解码与显示方向并规整。本包不提供“任何素材自动正确”的承诺。

## 本地渲染与复看

```text
python scripts/edit_render.py plan project/edit-v1.json --out project/preview-v1.mp4 --report project/render-plan-v1.json
python scripts/edit_render.py render project/edit-v1.json --out project/preview-v1.mp4 --report project/render-result-v1.json
python scripts/finishing_tools.py check project/edit-v1.json project/preview-v1.mp4 --out project/final-check-v1.json
```

plan只检查输入并写命令清单，不生成视频；render真实执行本地FFmpeg并检查实际输出帧数。命令以参数列表执行，不把输入文字拼成可执行脚本。`--timeout`默认600秒，可按明确的序列工作量调整。失败或超时留下的文件属于未验收的部分输出，不能称为成片；重试使用新路径。源与既有输出不覆盖。

输出保留全部原画幅并按目标画布加边。没有声明WAV就输出明确标注的无声预览，不偷偷采用源视频声音。预览技术通过后要播放切点、听声音衔接；机器的visual_reviewed/auditory_reviewed默认false，不能改成true假装已看听。可用已有media_review的接触表辅助检查。

## 交换文件与修改比较

```text
python scripts/edit_decisions.py otio project/edit-v1.json --out project/edit-v1.otio
python scripts/edit_decisions.py edl project/edit-v1.json --picture-only --out project/picture-v1.edl
python scripts/edit_decisions.py diff project/edit-v1.json project/edit-v2.json --out project/edit-changes.json
```

OTIO保留画面和声音的源范围与开始时间。增益、淡入淡出只是元数据，目标编辑器不会被假定自动应用；渲染器才真正执行这些混音处理。EDL本包只导出画面，限24/25/30fps非丢帧，使用唯一短reel映射和从文件第0帧起算的源时码，不冒充拍摄机嵌入时码。实际商业编辑器导入与插件兼容性另测。

diff按稳定片段ID列出剪切、移位、音轨和来源变化，提示字幕与声音需重核。它不读取媒体，也不判断改后故事更好；导演仍需回到原文和两个实际版本比较。

## 剪后字幕与停顿候选

```text
python scripts/subtitle_conform.py project/edit-v1.json project/original-source.srt --source V1 --out project/edited-source.srt
python scripts/finishing_tools.py silence project/media/dialogue.wav --threshold-db -40 --min-sec 0.4 --out project/silence-candidates.json
```

字幕输入必须对应指定V1文件自身的时间线；完整电影的预估字幕不能直接套到一个独立生成片段。保留区间重排或重复时，字幕同步移动/重复；被删除条目记录在报告。切到一句话中间只保留原文并提示人工处理，不推测哪些词被说出。全部条目被删时只输出报告，不制造空字幕成品。J/L音频与画面时序不同，声音字幕需要依真实音轨另校。

静音候选按WAV窗口RMS测量，不录音、不识别人、不自动剪掉。低声对白、呼吸、迟疑和反应可能是剧情关键；先听、留边界余量，再由作者决定是否修改edit文件。

## 调色与最终交接

```text
python scripts/finishing_tools.py color project/media/take01.mp4 --out project/color-tags.json
python scripts/finishing_tools.py cdl project/look.json --out project/look.cc
```

look.json需要id、slope三值、offset三值、power三值和saturation，例如中性校正为 `[1,1,1]`、`[0,0,0]`、`[1,1,1]`、`1`。标签描述编码声明，不测量真实色域；CDL不是完整OCIO配置或3D LUT。记录输入变换、工作空间、显示变换、参考帧和监看环境后，才在目标调色工程应用并复核。

需要字幕或片头烧录时，先完成实际画幅、字体与安全区预览，再在能执行该任务的工具内做；本渲染器不会因方案里写了“字幕”就假称已烧录。交付同时保留决定JSON、源哈希、交换文件、实际预览和检查结果。

## 依赖与已验证范围

实际视频检查/交换需requirements-media.txt；渲染与EDL另外使用requirements-editing.txt。可以使用已有FFmpeg，否则按需安装imageio-ffmpeg；脚本不自行联网下载。FFmpeg和编解码器的许可按安装发行包处理，本Skill不分发其二进制。

真实CPU测试覆盖逆序取帧、总帧数、延后声音、淡入淡出调用、输出音轨、OTIO音轨位置、EDL往返、字幕重排与静音候选。没有安装或操纵Resolve/Premiere，没有做GPU生成、HDR母版或影院DCP。参考来源的强制审批、固定竖屏、自动删静音和录麦行为均不继承；当前用户目标和授权优先。
