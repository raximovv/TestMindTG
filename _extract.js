// Pull the 50 items, scoring, and archetype content straight from the live site,
// and produce a cross-check set (random answers -> archetype) from the REAL JS
// scorer, so the Python port can be proven identical.
const fs = require('fs'), vm = require('vm');
const SITE = 'C:/Users/Asus/TestMind-site/';
const ctx = { console, Math };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(SITE + 'characters.js', 'utf8'), ctx);       // ARCHETYPES, FAMILIES
const html = fs.readFileSync(SITE + 'test.html', 'utf8');
const m = html.match(/<script id="tm-logic">([\s\S]*?)<\/script>/);
vm.runInContext(m[1], ctx);                                                   // ITEMS, scoreAnswers, ...

const arche = {};
for (const k in ctx.ARCHETYPES){
  const a = ctx.ARCHETYPES[k];
  arche[k] = { name: a.name, slug: a.slug, famName: ctx.FAMILIES[a.fam].name,
               color: ctx.FAMILIES[a.fam].c, lines: a.lines, strength: a.strength,
               watch: a.watch, figure: a.figure };
}
fs.writeFileSync('bot_content.json', JSON.stringify({
  items: ctx.ITEMS, traits: ctx.TRAITS, poles: ctx.POLES, texts: ctx.TEXTS,
  trait_order: ctx.TRAIT_ORDER, disclaimer: ctx.DISCLAIMER, archetypes: arche
}, null, 1));

// cross-check dataset: full 1..5 answer vectors (what the bot always produces)
const N = 6000, cases = [];
for (let i = 0; i < N; i++){
  const a = ctx.ITEMS.map(() => 1 + Math.floor(Math.random() * 5));
  const s = ctx.scoreAnswers(a);
  cases.push({ a, key: ctx.archetypeKeyOf(s) });
}
fs.writeFileSync('xcheck.json', JSON.stringify(cases));
console.log('items:', ctx.ITEMS.length, '| archetypes:', Object.keys(arche).length,
            '| trait counts:', ctx.ITEMS.reduce((m,it)=>((m[it.d]=(m[it.d]||0)+1),m),{}),
            '| xcheck:', N);
