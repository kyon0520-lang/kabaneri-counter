// admin/lib.js の試験。リポジトリ直下で `node src/test-admin-lib.mjs`
// 実際の column/ のファイルを使い、「何も直さずに組み立て直すと元と同じになる」ことなどを確かめる。
import fs from 'node:fs';
import assert from 'node:assert/strict';
import * as L from '../admin/lib.js';

const rd = (p) => fs.readFileSync(p, 'utf8');
const index = rd('column/index.html');
const top = rd('src/top.html');
const sitemap = rd('sitemap.xml');
const entries = L.parseIndex(index);
let n = 0;
const ok = (name) => { n++; console.log('ok', name); };

assert.ok(entries.length >= 15);
assert.equal(L.buildIndex(index, entries), index);
ok(`一覧（${entries.length}本）を組み立て直すと元と同じ`);

for (const e of entries) {
  const html = rd(`column/${e.slug}.html`);
  const a = L.parseArticle(html);
  assert.equal(L.stripTags(e.title), a.title, e.slug + ' の一覧のタイトルと記事のタイトル');
  assert.equal(L.buildArticle(html, {}), html, e.slug);
  assert.equal(L.buildArticle(html, { title: a.title, desc: a.desc, body: a.body, related: a.related, dateModified: '2030-01-01' }), html, e.slug + '（同じ値で差し替え）');
  const { blocks, tail } = L.splitBlocks(a.body);
  assert.equal(L.joinBlocks(blocks, tail), a.body, e.slug + ' の本文の分割');
  assert.ok(blocks.every((b) => b.src.startsWith('<') && b.src.endsWith('>')), e.slug + ' の塊の形');
  // 並びは一覧の順が決まり。古い記事には並びがずれたものがある（toho-hint-words。作り直すと揃う）ので、中身だけ比べる
  const items = (s) => [...s.matchAll(/<a href="[^"]*">.*?<\/a>\n/g)].map((m) => m[0]).sort();
  assert.deepEqual(items(L.relatedHtml(entries, e.slug)), items(a.related), e.slug + ' のほかのCOLUMN');
  if (L.relatedHtml(entries, e.slug) !== a.related) console.log('  （参考）並びが一覧と違う:', e.slug);
  assert.deepEqual(L.ctaKeys(a.cta).length > 0, true, e.slug + ' のツール案内');
  assert.equal(L.ctaHtml(L.ctaKeys(a.cta)).length, a.cta.trimEnd().length + 1, e.slug + ' のツール案内の組み立て');
}
ok('全記事: 組み立て直し・本文の分割・ほかのCOLUMN が元と同じ');

// タイトルを変えると、title・og:title・h1・構造化データが変わる
{
  const e = entries[0];
  const html = rd(`column/${e.slug}.html`);
  const out = L.buildArticle(html, { title: 'A&B <テスト>', desc: '説明"です"', dateModified: '2030-01-02' });
  assert.ok(out.includes('<title>A&amp;B &lt;テスト&gt;｜みんなのスロット</title>'));
  assert.ok(out.includes('<h1 class="disp">A&amp;B &lt;テスト&gt;</h1>'));
  assert.ok(out.includes('<meta property="og:title" content="A&amp;B &lt;テスト&gt;">'));
  assert.ok(out.includes('<meta name="description" content="説明&quot;です&quot;">'));
  assert.ok(out.includes('"headline": "A&B \\u003cテスト>"'));
  assert.ok(out.includes('"dateModified": "2030-01-02"'));
  const b = L.parseArticle(out);
  assert.equal(b.title, 'A&B <テスト>');
  assert.equal(b.desc, '説明"です"');
  ok('タイトル・説明文の差し替えとエスケープ');
}

// 新しい記事
{
  const tpl = rd(`column/${entries[0].slug}.html`);
  const html = L.newArticle(tpl, {
    slug: 'new-one', title: '新しい記事', desc: '説明', date: '2030-02-03',
    body: '<p>本文</p>', cta: L.ctaHtml(['counter']), related: L.relatedHtml(entries, 'new-one'),
  });
  const a = L.parseArticle(html);
  assert.equal(a.title, '新しい記事');
  assert.equal(a.date, '2030-02-03');
  assert.ok(html.includes('<link rel="canonical" href="https://minnanoslot.com/column/new-one">'));
  assert.ok(html.includes('"datePublished": "2030-02-03", "dateModified": "2030-02-03"'));
  assert.ok(html.includes('"mainEntityOfPage": "https://minnanoslot.com/column/new-one"'));
  assert.ok(html.includes('<p class="meta">2030年2月3日 公開</p>'));
  assert.ok(!html.includes('minnanoslot.com/column/' + entries[0].slug), '型にした記事の URL が残っていない');
  ok('新しい記事の組み立て');
}

// トップ
{
  const model = L.parseTop(top);
  assert.equal(L.buildTop(top, entries, model), top);
  ok(`トップの COLUMN 欄を組み立て直すと元と同じ（新着 ${model.feat}、ほか${model.rows.length}本）`);
  const add = L.topAdd(model, 'new-one');
  assert.equal(add.feat, 'new-one');
  assert.equal(add.rows[0], model.feat);
  assert.equal(add.rows.length, model.rows.length);
  const rem = L.topRemove(model, model.feat, entries);
  assert.equal(rem.feat, model.rows[0]);
  assert.equal(rem.rows.length, model.rows.length);
  assert.ok(!rem.rows.includes(model.feat));
  const rem2 = L.topRemove(model, 'not-there', entries);
  assert.deepEqual(rem2, model);
  ok('トップの新着の入れ替え');
}

// sitemap
{
  const s = L.sitemapAdd(sitemap, 'new-one', entries[0].slug);
  assert.ok(s.includes(`/column/${entries[0].slug}</loc></url>\n  <url><loc>https://minnanoslot.com/column/new-one</loc>`));
  assert.equal(L.sitemapRemove(s, 'new-one'), sitemap);
  ok('sitemap の追加と削除');
}

assert.equal(L.isoDate('2026年9月5日'), '2026-09-05');
assert.equal(L.jpDate('2026-09-05'), '2026年9月5日');
console.log(`\nすべて通過（${n}件）`);
