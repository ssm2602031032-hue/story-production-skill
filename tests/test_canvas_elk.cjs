const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process');
const root=path.resolve(__dirname,'..'),script=path.join(root,'skills/story-production/scripts/canvas_elk.cjs'),input=path.join(root,'skills/story-production/assets/example-dependency-canvas.json');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'story-canvas-elk-')),runtime=process.env.CANVAS_ELK_PROJECT||process.cwd();
try {
 const output=path.join(temp,'dependency with spaces.canvas'),before=fs.readFileSync(input);
 cp.execFileSync(process.execPath,[script,input,output],{cwd:runtime,encoding:'utf8'});
 const doc=JSON.parse(fs.readFileSync(output,'utf8')),raw=JSON.parse(before),report=JSON.parse(fs.readFileSync(output+'.routing.json','utf8'));
 assert.equal(doc.nodes.length,raw.nodes.length);assert.equal(doc.edges.length,raw.edges.length);assert.deepEqual(fs.readFileSync(input),before);assert.equal(report.native_app_tested,false);assert.deepEqual(report.complete_original_spec,raw);
 for(const edge of doc.edges){assert(doc.nodes.some(n=>n.id===edge.fromNode));assert(doc.nodes.some(n=>n.id===edge.toNode));}
 for(let i=0;i<doc.nodes.length;i++)for(let j=i+1;j<doc.nodes.length;j++){const a=doc.nodes[i],b=doc.nodes[j];assert(!(a.x<b.x+b.width&&b.x<a.x+a.width&&a.y<b.y+b.height&&b.y<a.y+a.height));}
 assert(report.edges.every(e=>Array.isArray(e.sections)&&e.sections.length));
 assert.throws(()=>cp.execFileSync(process.execPath,[script,input,output],{cwd:runtime,stdio:'pipe'}));
 const pinned=JSON.parse(before);pinned.nodes[0].pinned={x:0,y:0};const bad=path.join(temp,'pinned.json');fs.writeFileSync(bad,JSON.stringify(pinned));assert.throws(()=>cp.execFileSync(process.execPath,[script,bad,path.join(temp,'bad.canvas')],{cwd:runtime,stdio:'pipe'}));assert(!fs.existsSync(path.join(temp,'bad.canvas')));
 console.log('ELK adapter: actual layout, semantic links, collision check, overwrite protection and pinned-node rejection passed.');
} finally {if(path.dirname(temp)===path.resolve(os.tmpdir())&&path.basename(temp).startsWith('story-canvas-elk-'))fs.rmSync(temp,{recursive:true,force:true});}
