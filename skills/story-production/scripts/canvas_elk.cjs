#!/usr/bin/env node
// Optional dependency view using the real ELK layout engine. No runtime installation or network calls.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { createRequire } = require('node:module');
async function main() {
  const [input, output] = process.argv.slice(2);
  if (!input || !output || !output.endsWith('.canvas')) throw new Error('Usage: node canvas_elk.cjs spec.json new.canvas (run from a project with elkjs installed)');
  const out = path.resolve(output), report = out + '.routing.json';
  for (const target of [out, report]) {
    if (fs.existsSync(target)) throw new Error('Output already exists; choose a new version');
    for (let p = path.dirname(target); ; p = path.dirname(p)) {
      if (fs.existsSync(p) && fs.lstatSync(p).isSymbolicLink()) throw new Error('Output may not traverse a symbolic link');
      if (p === path.dirname(p)) break;
    }
  }
  const bytes = fs.readFileSync(input), spec = JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/, ''));
  if (!Array.isArray(spec.nodes) || !spec.nodes.length || spec.nodes.length > 120 || !Array.isArray(spec.edges)) throw new Error('Expected a bounded production-board spec');
  if (new Set(spec.nodes.map(n => n.group)).size !== 1) throw new Error('ELK view handles one dependency group at a time; use stage-grid for multi-scene semantic organization');
  if (spec.nodes.some(n => n.pinned || n.file || n.url)) throw new Error('This dependency view supports text cards without pinned/media/link nodes; use stage-grid to preserve those');
  const ids = new Set();
  for (const n of spec.nodes) {
    if (typeof n.id !== 'string' || !n.id || ids.has(n.id)) throw new Error('Node IDs must be unique');
    if (typeof n.title !== 'string' || typeof n.summary !== 'string') throw new Error('Each card needs title and summary');
    ids.add(n.id);
  }
  const edgeIds = new Set();
  for (const e of spec.edges) {
    if (typeof e.id !== 'string' || !e.id || edgeIds.has(e.id) || !ids.has(e.from) || !ids.has(e.to) || e.from === e.to || typeof e.label !== 'string' || !e.label.trim()) throw new Error('Each edge needs unique ID, valid endpoints, and a relation label');
    edgeIds.add(e.id);
  }
  const local = createRequire(path.join(process.cwd(), 'package.json'));
  let ELK;
  try { ELK = local('elkjs/lib/elk.bundled.js'); } catch { throw new Error('Install optional elkjs in the selected project environment; no download was performed'); }
  const elk = new ELK();
  const graph = {id:'root', layoutOptions:{'elk.algorithm':'layered','elk.direction':'RIGHT','elk.edgeRouting':'ORTHOGONAL','elk.spacing.nodeNode':'60','elk.layered.spacing.nodeNodeBetweenLayers':'120'}, children:spec.nodes.map(n => ({id:n.id,width:360,height:280})), edges:spec.edges.map(e => ({id:e.id,sources:[e.from],targets:[e.to]}))};
  const placed = await elk.layout(graph);
  for (const n of placed.children) if (![n.x,n.y,n.width,n.height].every(Number.isFinite)) throw new Error('ELK returned invalid geometry');
  for (let i=0;i<placed.children.length;i++) for (let j=i+1;j<placed.children.length;j++) {
    const a=placed.children[i], b=placed.children[j];
    if(a.x<b.x+b.width && b.x<a.x+a.width && a.y<b.y+b.height && b.y<a.y+a.height) throw new Error('ELK produced overlapping cards');
  }
  const by = new Map(spec.nodes.map(n => [n.id,n]));
  const canvas = {nodes:placed.children.map(n => ({id:n.id,type:'text',x:Math.round(n.x),y:Math.round(n.y),width:360,height:280,text:'## '+by.get(n.id).title+'\n\n'+by.get(n.id).summary})),edges:spec.edges.map(e => ({id:e.id,fromNode:e.from,toNode:e.to,fromSide:'right',toSide:'left',toEnd:'arrow',label:e.label}))};
  fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,JSON.stringify(canvas,null,2)+'\n',{flag:'wx'});
  const result={engine:'elkjs',source_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),nodes:placed.children,edges:placed.edges,complete_original_spec:spec,native_app_tested:false,limits:'Actual ELK geometry/routing for a separate dependency view. Standard JSON Canvas clients re-route edges; bend points remain in this sidecar. Full source data is preserved here, not executed or approved.'};
  fs.writeFileSync(report,JSON.stringify(result,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({output:out,report,nodes:canvas.nodes.length,edges:canvas.edges.length,engine:'elkjs',native_app_tested:false}));
}
main().catch(error => {console.error('Error: '+error.message);process.exitCode=1;});
