# 改稿快照与直接影响工具

在修改之前保存源快照，修改后生成需要复核的清单：

```text
python scripts/project_ops.py snapshot --source project/film.json --out project/before-edit.json
python scripts/project_ops.py impact --before project/before-edit.json --source project/film.json --ledger project/creative-ledger.json --out project/change-impact.json
```

支持电影、小说和整季源。工具不会修改源稿、创作记录、已批准素材或状态。快照只记录单元、资产与相关上下文的哈希，原始作品继续作为权威源保存。

报告区分新增/删除/改变的单元、正文变化、时序变化、资产变化、直接需要复核的引用以及创作记录中的受影响条目。更改角色外貌会找出使用该角色的镜头；更改一句台词不会被误认为只改排版。整季包含各集文件指纹，单集变化可被识别。

哈希比较无法理解所有隐含事实。场号重新编号可能需要人工建立旧新映射；没有显式资产ID的小说描写或剧情暗示也可能未被自动关联。报告是修订起点，不能据此宣称所有因果、口型或字幕已经重新验证。

根据实际影响决定重新录音、生成、合成、剪辑或仅复核。确认后才更新创作记录的源指纹与批准状态，不把旧素材的认可自动继承给新版本。
