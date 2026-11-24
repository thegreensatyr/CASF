// CasinoForensicsUnit — launch gate.
// Run:  node scripts/deploy-check.js
// Exit code 1 = DO NOT DEPLOY. This exists because the previous site went live with made-up stats.
//
// It blocks deploy if:
//   1. any page still has a DRAFT marker (copy not yet approved by Dustin)
//   2. any TODO / PLACEHOLDER / Lorem text remains
//   3. any record in data/casinos.json is missing its sources or check dates
// It also LISTS every number-like claim (percentages, dollar amounts, "N casinos") for a human to confirm.

const fs = require('fs');
const path = require('path');
const ROOT = path.join(__dirname, '..');

const problems = [];
const review = [];

const pages = fs.readdirSync(ROOT).filter(f => f.endsWith('.html'));
for (const f of pages) {
  const text = fs.readFileSync(path.join(ROOT, f), 'utf8');
  const lines = text.split('\n');
  lines.forEach((line, i) => {
    const where = `${f}:${i + 1}`;
    if (/<!--\s*DRAFT/i.test(line)) problems.push(`${where}  DRAFT marker — copy not approved yet`);
    // Case-sensitive on purpose: catches "TODO" / "PLACEHOLDER" markers, not the HTML `placeholder=` attribute.
    if ((/\b(TODO|TBD|PLACEHOLDER)\b/.test(line) && !/PLACEHOLDER CREST/.test(line)) || /lorem ipsum/i.test(line)) problems.push(`${where}  contains TODO/placeholder text`);
    const visible = line.replace(/<[^>]+>/g, ' ');
    const claims = visible.match(/\d[\d,.]*\s?%|\$\s?\d[\d,.]*|\b\d[\d,]*\+?\s+(casinos|reviews|players|users|sites|investigations)\b/gi);
    if (claims) review.push(`${where}  ${claims.join(' | ')}`);
  });
  if (/PLACEHOLDER CREST/.test(text)) problems.push(`${f}  still uses the placeholder crest logo`);
}

try {
  const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'casinos.json'), 'utf8'));
  const FIELDS = ['license', 'redemptionTest', 'termsReviewed', 'stateAvailability'];
  (data.casinos || []).forEach((c, i) => {
    const name = c.name || `record #${i + 1}`;
    if (c.status !== 'verified') problems.push(`casinos.json: ${name} has status "${c.status}" (only "verified" may be listed)`);
    if (!c.verifiedOn) problems.push(`casinos.json: ${name} has no verifiedOn date`);
    if (c.type !== 'real-money' && c.type !== 'sweepstakes') problems.push(`casinos.json: ${name} needs type "real-money" or "sweepstakes"`);
    if (!Array.isArray(c.payoutMethods) || !c.payoutMethods.length) problems.push(`casinos.json: ${name} needs payoutMethods (e.g. ["cash","crypto"])`);
    FIELDS.forEach(f => {
      const v = c[f];
      if (!v || !v.value) problems.push(`casinos.json: ${name} is missing "${f}"`);
      else {
        if (!/^https:\/\//.test(v.sourceUrl || '')) problems.push(`casinos.json: ${name} "${f}" has no https sourceUrl`);
        if (!v.checkedOn) problems.push(`casinos.json: ${name} "${f}" has no checkedOn date`);
      }
    });
  });
} catch (e) {
  problems.push('data/casinos.json could not be read: ' + e.message);
}

console.log('\nCasinoForensicsUnit launch check\n' + '='.repeat(34));
if (review.length) {
  console.log('\nNUMBERS TO CONFIRM (each must have a real source — remove any that do not):');
  review.forEach(r => console.log('  • ' + r));
} else {
  console.log('\nNo percentage / dollar / count claims found.');
}
if (problems.length) {
  console.log('\nBLOCKING PROBLEMS — do not deploy:');
  problems.forEach(p => console.log('  ✖ ' + p));
  console.log(`\nResult: FAIL (${problems.length} problem${problems.length === 1 ? '' : 's'})\n`);
  process.exit(1);
}
console.log('\nResult: PASS — still confirm the numbers above by hand.\n');
