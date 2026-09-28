/**
 * COLUMN の HTML を読み書きする部品（画面から使う。node の試験からも読み込めるよう DOM は使わない）。
 *
 * 記事のページは column-src/ のスクリプトが作った形をしている。
 * ここではその形を崩さないよう、変えたい部分だけを差し替える。
 * 何も直さずに組み立て直すと、元のファイルと1文字も変わらないことを試験で確かめている（src/test-admin-lib.mjs）。
 */

export const SITE = 'https://minnanoslot.com';

export const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
export const escAttr = (s) => esc(s).replace(/"/g, '&quot;');
export const unesc = (s) => String(s)
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
export const stripTags = (s) => unesc(String(s).replace(/<[^>]+>/g, ''));

/** 記事の下のツール案内（column-src/build_column.py の CTA と同じ） */
export const TOOLS = {
  counter: ['/kabaneri-unato/', 'カバネリ海門発光カウンター',
    'スマスロ カバネリ 海門決戦の発光・CZ・下段ベルを、打ちながら数えるカウンター。登録不要・無料。'],
  manual: ['/kabaneri-unato/manual', 'カバネリ海門発光カウンター 取扱説明書',
    '画面の見かた、数え方、記録の保存と引き継ぎまで。'],
  matsuwaru: ['/matsuwaru/toho/', '全台系まつわるチェッカー（マルハン新宿東宝ビル店）',
    '店長の示唆から、過去に全台系になった機種を逆引きするツール。'],
  omikuji: ['/kabaneri-unato/2takuomikuji/', 'カバネリチャレンジおみくじ',
    'カバネリチャレンジの中押し・右押しの2択をサポートするおみくじアプリ。'],
  events: ['/matsuwaru/toho/events', 'イベント傾向チェッカー',
    '「0のつく日」などのイベントごとに、これまでどの機種が選ばれてきたかを見られます。'],
};

export function ctaHtml(keys) {
  return keys.map((k) => {
    const [href, name, desc] = TOOLS[k];
    return `<a class="cta" href="${href}"><span class="k">TOOL</span><span class="n disp">${name}</span><span class="d">${desc}</span></a>\n`;
  }).join('');
}

/** cta の HTML から、どのツールが入っているかを読む */
export function ctaKeys(html) {
  return Object.keys(TOOLS).filter((k) => html.includes(`<a class="cta" href="${TOOLS[k][0]}">`));
}

// ---------------------------------------------------------------- 日付

/** '2026-09-28' → '2026年9月28日' */
export function jpDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${y}年${m}月${d}日`;
}
/** '2026年9月28日' → '2026-09-28' */
export function isoDate(jp) {
  const m = String(jp).match(/(\d{4})年(\d{1,2})月(\d{1,2})日/);
  return m ? `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}` : '';
}
export function todayJst() {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
}

// ---------------------------------------------------------------- JSON（Python の json.dumps と同じ書き方）

function pyJson(v) {
  if (Array.isArray(v)) return '[' + v.map(pyJson).join(', ') + ']';
  if (v && typeof v === 'object') {
    return '{' + Object.entries(v).map(([k, x]) => JSON.stringify(k) + ': ' + pyJson(x)).join(', ') + '}';
  }
  // </script> で構造化データが途切れないように、< は書き換えておく
  return JSON.stringify(v).replace(/</g, '\\u003c');
}

// ---------------------------------------------------------------- 記事のページ

const RE = {
  title: /<title>([\s\S]*?)｜みんなのスロット<\/title>/,
  desc: /<meta name="description" content="([^"]*)">/,
  ogTitle: /<meta property="og:title" content="([^"]*)">/,
  ogDesc: /<meta property="og:description" content="([^"]*)">/,
  canonical: /<link rel="canonical" href="([^"]*)">/,
  ogUrl: /<meta property="og:url" content="([^"]*)">/,
  ld: /<script type="application\/ld\+json">([^<]*)<\/script>/,
  h1: /<h1 class="disp">([\s\S]*?)<\/h1>/,
  meta: /<p class="meta">([^<]*)<\/p>/,
};

/**
 * 記事のページを部品に分ける。
 * 返り値の title / desc は画面に出す文字（&amp; などは戻してある）。body / cta / related は HTML のまま。
 */
export function parseArticle(html) {
  for (const k of ['title', 'desc', 'h1', 'meta']) {
    if (!RE[k].test(html)) throw new Error(`記事の形が想定と違います（${k} が見つかりません）`);
  }
  const meta = html.match(RE.meta);
  const bodyStart = meta.index + meta[0].length;
  const relStart = html.indexOf('<section class="related">', bodyStart);
  if (relStart < 0) throw new Error('記事の形が想定と違います（ほかのCOLUMN が見つかりません）');
  let ctaStart = html.indexOf('<a class="cta"', bodyStart);
  if (ctaStart < 0 || ctaStart > relStart) ctaStart = relStart;
  const relEnd = html.indexOf('</section>', relStart) + '</section>'.length;
  return {
    title: stripTags(html.match(RE.h1)[1]),
    desc: unesc(html.match(RE.desc)[1]),
    date: isoDate(meta[1]),
    body: html.slice(bodyStart, ctaStart),
    cta: html.slice(ctaStart, relStart),
    related: html.slice(relStart, relEnd),
    _pos: { bodyStart, ctaStart, relStart, relEnd },
  };
}

function setLd(html, fn) {
  const m = html.match(RE.ld);
  if (!m) return html;
  const d = JSON.parse(m[1]);
  fn(d);
  return html.replace(RE.ld, () => `<script type="application/ld+json">${pyJson(d)}</script>`);
}

/**
 * 記事のページを組み立て直す。v に入れた項目だけ差し替える。
 * v: { title, desc, body, cta, related, dateModified, slug, datePublished }
 */
export function buildArticle(html, v) {
  const a = parseArticle(html);
  const p = a._pos;
  let out = html.slice(0, p.bodyStart)
    + (v.body ?? a.body) + (v.cta ?? a.cta) + (v.related ?? a.related) + html.slice(p.relEnd);
  const rep = (re, s) => { out = out.replace(re, () => s); };
  if (v.title != null && v.title !== a.title) {
    rep(RE.title, `<title>${esc(v.title)}｜みんなのスロット</title>`);
    rep(RE.ogTitle, `<meta property="og:title" content="${escAttr(v.title)}">`);
    rep(RE.h1, `<h1 class="disp">${esc(v.title)}</h1>`);
  }
  if (v.desc != null && v.desc !== a.desc) {
    rep(RE.desc, `<meta name="description" content="${escAttr(v.desc)}">`);
    rep(RE.ogDesc, `<meta property="og:description" content="${escAttr(v.desc)}">`);
  }
  if (v.slug) {
    const url = `${SITE}/column/${v.slug}`;
    rep(RE.canonical, `<link rel="canonical" href="${url}">`);
    rep(RE.ogUrl, `<meta property="og:url" content="${url}">`);
  }
  if (v.datePublished) rep(RE.meta, `<p class="meta">${jpDate(v.datePublished)} 公開</p>`);
  const changed = out !== html;
  out = setLd(out, (d) => {
    if (v.title != null) d.headline = v.title;
    if (v.desc != null) d.description = v.desc;
    if (v.slug) d.mainEntityOfPage = `${SITE}/column/${v.slug}`;
    if (v.datePublished) d.datePublished = v.datePublished;
    if (v.dateModified && changed) d.dateModified = v.dateModified;
    else if (v.datePublished) d.dateModified = v.datePublished;
  });
  return out;
}

/**
 * 新しい記事のページを作る。見出し・フッターなどの共通部分は、既存の記事（template）からそのまま借りる。
 * v: { slug, title, desc, date, body, cta, related }
 */
export function newArticle(template, v) {
  return buildArticle(template, {
    slug: v.slug, title: v.title, desc: v.desc, datePublished: v.date,
    body: '\n' + v.body.trim() + '\n\n', cta: v.cta, related: v.related,
  });
}

// ---------------------------------------------------------------- 本文を段落などの塊に分ける

const VOID = new Set(['br', 'img', 'hr', 'input', 'meta', 'link', 'wbr', 'source', 'col', 'area']);

/**
 * 本文を、いちばん外側のタグごとの塊に分ける。
 * 返り値: { blocks: [{ sep: 前の空白など, src: 塊の HTML }], tail }
 * blocks の sep + src を順につなぎ、最後に tail を足すと元の本文に戻る。
 */
export function splitBlocks(body) {
  const blocks = [];
  let i = 0;
  let pending = '';
  const n = body.length;
  while (i < n) {
    const ws = /\S/g;
    ws.lastIndex = i;
    const r = ws.exec(body);
    if (!r) break;
    const start = r.index;
    const sep = body.slice(i, start);
    if (body.startsWith('<!--', start) || body[start] !== '<') {
      // コメントや裸の文字は、次の塊の前置きとして持ち運ぶ
      let end = body.startsWith('<!--', start) ? body.indexOf('-->', start) + 3 : body.indexOf('<', start);
      if (end <= start) end = n;
      pending += sep + body.slice(start, end);
      i = end;
      continue;
    }
    const tag = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*?(\/?)>/g;
    tag.lastIndex = start;
    let depth = 0;
    let end = n;
    let t;
    while ((t = tag.exec(body))) {
      if (t[0].startsWith('<!--')) continue;
      const name = t[2].toLowerCase();
      if (t[1]) depth--;
      else if (!(t[3] || VOID.has(name))) depth++;
      if (depth <= 0) { end = tag.lastIndex; break; }
    }
    blocks.push({ sep: pending + sep, src: body.slice(start, end) });
    pending = '';
    i = end;
  }
  return { blocks, tail: pending + body.slice(i) };
}

export function joinBlocks(blocks, tail) {
  return blocks.map((b) => b.sep + b.src).join('') + tail;
}

/** 本文の文字数（タグと空白を除く。column-src の数え方と同じ） */
export function countChars(html) {
  return stripTags(html).replace(/\s+/g, '').length;
}

// ---------------------------------------------------------------- 一覧（column/index.html）

const ROW = /<a href="\/column\/([\w-]+)"><span class="d">([^<]*)<\/span><span class="n disp">([^<]*)<\/span><span class="s">([^<]*)<\/span><\/a>/g;

/** 一覧の記事。title / short は HTML のまま（一覧・ほかのCOLUMN・トップにそのまま入れる） */
export function parseIndex(html) {
  return [...html.matchAll(ROW)].map((m) => ({ slug: m[1], date: m[2], title: m[3], short: m[4] }));
}

export function indexRow(e) {
  return `<a href="/column/${e.slug}"><span class="d">${e.date}</span><span class="n disp">${e.title}</span><span class="s">${e.short}</span></a>`;
}

export function buildIndex(html, entries) {
  const all = [...html.matchAll(ROW)];
  if (!all.length) throw new Error('一覧の形が想定と違います');
  const first = all[0].index;
  const last = all[all.length - 1];
  const end = last.index + last[0].length;
  return html.slice(0, first) + entries.map(indexRow).join('\n') + html.slice(end);
}

// ---------------------------------------------------------------- ほかのCOLUMN

/** 一覧の並びから、自分を除いた「ほかのCOLUMN」を作る（column-src/articles4.py の related_from_index と同じ） */
export function relatedHtml(entries, self) {
  const items = entries.filter((e) => e.slug !== self)
    .map((e) => `<a href="/column/${e.slug}">${e.title}<span>${e.short}</span></a>\n`).join('');
  return `<section class="related"><h2 class="disp">ほかのCOLUMN</h2>\n${items}</section>`;
}

// ---------------------------------------------------------------- トップページ（src/top.html）の COLUMN 欄

const FEAT = /    <a class="news-feat rv" href="\.\/column\/([\w-]+)">[\s\S]*?<\/a>\n    <div class="news-rest">\n([\s\S]*?)    <\/div>\n/;
const TOPROW = /<a class="news-row rv" href="\.\/column\/([\w-]+)">/g;
const COUNT = /COLUMNの一覧を見る（全\d+本）/;

/** トップにいま出ている記事: { feat: slug, rows: [slug, ...] } */
export function parseTop(html) {
  const m = html.match(FEAT);
  if (!m) throw new Error('トップページの COLUMN 欄の形が想定と違います');
  return { feat: m[1], rows: [...m[2].matchAll(TOPROW)].map((x) => x[1]) };
}

/** 一覧の情報（entries）から、トップの COLUMN 欄を書き直す。model はどの記事を出すか */
export function buildTop(html, entries, model) {
  const by = Object.fromEntries(entries.map((e) => [e.slug, e]));
  const f = by[model.feat];
  if (!f) throw new Error(`トップの新着の記事（${model.feat}）が一覧にありません`);
  const rows = model.rows.filter((s) => by[s]).map((s) => {
    const e = by[s];
    const [, m, d] = isoDate(e.date).split('-');
    return `      <a class="news-row rv" href="./column/${s}">
        <span class="date">${m}.${d} COLUMN</span>
        <span class="ttl">${e.title}</span>
      </a>
`;
  }).join('');
  const block = `    <a class="news-feat rv" href="./column/${f.slug}">
      <div class="meta">
        <span class="news-tag feat">新着</span>
        <span class="date">${f.date}・COLUMN</span>
      </div>
      <div class="ttl">${f.title}</div>
      <p class="lede">${f.short}</p>
      <span class="arrow">→</span>
    </a>
    <div class="news-rest">
${rows}    </div>
`;
  return html.replace(FEAT, () => block).replace(COUNT, () => `COLUMNの一覧を見る（全${entries.length}本）`);
}

/** 新しい記事を新着にする。それまでの新着は下の並びの先頭へ下げ、いちばん古い行を1つ消す */
export function topAdd(model, slug) {
  return { feat: slug, rows: [model.feat, ...model.rows].slice(0, model.rows.length) };
}

/** 記事をトップから外す。空いたところは、出ていない記事のうち新しいものから埋める */
export function topRemove(model, slug, entries) {
  let feat = model.feat;
  let rows = model.rows.filter((s) => s !== slug);
  if (feat === slug) feat = rows.shift();
  const shown = new Set([feat, ...rows]);
  const rest = entries.map((e, i) => ({ e, i })).filter(({ e }) => !shown.has(e.slug) && e.slug !== slug)
    .sort((a, b) => isoDate(b.e.date).localeCompare(isoDate(a.e.date)) || b.i - a.i);
  while (rows.length < model.rows.length && rest.length) rows.push(rest.shift().e.slug);
  return { feat, rows };
}

// ---------------------------------------------------------------- sitemap.xml

const locLine = (slug) => `  <url><loc>${SITE}/column/${slug}</loc></url>`;

export function sitemapAdd(xml, slug, after) {
  if (xml.includes(`<loc>${SITE}/column/${slug}</loc>`)) return xml;
  const lines = xml.split('\n');
  let at = after ? lines.indexOf(locLine(after)) : -1;
  if (at < 0) {
    lines.forEach((l, i) => { if (l.includes(`<loc>${SITE}/column/`)) at = i; });
  }
  if (at < 0) throw new Error('sitemap.xml に COLUMN の行が見つかりません');
  lines.splice(at + 1, 0, locLine(slug));
  return lines.join('\n');
}

export function sitemapRemove(xml, slug) {
  return xml.split('\n').filter((l) => l !== locLine(slug)).join('\n');
}
