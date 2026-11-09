// Existing Worker configuration is the authority; no price requests or data writes.
import fs from 'node:fs';
import {SYMBOLS_BY_GROUP} from '../../workers/live/v1/prices.js';
const target = new URL('../src/main/resources/worker-symbol-groups.json', import.meta.url);
const text = JSON.stringify(SYMBOLS_BY_GROUP, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (fs.readFileSync(target, 'utf8').replaceAll('\r\n', '\n') !== text) {
    throw new Error('Worker symbol groups changed; run node api/tools/export-symbol-groups.mjs');
  }
  console.log('Spring symbol groups match the existing Worker.');
} else {
  fs.writeFileSync(target, text);
  console.log('Exported existing symbol groups. No financial data was generated.');
}
