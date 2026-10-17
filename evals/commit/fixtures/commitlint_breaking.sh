#!/bin/bash
source "$(dirname "$0")/../../shared/common.sh" "$1"
mkdir -p src/cli src/core .husky
cat > commitlint.config.js <<'J'
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', ['feat', 'fix', 'docs', 'refactor', 'test', 'chore', 'deps']],
    'scope-enum': [2, 'always', ['api', 'cli', 'core']],
    'scope-empty': [2, 'never'],
    'header-max-length': [2, 'always', 60],
  },
};
J
printf '#!/bin/sh\nnpx --no -- commitlint --edit "$1"\n' > .husky/commit-msg
cat > package.json <<'J'
{ "name": "imgpack", "version": "2.4.1", "bin": { "imgpack": "src/cli/index.js" } }
J
cat > src/core/pack.js <<'J'
module.exports = function pack(files, dest) { return { files, dest }; };
J
cat > src/cli/index.js <<'J'
#!/usr/bin/env node
const pack = require('../core/pack');
const args = process.argv.slice(2);
let out = 'dist';
const files = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--out' || args[i] === '-o') out = args[++i];
  else files.push(args[i]);
}
console.log(pack(files, out));
J
cat > README.md <<'J'
# imgpack

    imgpack --out build/ a.png b.png
J
git add -A; c 1 "chore(core): initial commit"
git commit -q --allow-empty -m "feat(cli): support -o shorthand for --out"
# staged change: rename --out to --output, drop --out
sedi "s/args\[i\] === '--out'/args[i] === '--output'/" src/cli/index.js
sedi 's/imgpack --out build/imgpack --output build/' README.md
git add -A
