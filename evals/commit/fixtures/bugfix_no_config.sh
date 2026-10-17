#!/bin/bash
source "$(dirname "$0")/../../shared/common.sh" "$1"
mkdir -p src test
cat > package.json <<'J'
{ "name": "daterange", "version": "1.2.0", "main": "src/range.js", "scripts": { "test": "node test/range.test.js" } }
J
cat > src/range.js <<'J'
// Returns an array of ISO date strings from start to end (inclusive).
function dateRange(start, end) {
  const out = [];
  const d = new Date(start);
  const last = new Date(end);
  while (d < last) {
    out.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return out;
}
module.exports = { dateRange };
J
cat > test/range.test.js <<'J'
const assert = require('assert');
const { dateRange } = require('../src/range');
assert.deepStrictEqual(dateRange('2026-01-01', '2026-01-01').length, 0);
console.log('ok');
J
git add -A; c 1 "feat(range): add dateRange helper"
echo "# daterange" > README.md; git add -A; c 2 "docs: add readme"
sed -i '' 's/  while (d < last) {/  while (d <= last) {/' src/range.js
cat > test/range.test.js <<'J'
const assert = require('assert');
const { dateRange } = require('../src/range');
assert.deepStrictEqual(dateRange('2026-01-01', '2026-01-01'), ['2026-01-01']);
assert.deepStrictEqual(dateRange('2026-01-30', '2026-02-01'), ['2026-01-30', '2026-01-31', '2026-02-01']);
console.log('ok');
J
git add -A
