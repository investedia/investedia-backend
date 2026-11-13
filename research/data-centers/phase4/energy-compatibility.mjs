// Read-only probe of the pinned current Energy normalizer. No production file edits.
import fs from 'node:fs';import vm from 'node:vm';import cp from 'node:child_process';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const repo='/workspace/investedia-frontend',commit='c78ab084349b43e4c166fa0f6a0dde6dbae8af5c',read=p=>cp.execFileSync('git',['-C',repo,'show',`${commit}:${p}`],{encoding:'utf8'}),source=read('assets/js/projects-data.js'),body=read('assets/globe/projects-invest.json'),raw=JSON.parse(body),before=JSON.stringify(raw),sandbox={window:{},document:{currentScript:{src:'https://example.invalid/assets/js/projects-data.js'}},URL,fetch:()=>{throw Error('Offline probe must not fetch')}};
vm.runInNewContext(source,sandbox);const normal=sandbox.window.InvProjectsData.invest(raw);assert.equal(JSON.stringify(raw),before);assert(normal.length>0);
const second=sandbox.window.InvProjectsData.invest(JSON.parse(body));assert.equal(JSON.stringify(normal),JSON.stringify(second));
const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
const selected=normal.filter(p=>raw.projects.find(r=>r.id===p.id)?.exposures.some(e=>e.verification?.listing?.ticker)).slice(0,2);assert.equal(selected.length,2);
fs.writeFileSync(new URL('sources/energy-normalized.body',import.meta.url),JSON.stringify({raw,normal}));
const data={commit,sha256:sha(body),loader_sha256:sha(source),as_of:raw.as_of,source_schema:raw.schema,source_credit:raw.credit,projects:selected.map(n=>({raw:raw.projects.find(r=>r.id===n.id),normalized:n,normalized_sha256:sha(JSON.stringify(n))}))};
fs.writeFileSync(new URL('energy-snapshot.json',import.meta.url),JSON.stringify(data,null,2)+'\n');
const report={commit,energy_records_normalized:normal.length,raw_records:raw.projects.length,input_unchanged:true,repeated_normalization_identical:true,normalized_sha256:sha(JSON.stringify(normal)),loader_sha256:sha(source),production_files_modified:false,selected_preview_ids:selected.map(p=>p.id)};fs.writeFileSync(new URL('energy-compatibility.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
