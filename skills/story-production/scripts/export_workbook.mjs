#!/usr/bin/env node
// Requires @oai/artifact-tool from the host runtime. Does not install dependencies.
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const args=process.argv.slice(2),folder=args[0];
if(!folder){console.error('Usage: node export_workbook.mjs OUTPUT_DIR [--preview-dir DIR]');process.exit(2)}
let Workbook,SpreadsheetFile;
try{({Workbook,SpreadsheetFile}=await import('@oai/artifact-tool'))}catch{console.error('@oai/artifact-tool is unavailable. Use the complete CSV files or export with a supported spreadsheet tool. No XLSX was produced.');process.exit(1)}
const dir=path.resolve(folder),previewAt=args.indexOf('--preview-dir'),previewDir=previewAt>=0?path.resolve(args[previewAt+1]):null;
async function exists(p){try{await fs.access(p);return true}catch{return false}}
function safe(v){return typeof v==='string'&&/^[\s]*[=+\-@]/.test(v)?"'"+v:v}
const wb=Workbook.create(),font='Arial';const sheets=[];const validation={};
function setup(name,title,headers,rows,widths){
 const s=wb.worksheets.add(name),end=6+rows.length;sheets.push(s);s.showGridLines=false;
 s.getRangeByIndexes(0,0,Math.max(7,end),headers.length).format.font={name:font,size:10,color:'#172631'};
 s.getRange('A2').values=[[safe(title)]];s.getRange('A2').format.font={name:font,size:16,bold:true};s.getRange('A2').format.rowHeight=26;
 const h=s.getRangeByIndexes(5,0,1,headers.length);h.values=[headers];h.format={fill:'#263641',font:{name:font,size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:34,horizontalAlignment:'center',verticalAlignment:'center'};
 if(rows.length){const r=s.getRangeByIndexes(6,0,rows.length,headers.length);r.values=rows.map(row=>row.map(safe));r.format.wrapText=true;r.format.verticalAlignment='top';}
 widths.forEach((w,i)=>s.getRangeByIndexes(0,i,Math.max(7,end),1).format.columnWidth=w);
 rows.forEach((row,i)=>{let lines=1;row.forEach((v,c)=>{const text=String(v??'');let count=0;for(const line of text.split('\n'))count+=Math.max(1,Math.ceil([...line].reduce((n,c)=>n+(/[\u4e00-\u9fff]/.test(c)?2:1),0)/(widths[c]||30)));lines=Math.max(lines,count)});s.getRange(`A${i+7}`).format.rowHeight=Math.max(28,Math.min(330,lines*14+8))});
 s.freezePanes.freezeRows(6);s.freezePanes.freezeColumns(1);return s;
}
let inputKind,episodeFolders=[];
if(await exists(path.join(dir,'shot-plan.json'))){
 inputKind='film';const p=JSON.parse(await fs.readFile(path.join(dir,'shot-plan.json'),'utf8'));const fps=p.meta.fps;
 const timeline=setup('镜头时间线',p.meta.title+' · 秒级分镜',['镜号','场号','入点','出点不含','时长秒','景别','焦段mm','摄影','动作与表演','对白','声音','首帧','尾帧','连续与制作'],p.shots.map(s=>[s.id,s.scene,null,null,s.duration_sec,s.size,s.lens_mm_equiv,s.camera,s.picture,s.dialogue.map(d=>d.speaker+'：'+d.text).join('\n'),s.sound,s.first_anchor,s.last_anchor,s.special]),[16,8,14,14,11,12,11,30,65,60,45,45,45,65]);
 timeline.getRange('A3').values=[['黄色时长可改。按叙事顺序排列；可筛选，重排镜头后须重建分场与生成任务。']];
 timeline.getRange('A4:F4').values=[['正片秒数',null,'帧率',fps,'片尾秒',p.meta.credits_seconds]];
 const last=6+p.shots.length;
 timeline.getRange('B4').formulas=[[`=SUM(E7:E${last})`]];
 timeline.getRange('C7').formulas=[['=0']];
 if(last>7){timeline.getRange('C8').formulas=[['=D7']];timeline.getRange(`C8:C${last}`).fillDown()}
 timeline.getRange('D7').formulas=[['=C7+E7/86400']];timeline.getRange(`D7:D${last}`).fillDown();timeline.getRange(`C7:D${last}`).setNumberFormat('[h]:mm:ss.000');timeline.getRange(`E7:E${last}`).format.fill='#FFF1CD';
 timeline.dataValidations.add({range:`E7:E${last}`,rule:{type:'decimal',operator:'greaterThan',formula1:0}});
 const sceneSheet=setup('分场设计',p.meta.title+' · 分场设计',['场次','场景','入点','出点','目的','空间','轴线','灯光','连续'],p.scenes.map(s=>[s.scene,s.heading,null,null,s.intent,s.space,s.axis,s.light,s.continuity]),[9,40,15,15,55,65,50,55,70]);
 let row=7;for(let i=0;i<p.scenes.length;i++){const count=p.shots.filter(s=>s.scene===p.scenes[i].scene).length;sceneSheet.getRange(`C${i+7}:D${i+7}`).formulas=[[`='镜头时间线'!C${row}`,`='镜头时间线'!D${row+count-1}`]];row+=count}sceneSheet.getRange(`C7:D${6+p.scenes.length}`).setNumberFormat('[h]:mm:ss.000');
 const shotRows=new Map(p.shots.map((s,i)=>[s.id,{s,row:i+7}]));
 const voice=setup('对白录制',p.meta.title+' · 对白录制',['对白号','镜号','人物','入点','出点','台词','镜内起秒','镜内止秒','说明'],p.dialogues.map(d=>{const s=shotRows.get(d.shot).s;return[d.id,d.shot,d.speaker,null,null,d.text,d.start_sec-s.start_sec,d.end_sec-s.start_sec,d.note||'暂定录音区间，先完整录音再校准']}),[22,16,20,17,17,70,13,13,60]);
 voice.getRange('A3').values=[['镜内起止为预排值；缩短镜头后须重新校准对白。原声复用规则以recurring-audio.csv为准。']];
 for(let i=0;i<p.dialogues.length;i++){const r=i+7,m=shotRows.get(p.dialogues[i].shot).row;voice.getRange(`D${r}:E${r}`).formulas=[[`='镜头时间线'!C${m}+G${r}/86400`,`='镜头时间线'!C${m}+H${r}/86400`]]}
 if(p.dialogues.length){voice.getRange(`D7:E${6+p.dialogues.length}`).setNumberFormat('[h]:mm:ss.000');voice.getRange(`G7:H${6+p.dialogues.length}`).format.fill='#FFF1CD'}
 const gen=setup('AI生成单元',p.meta.title+' · 生成队列',['单元','镜号','镜内入秒','镜内出秒','可用秒数','首帧要求','尾帧要求','状态'],p.clips.map(c=>[c.id,c.shot,c.shot_local_in_sec,c.shot_local_out_sec,c.clip_duration_sec,c.first_rule,c.last_rule,c.status]),[23,16,13,13,13,70,70,35]);
 gen.getRange('A3').values=[['静态分段快照。修改时长后必须重新分段；纯后期镜不进入视频生成。完整提示词见JSON。']];
 wb.recalculate();const before=timeline.getRange(`D${last}`).values[0][0],old=timeline.getRange('E7').values[0][0];timeline.getRange('E7').values=[[old+1]];wb.recalculate();const after=timeline.getRange(`D${last}`).values[0][0];timeline.getRange('E7').values=[[old]];wb.recalculate();
 if(Math.abs((after-before)*86400-1)>.001)throw new Error('Timeline propagation failed');
 if(Math.abs(timeline.getRange('B4').values[0][0]-p.meta.story_seconds)>.001)throw new Error('Story duration mismatch');validation.timeline_delta_seconds=(after-before)*86400;validation.story_seconds=p.meta.story_seconds;
}else if(await exists(path.join(dir,'novel-plan.json'))){
 inputKind='novel';const p=JSON.parse(await fs.readFile(path.join(dir,'novel-plan.json'),'utf8'));
 setup('章节规划',p.title+' · 章节',['章节','标题','故事时间','视角','本章目标','章尾承接','正文字符'],p.chapters.map(c=>[c.n,c.title,c.story_time,c.pov,c.goal,c.ending_hook,c.body.length]),[10,32,30,24,65,65,15]);
 setup('人物与设定',p.title+' · 人物',['ID','人物','人物弧线','外形','声音'],p.characters.map(c=>[c.id,c.name,c.arc||'',c.appearance||'',c.voice||'']),[15,20,75,65,65]);
}else if(await exists(path.join(dir,'season-plan.json'))){
 inputKind='series';const p=JSON.parse(await fs.readFile(path.join(dir,'season-plan.json'),'utf8'));
 episodeFolders=p.episodes.map(e=>path.join(dir,'episodes',`E${String(e.n).padStart(3,'0')}`));
 setup('整季集表',p.title+' · 整季集表',['集','标题','完整剧情','状态','源文件'],p.episodes.map(e=>[e.n,e.title,e.summary,e.status,e.source]),[8,35,100,15,45]);
 setup('跨集连续性',p.title+' · 状态流转',['集','场','资产ID','进入状态','离开状态','原因'],(p.continuity_events||[]).map(e=>[e.episode,e.scene,e.asset_id,e.from_state,e.to_state,e.reason]),[8,8,20,24,24,80]);
 setup('改编映射',p.title+' · 改编映射',['源章节','集','场','改动','原因'],(p.adaptation_map||[]).map(m=>[(m.source_chapters||[]).join(','),m.episode,(m.scenes||[]).join(','),m.change,m.reason]),[20,8,22,80,80]);
}else{throw new Error('No supported plan JSON in output directory')}
wb.recalculate();const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'Formula validation'});
if(previewDir){await fs.mkdir(previewDir,{recursive:true});await fs.writeFile(path.join(previewDir,'formula-check.ndjson'),errors.ndjson);for(let i=0;i<sheets.length;i++){const blob=await wb.render({sheetName:sheets[i].name,range:'A2:H10',scale:1.3,format:'png'});await fs.writeFile(path.join(previewDir,`sheet-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()))}await fs.writeFile(path.join(previewDir,'validation.json'),JSON.stringify(validation,null,2))}
const out=path.join(dir,'production.xlsx');try{if((await fs.lstat(out)).isSymbolicLink())throw new Error('Refusing symlink workbook output')}catch(e){if(e.code!=='ENOENT')throw e}
const exported=await SpreadsheetFile.exportXlsx(wb);await exported.save(out);console.log(JSON.stringify({file:out,kind:inputKind,sheets:sheets.length,...validation}));
const sourceName={film:'shot-plan.json',novel:'novel-plan.json',series:'season-plan.json'}[inputKind];const hash=b=>createHash('sha256').update(b).digest('hex');
await fs.writeFile(path.join(dir,'xlsx-export.json'),JSON.stringify({exporter:'story-production-xlsx',source_dependencies:{[sourceName]:hash(await fs.readFile(path.join(dir,sourceName)))},files:[{path:'production.xlsx',sha256:hash(await fs.readFile(out))}]},null,2));
for(const ep of episodeFolders){const childArgs=[fileURLToPath(import.meta.url),ep];if(previewDir)childArgs.push('--preview-dir',path.join(previewDir,path.basename(ep)));const child=spawnSync(process.execPath,childArgs,{stdio:'inherit'});if(child.status!==0)throw new Error(`Episode workbook export failed: ${path.basename(ep)}`)}
