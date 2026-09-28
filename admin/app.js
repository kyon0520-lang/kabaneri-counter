/**
 * COLUMN 管理画面（minnanoslot.com/admin/）
 *
 * - はじめの画面: 予約中の公開・下書き・公開中の記事
 * - 編集: 本番と同じ見た目のページを、そのまま押して書き換える（iframe の中を contenteditable にする）
 * - 確認: 直す前と直した後を並べて見せ、すぐ公開か予約かを選んで保存する
 *
 * 保存はすべて /api/admin/*（functions/api/admin/）経由で GitHub へのコミットになる。
 */
import * as L from './lib.js';

const $ = (s, r = document) => r.querySelector(s);
const app = $('#app');
const h = (s) => L.esc(s == null ? '' : s);

// ---------------------------------------------------------------- 通信

async function api(path, opt = {}) {
  let r;
  try {
    r = await fetch('/api/admin/' + path, {
      credentials: 'same-origin', ...opt,
      headers: { 'x-admin': '1', ...(opt.body ? { 'content-type': 'application/json' } : {}) },
    });
  } catch (e) {
    throw new Error('通信できませんでした。電波のよい場所でもう一度お試しください');
  }
  let j;
  try { j = await r.json(); } catch (e) { j = { ok: false, error: `サーバーの応答が読めませんでした（${r.status}）` }; }
  if (!j.ok) {
    const e = new Error(j.error || '失敗しました');
    e.need = j.need;
    throw e;
  }
  return j;
}
const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) });

async function readFiles(ref, paths) {
  const r = await api(`files?ref=${encodeURIComponent(ref)}&paths=${encodeURIComponent(paths.join(','))}`);
  return r.files;
}

// ---------------------------------------------------------------- 小さな部品

function busy(text) {
  const d = document.createElement('div');
  d.className = 'busy';
  d.innerHTML = `<div class="spin"></div><div>${h(text)}</div>`;
  document.body.append(d);
  return () => d.remove();
}

/** ダイアログ。buttons: [{ label, value, kind }]。押したボタンの value で解決する */
function dialog({ title, html = '', buttons = [{ label: 'OK', value: true, kind: 'pri' }], onOpen }) {
  return new Promise((resolve) => {
    const ov = document.createElement('div');
    ov.className = 'ov';
    ov.innerHTML = `<div class="sheet" role="dialog" aria-modal="true">
      ${title ? `<h3>${h(title)}</h3>` : ''}<div class="dlg-body">${html}</div>
      <div class="btns">${buttons.map((b, i) => `<button class="btn ${b.kind || ''}" data-i="${i}">${h(b.label)}</button>`).join('')}</div></div>`;
    const close = (v) => { ov.remove(); resolve(v); };
    ov.addEventListener('click', (e) => {
      const b = e.target.closest('[data-i]');
      if (b) {
        const def = buttons[+b.dataset.i];
        if (def.check && !def.check(ov)) return;
        close(typeof def.value === 'function' ? def.value(ov) : def.value);
      } else if (e.target === ov) close(null);
    });
    document.body.append(ov);
    if (onOpen) onOpen(ov);
  });
}
const alertBox = (title, text) => dialog({ title, html: `<p>${h(text)}</p>` });
const confirmBox = (title, html, okLabel = 'はい', kind = 'pri') =>
  dialog({ title, html, buttons: [{ label: 'やめる', value: false }, { label: okLabel, value: true, kind }] });

function showError(e) {
  if (e && e.need === 'login') { location.hash = '#/'; return renderLogin(e.message); }
  return alertBox('うまくいきませんでした', e && e.message || String(e));
}

const jpd = (iso) => (iso ? L.jpDate(iso) : '');
function tomorrowJst() {
  return new Date(Date.now() + 9 * 3600 * 1000 + 24 * 3600 * 1000).toISOString().slice(0, 10);
}

// ---------------------------------------------------------------- ログイン

function renderLogin(msg) {
  S.ov = null;
  app.innerHTML = `<div class="top"><div class="in"><h1>COLUMN管理</h1></div></div>
  <div class="main"><div class="login">
    ${msg ? `<div class="note warn">${h(msg)}</div>` : ''}
    <div class="card">
      <h2>ログイン</h2>
      <p style="font-size:13.5px;color:var(--ink-2);margin:0 0 14px">管理者のメールアドレスを入れてください。ログイン用のリンクが届きます。</p>
      <label class="fld"><span>メールアドレス</span><input type="email" id="lg-mail" autocomplete="email" inputmode="email"></label>
      <button class="btn pri" id="lg-go" style="width:100%;padding:12px">リンクを送る</button>
      <div id="lg-out" style="margin-top:12px"></div>
    </div></div></div>`;
  $('#lg-go').onclick = async () => {
    const email = $('#lg-mail').value.trim();
    const out = $('#lg-out');
    if (!email) return;
    $('#lg-go').disabled = true;
    try {
      const r = await fetch('/api/auth/request', {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ email, next: '/admin/' }),
      }).then((x) => x.json());
      if (r.devLink) out.innerHTML = `<div class="note warn">試験用の設定のため、メールの代わりにリンクを出しています。<br><a href="${h(r.devLink)}">ログインする</a></div>`;
      else if (r.ok) out.innerHTML = '<div class="note ok">メールを送りました。届いたメールのボタンを押すと、この画面に戻ってきます（30分以内・1回だけ使えます）。</div>';
      else out.innerHTML = `<div class="note err">${h(r.error || '送れませんでした')}</div>`;
    } catch (e) {
      out.innerHTML = '<div class="note err">通信できませんでした</div>';
    }
    $('#lg-go').disabled = false;
  };
}

function renderNoAdmin(msg) {
  app.innerHTML = `<div class="top"><div class="in"><h1>COLUMN管理</h1></div></div>
  <div class="main"><div class="login"><div class="note err">${h(msg)}</div>
  <button class="btn" id="lo">ログアウトして、別のアドレスで入り直す</button></div></div>`;
  $('#lo').onclick = logout;
}

async function logout() {
  await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {});
  renderLogin('ログアウトしました');
}

// ---------------------------------------------------------------- はじめの画面

const S = { ov: null };

async function loadOverview() {
  S.ov = await api('overview');
  return S.ov;
}

function titleOf(slug) {
  const e = S.ov && S.ov.articles.find((a) => a.slug === slug);
  return e ? L.unesc(e.title) : '';
}

async function renderHome(flash) {
  E = null;
  flash = flash || S.flash;
  S.flash = null;
  let ov;
  try {
    ov = await loadOverview();
  } catch (e) {
    if (e.need === 'login') return renderLogin();
    if (e.need === 'admin') return renderNoAdmin(e.message);
    app.innerHTML = `<div class="main"><div class="note err">${h(e.message)}</div><button class="btn" onclick="location.reload()">読み込み直す</button></div>`;
    return;
  }
  const sch = ov.scheduled.map((s) => {
    const t = titleOf(s.slug);
    return `<div class="card" style="margin:0 0 8px">
      <button class="item" data-open-sch="${h(s.branch)}"><span class="tx">
        <span class="t"><span class="pill sch">${h(jpd(s.date))} 公開予定</span>${t ? h(t) : `新しい記事（${h(s.slug)}）`}</span>
        <span class="s">${t ? '公開中の記事の直し' : '新しい記事'}・予約用ブランチ ${h(s.branch)}</span></span><span class="go">›</span></button>
      <div class="acts"><button class="btn sm" data-sch-publish="${h(s.branch)}">いますぐ公開</button>
      <button class="btn sm dan" data-sch-cancel="${h(s.branch)}">予約を取り消す</button></div></div>`;
  }).join('');
  const drafts = ov.drafts || [];
  const dr = drafts.map((d) => `<button class="item" data-draft="${h(d.id)}"><span class="tx">
      <span class="t">${d.origin === 'unpublished' ? '<span class="pill off">非公開に戻した記事</span>' : '<span class="pill new">下書き</span>'}${h(d.title || '（タイトル未定）')}</span>
      <span class="s">${h(d.slug ? '/column/' + d.slug : 'URL未定')}・${h(new Date(d.updated_at).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }))} 保存</span></span><span class="go">›</span></button>`).join('');
  const arts = ov.articles.map((a) => {
    const s = ov.scheduled.find((x) => x.slug === a.slug);
    return `<button class="item" data-article="${h(a.slug)}"><span class="tx">
      <span class="t">${s ? `<span class="pill sch">${h(jpd(s.date))} に直しを予約中</span>` : ''}${a.title}</span>
      <span class="s">${h(a.date)} 公開・/column/${h(a.slug)}</span></span><span class="go">›</span></button>`;
  }).join('');

  app.innerHTML = `<div class="top"><div class="in"><h1>COLUMN管理</h1><span class="who">${h(ov.email)}</span>
    <button class="btn sm" id="logout">ログアウト</button></div></div>
  <div class="main">
    ${flash ? `<div class="note ok">${flash}</div>` : ''}
    ${ov.main !== 'main' ? `<div class="note warn">試験用の設定です。本番ではなく <b>${h(ov.main)}</b> ブランチを読み書きしています。</div>` : ''}
    <div class="sec"><h2>予約中の公開 <span class="n">${ov.scheduled.length}</span></h2>
      ${sch || '<div class="list"><div class="empty">予約はありません</div></div>'}
      <p style="font-size:12px;color:var(--ink-3);margin:6px 2px 0">予約した公開は、その日の朝 8時47分ごろに本番に出ます。予約の中身は、公開日の前から GitHub 上では見えます。</p></div>
    <div class="sec"><h2>下書き <span class="n">${drafts.length}</span></h2>
      ${ov.draftsReady ? `<div class="list">${dr}<button class="item" id="new-draft"><span class="tx"><span class="t" style="color:var(--accent)">＋ 新しい記事を書く</span></span></button></div>`
    : '<div class="note warn">下書きの置き場所（データベースの表）がまだ用意されていません。用意ができると、ここで新しい記事を書けるようになります。</div>'}
    </div>
    <div class="sec"><h2>公開中の記事 <span class="n">${ov.articles.length}</span></h2>
      <div class="list">${arts || '<div class="empty">記事がありません</div>'}</div></div>
  </div>`;

  $('#logout').onclick = logout;
  window.scrollTo(0, 0);
}

/** はじめの画面に戻って、知らせを出す（画面の切り替えで知らせが消えないようにする） */
function goHome(flash) {
  E = null;
  if (location.hash === '#/' || location.hash === '') return renderHome(flash);
  S.flash = flash;
  location.hash = '#/';
}

async function homeClick(e) {
  if (E) return;
  const t = e.target.closest('button');
  if (!t) return;
  const d = t.dataset;
  if (d.article) location.hash = '#/article/' + d.article;
  else if (d.openSch) {
    const s = S.ov.scheduled.find((x) => x.branch === d.openSch);
    location.hash = '#/article/' + s.slug;
  } else if (d.draft) location.hash = '#/draft/' + d.draft;
  else if (t.id === 'new-draft') location.hash = '#/draft/new';
  else if (d.schCancel) {
    const s = S.ov.scheduled.find((x) => x.branch === d.schCancel);
    const name = titleOf(s.slug) || s.slug;
    if (!await confirmBox('予約を取り消しますか？', `<p>${h(jpd(s.date))} に公開する予定の「${h(name)}」の予約を取り消します。</p><p>予約していた変更は消えます（本番の記事はいまのまま残ります）。新しい記事の予約だった場合、その記事の文章も消えるので、残したいときは先に開いて中身を控えてください。</p>`, '取り消す', 'dan fill')) return;
    const done = busy('取り消しています…');
    try { await post('scheduled', { action: 'cancel', branch: s.branch }); done(); renderHome('予約を取り消しました。'); } catch (err) { done(); showError(err); }
  } else if (d.schPublish) {
    const s = S.ov.scheduled.find((x) => x.branch === d.schPublish);
    const name = titleOf(s.slug) || s.slug;
    if (!await confirmBox('いますぐ公開しますか？', `<p>${h(jpd(s.date))} に予定していた「${h(name)}」を、いま本番に出します。</p><p>2〜3分ほどで本番に反映されます。</p>`, '公開する')) return;
    const done = busy('公開しています…');
    try { await post('scheduled', { action: 'publish', branch: s.branch }); done(); renderHome(PUBLISHED_MSG); } catch (err) { done(); showError(err); }
  }
}

const PUBLISHED_MSG = '保存しました。<b>2〜3分ほどで本番に反映されます。</b>（GitHub Actions の「COLUMN即時公開」が本番へ出します）';

// ---------------------------------------------------------------- 編集

let E = null;   // いま開いている記事・下書き

const EDITABLE_SPAN = ['tag', 'up', 'down', 'big', 'sub', 'nw'];
const P_CLASS = ['lead', 'note'];

/** 画面で直してよい塊か（表や、特殊な飾りを含む段落は固定） */
function isEditable(el) {
  const t = el.tagName;
  if (t === 'P') { if ([...el.classList].some((c) => !P_CLASS.includes(c))) return false; }
  else if (t === 'DIV') { if (!el.classList.contains('box') || [...el.classList].some((c) => !['box', 'soft'].includes(c))) return false; }
  else if (!['H2', 'H3', 'UL', 'OL'].includes(t)) return false;
  if (el.hasAttribute('style')) return false;
  for (const d of el.querySelectorAll('*')) {
    if (d.hasAttribute('style')) return false;
    const n = d.tagName;
    if (['STRONG', 'B', 'BR', 'EM', 'LI'].includes(n)) { if (d.classList.length) return false; continue; }
    if (n === 'A') { if (d.classList.length) return false; continue; }
    if (n === 'SPAN') {
      const ok = t === 'DIV' && d.parentElement === el ? ['t'] : EDITABLE_SPAN;
      if ([...d.classList].some((c) => !ok.includes(c))) return false;
      continue;
    }
    if (t === 'DIV' && d.parentElement === el && ['P', 'UL', 'OL'].includes(n) && !d.classList.length) continue;
    return false;
  }
  return true;
}

const safeHref = (u) => /^(\/[^\s"<>]*|https:\/\/[^\s"<>]+|#[\w-]*)$/.test(u);
const clean = (s) => s.replace(/^(\s|<br>)+|(\s|<br>)+$/g, '');

/** 直した塊を、生成スクリプトと同じ書き方の HTML にする。使ってよいタグ以外は外す */
function inl(node) {
  let s = '';
  for (const c of node.childNodes) {
    if (c.nodeType === 3) { s += L.esc(c.nodeValue.replace(/ /g, ' ')); continue; }
    if (c.nodeType !== 1) continue;
    const t = c.tagName;
    const bold = t === 'STRONG' || t === 'B' || (c.style && (c.style.fontWeight === 'bold' || +c.style.fontWeight >= 600));
    if (bold) { const x = inl(c); s += x.trim() ? `<strong>${x}</strong>` : x; }
    else if (t === 'A') { const u = c.getAttribute('href') || ''; s += safeHref(u) ? `<a href="${L.escAttr(u)}">${inl(c)}</a>` : inl(c); }
    else if (t === 'BR') s += '<br>';
    else if (t === 'SPAN') { const k = [...c.classList].filter((x) => EDITABLE_SPAN.includes(x)); s += k.length ? `<span class="${k.join(' ')}">${inl(c)}</span>` : inl(c); }
    else if (t === 'DIV' || t === 'P' || t === 'LI') s += (s && !s.endsWith('<br>') ? '<br>' : '') + inl(c);
    else s += inl(c);
  }
  return s;
}

function serializeBlock(el) {
  const t = el.tagName.toLowerCase();
  if (t === 'p') {
    const k = [...el.classList].filter((c) => P_CLASS.includes(c));
    const x = clean(inl(el));
    return x ? `<p${k.length ? ` class="${k.join(' ')}"` : ''}>${x}</p>` : '';
  }
  if (t === 'h2' || t === 'h3') { const x = clean(inl(el)); return x ? `<${t}>${x}</${t}>` : ''; }
  if (t === 'ul' || t === 'ol') {
    const items = [];
    for (const c of el.childNodes) {
      const x = clean(c.nodeType === 3 ? L.esc(c.nodeValue) : c.nodeType === 1 ? inl(c) : '');
      if (x) items.push(x);
    }
    return items.length ? `<${t}>\n${items.map((x) => `<li>${x}</li>`).join('\n')}\n</${t}>` : '';
  }
  if (t === 'div' && el.classList.contains('box')) {
    const parts = [];
    for (const c of el.childNodes) {
      if (c.nodeType === 3) { const x = clean(L.esc(c.nodeValue)); if (x) parts.push(`<p>${x}</p>`); continue; }
      if (c.nodeType !== 1) continue;
      const ct = c.tagName;
      if (ct === 'SPAN' && c.classList.contains('t')) { const x = clean(inl(c)); if (x) parts.push(`<span class="t">${x}</span>`); }
      else if (ct === 'UL' || ct === 'OL') { const x = serializeBlock(c); if (x) parts.push(x); }
      else { const x = clean(inl(c)); if (x) parts.push(`<p>${x}</p>`); }
    }
    return parts.length ? `<div class="box${el.classList.contains('soft') ? ' soft' : ''}">${parts.join('\n')}</div>` : '';
  }
  return '';
}

/** 画面の中身から本文の HTML を作る。直していない塊は、元の HTML をそのまま使う */
function collectBody() {
  const out = [];
  for (const el of blockEls()) {
    if (el.hasAttribute('data-bi')) {
      const i = +el.dataset.bi;
      const b = E.blocks[i];
      if (el.innerHTML === E.init[i]) out.push({ i, sep: b.sep, src: b.src });
      else { const src = serializeBlock(el); if (src) out.push({ i, sep: b.sep, src, changed: true }); }
    } else {
      const src = serializeBlock(el);
      if (src) out.push({ i: null, sep: out.length ? '\n\n' : '\n', src });
    }
  }
  return { list: out, body: L.joinBlocks(out, E.tail) };
}

function blockEls() {
  const main = E.doc.querySelector('main');
  return [...main.children].filter((c) => c.hasAttribute('data-bi') || c.hasAttribute('data-new'));
}

const EDIT_CSS = `
[data-bi],[data-new]{outline:1.5px dashed transparent;outline-offset:5px;border-radius:2px;scroll-margin:90px}
[contenteditable=true]{outline-color:#c9d8f5;cursor:text}
[contenteditable=true]:focus{outline:2px solid #2f6bd8}
[data-cur]{outline:2px solid #2f6bd8 !important}
[data-lock][data-cur]{outline-style:dashed !important;outline-color:#8b8b8b !important}
[data-empty]::before{content:attr(data-ph);color:#aaa;pointer-events:none}
.cta,.related{opacity:.5}
h1.ph{color:#bbb}
a{cursor:text}`;

function markBody(body) {
  const { blocks, tail } = L.splitBlocks(body);
  const marked = blocks.map((b, i) => ({ sep: b.sep, src: b.src.replace(/^<([a-zA-Z][\w-]*)/, `<$1 data-bi="${i}"`) }));
  return { blocks, tail, marked: L.joinBlocks(marked, tail) };
}

/** 編集用のページ（スクリプトは外し、見た目のためのスタイルだけ足す） */
function editorDoc(html, markedBody) {
  let s = L.buildArticle(html, { body: markedBody });
  s = s.replace(/<script\b[\s\S]*?<\/script>/g, '');
  s = s.replace('<head>', `<head><base href="${location.origin}/column/">`);
  s = s.replace('</head>', `<style>${EDIT_CSS}</style></head>`);
  return s;
}

function newBlock(kind) {
  const d = E.doc;
  let el;
  if (kind === 'p') { el = d.createElement('p'); el.dataset.ph = '段落の文章'; }
  else if (kind === 'h2') { el = d.createElement('h2'); el.dataset.ph = '見出し'; }
  else if (kind === 'h3') { el = d.createElement('h3'); el.dataset.ph = '小見出し'; }
  else if (kind === 'ul') { el = d.createElement('ul'); el.innerHTML = '<li></li>'; el.dataset.ph = '箇条書き（改行で次の行）'; }
  else if (kind === 'box') { el = d.createElement('div'); el.className = 'box'; el.innerHTML = '<span class="t">囲みの見出し</span>\n<p>囲みの本文</p>'; }
  el.setAttribute('data-new', '');
  el.contentEditable = 'true';
  return el;
}

function placeCaret(el, atEnd = false) {
  const d = E.doc;
  (el.closest('[contenteditable=true]') || el).focus();
  const r = d.createRange();
  r.selectNodeContents(el.tagName === 'UL' ? (el.lastElementChild || el) : el);
  r.collapse(!atEnd);
  const sel = d.getSelection();
  sel.removeAllRanges();
  sel.addRange(r);
}

function setCur(el) {
  if (E.cur === el) return;
  if (E.cur) E.cur.removeAttribute('data-cur');
  E.cur = el;
  if (el) el.setAttribute('data-cur', '');
  updateTools();
}

function updateEmpty(el) {
  if (!el || !el.dataset.ph) return;
  el.toggleAttribute('data-empty', el.textContent.trim() === '');
}

function topBlock(node) {
  const main = E.doc.querySelector('main');
  while (node && node.parentElement !== main) node = node.parentElement;
  return node && (node.hasAttribute('data-bi') || node.hasAttribute('data-new')) ? node : null;
}

function updateTools() {
  const c = E && E.cur;
  const bar = $('#tools');
  if (!bar) return;
  const editable = c && c.isContentEditable;
  bar.querySelectorAll('[data-need=edit]').forEach((b) => { b.disabled = !editable; });
  bar.querySelectorAll('[data-need=any]').forEach((b) => { b.disabled = !c; });
  $('#msg').textContent = !c ? '直したいところを押してください。文字をそのまま書き換えられます'
    : editable ? (c.hasAttribute('data-new') ? '追加した部分です' : '文字を直せます。太字・リンクは文字を選んでから')
      : 'この部分（表など）は固定です。上下の移動だけできます。中身を直したいときは Claude に依頼してください';
}

let countTimer = 0;
function onEdited() {
  E.dirty = true;
  clearTimeout(countTimer);
  countTimer = setTimeout(() => {
    const n = L.countChars(collectBody().body);
    $('#chars').textContent = `本文 ${n.toLocaleString()}字${E.kind === 'draft' ? '（目安 2,500〜4,000字）' : ''}`;
    fitFrame();
  }, 300);
}

function fitFrame() {
  const f = $('#pv');
  if (f && E.doc) f.style.height = E.doc.documentElement.scrollHeight + 'px';
}

function wireFrame(iframe) {
  const d = iframe.contentDocument;
  E.doc = d;
  E.init = [];
  for (const el of d.querySelectorAll('main > [data-bi]')) {
    E.init[+el.dataset.bi] = el.innerHTML;
    if (isEditable(el)) el.contentEditable = 'true';
    else el.setAttribute('data-lock', '');
  }
  if (E.kind === 'draft' && !blockEls().length) {
    // 空の下書き。書き出しの形（導入・見出し・段落）を置いておく
    const anchor = d.querySelector('main .cta, main .related');
    const lead = newBlock('p'); lead.className = 'lead'; lead.dataset.ph = '導入の文章（この記事で何がわかるかを2〜3文で）';
    const h2 = newBlock('h2');
    const p = newBlock('p');
    for (const el of [lead, h2, p]) { anchor.before(el); updateEmpty(el); }
  }
  syncTitle();

  d.addEventListener('click', (e) => { if (e.target.closest('a')) e.preventDefault(); setCur(topBlock(e.target)); });
  d.addEventListener('focusin', (e) => setCur(topBlock(e.target)));
  d.addEventListener('input', (e) => { updateEmpty(topBlock(e.target)); onEdited(); });
  d.addEventListener('paste', (e) => {
    const b = topBlock(e.target);
    if (!b || !b.isContentEditable) return;
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    d.execCommand('insertText', false, text);
  });
  d.addEventListener('keydown', (e) => {
    if (e.isComposing || e.keyCode === 229) return;   // 日本語の変換中の Enter は確定なので触らない
    const b = topBlock(e.target);
    if (!b || !b.isContentEditable) return;
    const t = b.tagName;
    if (e.key === 'Enter' && !e.shiftKey && ['P', 'H2', 'H3'].includes(t)) {
      e.preventDefault();
      // カーソルの後ろを、新しい段落に分ける
      const sel = d.getSelection();
      const r = sel.getRangeAt(0);
      r.deleteContents();
      const tail = d.createRange();
      tail.setStart(r.endContainer, r.endOffset);
      tail.setEnd(b, b.childNodes.length);
      const frag = tail.extractContents();
      const np = newBlock('p');
      np.append(frag);
      b.after(np);
      updateEmpty(b); updateEmpty(np);
      placeCaret(np);
      np.scrollIntoView({ block: 'center', behavior: 'smooth' });
      onEdited();
    } else if (e.key === 'Backspace' && ['P', 'H2', 'H3'].includes(t) && b.textContent === '' && b.hasAttribute('data-new')) {
      const prev = b.previousElementSibling;
      if (prev && prev.isContentEditable) {
        e.preventDefault();
        b.remove();
        placeCaret(prev, true);
        onEdited();
      }
    }
  });
  new iframe.contentWindow.ResizeObserver(fitFrame).observe(d.body);
  fitFrame();
  updateTools();
  onEdited();
  E.dirty = false;
}

function syncTitle() {
  if (!E.doc) return;
  const h1 = E.doc.querySelector('h1.disp');
  if (!h1) return;
  h1.textContent = E.f.title || 'タイトル';
  h1.classList.toggle('ph', !E.f.title);
}

async function tool(act) {
  const c = E.cur;
  const d = E.doc;
  if (act === 'bold') { d.execCommand('bold'); onEdited(); return; }
  if (act === 'link') {
    const sel = d.getSelection();
    if (!sel.rangeCount || sel.isCollapsed) return alertBox('リンク', 'リンクにしたい文字を先に選んでください。');
    const range = sel.getRangeAt(0).cloneRange();
    const url = await dialog({
      title: 'リンクを付ける',
      html: `<label class="fld"><span>リンク先 <em>サイトの中なら /column/offline のように / から</em></span><input type="text" id="lk" inputmode="url" placeholder="/column/offline"></label>`,
      buttons: [{ label: 'リンクを外す', value: '' }, { label: 'やめる', value: null }, {
        label: '付ける', kind: 'pri', value: (ov) => $('#lk', ov).value.trim(),
        check: (ov) => { const v = $('#lk', ov).value.trim(); if (!safeHref(v)) { $('#lk', ov).style.borderColor = 'var(--danger)'; return false; } return true; },
      }],
      onOpen: (ov) => setTimeout(() => $('#lk', ov).focus(), 50),
    });
    if (url == null) return;
    sel.removeAllRanges(); sel.addRange(range);
    if (url === '') d.execCommand('unlink'); else d.execCommand('createLink', false, url);
    onEdited();
    return;
  }
  if (act.startsWith('add-')) {
    const el = newBlock(act.slice(4));
    if (c) c.after(el);
    else E.doc.querySelector('main .cta, main .related').before(el);
    updateEmpty(el);
    setCur(el);
    if (act === 'add-box') { placeCaret(el.querySelector('.t')); d.execCommand('selectAll'); }
    else placeCaret(el);
    el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    onEdited();
    return;
  }
  if (!c) return;
  if (act === 'up' || act === 'down') {
    const els = blockEls();
    const i = els.indexOf(c);
    const j = act === 'up' ? i - 1 : i + 1;
    if (j < 0 || j >= els.length) return;
    if (act === 'up') els[j].before(c); else els[j].after(c);
    c.scrollIntoView({ block: 'center', behavior: 'smooth' });
    onEdited();
    return;
  }
  if (act === 'del') {
    if (!c.isContentEditable) return;
    const text = c.textContent.trim();
    if (text && !await confirmBox('この部分を消しますか？', `<div class="diff"><div class="b old">${h(text.slice(0, 300))}${text.length > 300 ? '…' : ''}</div></div><p>保存するまでは本番には影響しません。</p>`, '消す', 'dan fill')) return;
    const next = c.nextElementSibling;
    c.remove();
    setCur(null);
    if (next) next.scrollIntoView({ block: 'center' });
    onEdited();
  }
}

// ---------------------------------------------------------------- 編集画面を開く

async function openArticle(slug) {
  const done = busy('記事を読み込んでいます…');
  try {
    if (!S.ov) await loadOverview();
    const sch = S.ov.scheduled.find((s) => s.slug === slug);
    const ref = sch ? sch.branch : S.ov.main;
    const files = await readFiles(ref, [`column/${slug}.html`, 'column/index.html']);
    const f = files[`column/${slug}.html`];
    if (!f) throw new Error(`column/${slug}.html が見つかりません`);
    const entries = L.parseIndex(files['column/index.html'].text);
    const entry = entries.find((e) => e.slug === slug);
    if (!entry) throw new Error('一覧（column/index.html）にこの記事がありません');
    const a = L.parseArticle(f.text);
    const f0 = { title: a.title, desc: a.desc, short: L.unesc(entry.short) };
    E = {
      kind: 'article', slug, ref, from: sch ? sch.branch : null, schDate: sch ? sch.date : null,
      isNewInBranch: sch && !S.ov.articles.some((x) => x.slug === slug),
      file: f, html: f.text, a, f: { ...f0 }, f0, dirty: false,
    };
    done();
    renderEditor();
  } catch (e) { done(); await showError(e); location.hash = '#/'; }
}

async function openDraft(id) {
  const done = busy('読み込んでいます…');
  try {
    if (!S.ov) await loadOverview();
    const d = id === 'new'
      ? { id: null, slug: '', title: '', description: '', short: '', body: '', cta: L.ctaHtml(['matsuwaru']), origin: 'new', after_slug: '' }
      : (await api('drafts?id=' + encodeURIComponent(id))).draft;
    const idx = await readFiles(S.ov.main, ['column/index.html']);
    const entries = L.parseIndex(idx['column/index.html'].text);
    const tplSlug = entries[0].slug;
    const tpl = (await readFiles(S.ov.main, [`column/${tplSlug}.html`]))[`column/${tplSlug}.html`].text;
    const f0 = { slug: d.slug, title: d.title, desc: d.description, short: d.short, tools: L.ctaKeys(d.cta), after: d.after_slug };
    const html = L.newArticle(tpl, {
      slug: d.slug || 'new', title: d.title || 'タイトル', desc: d.description || '', date: L.todayJst(),
      body: d.body || '', cta: d.cta || '', related: L.relatedHtml(entries, d.slug),
    });
    E = { kind: 'draft', id: d.id, origin: d.origin, origDate: d.orig_date || '', entries, tpl, html, a: L.parseArticle(html), f: { ...f0 }, f0, dirty: false };
    done();
    renderEditor();
  } catch (e) { done(); await showError(e); location.hash = '#/'; }
}

function renderEditor() {
  const isDraft = E.kind === 'draft';
  const f = E.f;
  const cnt = (s) => [...(s || '')].length;
  const tools = Object.entries(L.TOOLS).map(([k, t]) => `<label><input type="checkbox" value="${k}" ${f.tools && f.tools.includes(k) ? 'checked' : ''}>${h(t[1])}</label>`).join('');
  const afterOpts = isDraft ? ['<option value="">いちばん最後</option>']
    .concat(E.entries.map((e) => `<option value="${h(e.slug)}" ${f.after === e.slug ? 'selected' : ''}>「${h(short30(L.stripTags(e.title)))}」の後ろ</option>`)).join('') : '';

  app.innerHTML = `<div class="top"><div class="in"><button class="btn sm" id="back">‹ 戻る</button>
    <h1>${isDraft ? (E.origin === 'unpublished' ? '非公開に戻した記事' : '新しい記事の下書き') : '記事を直す'}</h1></div></div>
  <div class="main">
    ${E.from ? `<div class="note warn">この記事には <b>${h(jpd(E.schDate))} の公開予約</b>があります。予約している内容を直しています（本番はまだ前のままです）。</div>` : ''}
    ${isDraft ? `<details class="rules"><summary>記事を書くときの決まり</summary><ul>
      <li>題材は、自分で作ったツールと、自分の集計だけ。ほかのサイトの転載や、よくある解説の言い換えは書かない</li>
      <li>本文は 2,500〜4,000字くらい。です・ます調で、専門用語はかみくだく</li>
      <li>数字には元の数も添える（例：178日 / 219日）。集計の条件（期間・日数・除いたもの）と、偶然でどのくらいブレるかも書く</li>
      <li>表は色付きの表にする（画像にしない）。進捗バーのような棒グラフは使わない。表が要る記事は、Mac で作ってもらってからここで仕上げる</li>
      <li>遊技をあおらない。最後は「無理のない範囲で、自己判断で」の一文で締める</li>
      <li>公開は2〜3日おきに1本ずつ（一度に何本も出さない）</li></ul></details>` : ''}
    ${isDraft ? `<label class="fld"><span>URL の名前 <em>半角の英小文字・数字・ハイフン</em></span>
      <div class="pre"><b>minnanoslot.com/column/</b><input type="text" id="f-slug" value="${h(f.slug)}" autocapitalize="off" autocomplete="off" spellcheck="false" placeholder="toho-example"></div>
      <div class="hint" id="slug-hint"></div></label>` : ''}
    <label class="fld"><span>タイトル <em id="c-title">${cnt(f.title)}字</em></span><input type="text" id="f-title" value="${h(f.title)}"></label>
    <label class="fld"><span>ひとこと紹介 <em>一覧・トップ・「ほかのCOLUMN」に出る　<b id="c-short">${cnt(f.short)}字</b></em></span><textarea id="f-short" rows="2">${h(f.short)}</textarea></label>
    <label class="fld"><span>説明文 <em>検索結果に出る。120字くらいまで　<b id="c-desc">${cnt(f.desc)}字</b></em></span><textarea id="f-desc" rows="3">${h(f.desc)}</textarea></label>
    ${isDraft ? `<div class="fld"><span>記事の下のツール案内</span><div class="chk" id="f-tools">${tools}</div></div>
      <label class="fld"><span>一覧での並び</span><select id="f-after">${afterOpts}</select><div class="hint">テーマの近い記事の後ろに置くと読みやすくなります</div></label>` : ''}
    <div class="pv-head"><b>仕上がり（押すとそのまま直せます）</b><span id="chars"></span></div>
    <div class="pv"><iframe id="pv" title="仕上がり"></iframe></div>
    ${!isDraft && !E.from && !E.isNewInBranch ? '<p style="margin:26px 0 0;text-align:center"><button class="btn dan sm" id="unpub">この記事を非公開に戻す</button></p>' : ''}
  </div>
  <div class="bar"><div class="in">
    <div class="tools" id="tools">
      <button class="btn" data-act="bold" data-need="edit"><b>太字</b></button>
      <button class="btn" data-act="link" data-need="edit">リンク</button>
      <span class="sepv"></span>
      <button class="btn" data-act="add-p">＋段落</button>
      <button class="btn" data-act="add-h2">＋見出し</button>
      <button class="btn" data-act="add-h3">＋小見出し</button>
      <button class="btn" data-act="add-ul">＋箇条書き</button>
      <button class="btn" data-act="add-box">＋囲み</button>
      <span class="sepv"></span>
      <button class="btn" data-act="up" data-need="any">↑</button>
      <button class="btn" data-act="down" data-need="any">↓</button>
      <button class="btn dan" data-act="del" data-need="edit">消す</button>
    </div>
    <p class="msg" id="msg"></p>
    <div class="row">${isDraft ? '<button class="btn" id="save-draft">下書きを保存</button>' : ''}
      <button class="btn pri" id="review">変更を確認して公開へ</button></div>
  </div></div>`;

  const bind = (id, key, counter) => {
    const el = $('#' + id);
    if (!el) return;
    el.addEventListener('input', () => {
      E.f[key] = el.value.replace(/\s*\n\s*/g, ' ');
      if (counter) $('#' + counter).textContent = cnt(E.f[key]) + '字';
      E.dirty = true;
      if (key === 'title') syncTitle();
      if (key === 'slug') checkSlug();
    });
  };
  bind('f-title', 'title', 'c-title');
  bind('f-short', 'short', 'c-short');
  bind('f-desc', 'desc', 'c-desc');
  bind('f-slug', 'slug');
  if (isDraft) {
    $('#f-tools').addEventListener('change', () => { E.f.tools = [...$('#f-tools').querySelectorAll('input:checked')].map((x) => x.value); E.dirty = true; });
    $('#f-after').addEventListener('change', (e) => { E.f.after = e.target.value; E.dirty = true; });
    checkSlug();
  }

  const m = markBody(E.a.body);
  E.blocks = m.blocks;
  E.tail = m.tail;
  E.cur = null;
  const iframe = $('#pv');
  iframe.addEventListener('load', () => wireFrame(iframe), { once: true });
  iframe.srcdoc = editorDoc(E.html, m.marked);

  $('#tools').addEventListener('pointerdown', (e) => { if (e.target.closest('button')) e.preventDefault(); });
  $('#tools').addEventListener('click', (e) => { const b = e.target.closest('[data-act]'); if (b) tool(b.dataset.act); });
  $('#back').onclick = () => { location.hash = '#/'; };
  $('#review').onclick = () => review();
  if ($('#save-draft')) $('#save-draft').onclick = () => saveDraft(true);
  if ($('#unpub')) $('#unpub').onclick = () => unpublish();
  keepBarAboveKeyboard();
  window.scrollTo(0, 0);
}

const short30 = (s) => ([...s].length > 30 ? [...s].slice(0, 30).join('') + '…' : s);

function slugProblem(s) {
  if (!s) return 'URL の名前を入れてください';
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(s)) return '半角の英小文字・数字と、間のハイフンだけ使えます';
  if (s === 'index' || s === 'column') return 'この名前は使えません';
  if (E.entries.some((e) => e.slug === s)) return '同じ名前の記事がすでにあります';
  if (S.ov.scheduled.some((x) => x.slug === s)) return '同じ名前の記事が予約されています';
  return '';
}
function checkSlug() {
  const p = slugProblem(E.f.slug);
  const el = $('#slug-hint');
  el.textContent = p || `公開すると https://minnanoslot.com/column/${E.f.slug} になります`;
  el.classList.toggle('bad', !!p);
}

let barWired = false;
function keepBarAboveKeyboard() {
  const vv = window.visualViewport;
  if (!vv || barWired) return;
  barWired = true;
  const f = () => { const bar = $('.bar'); if (bar) bar.style.transform = `translateY(${-Math.max(0, window.innerHeight - vv.height - vv.offsetTop)}px)`; };
  vv.addEventListener('resize', f);
  vv.addEventListener('scroll', f);
}

// ---------------------------------------------------------------- 変更の確認

function blockText(src) {
  return L.stripTags(src.replace(/<\/(li|p|span)>/g, '$&\n').replace(/<br>/g, '\n')).replace(/\n{2,}/g, '\n').trim();
}

/** 1文字ずつの違いに印を付ける（長すぎるときは全体を並べる） */
function diffHtml(a, b) {
  const A = [...a];
  const B = [...b];
  if (A.length * B.length > 4e6) return `<del>${h(a)}</del>\n<ins>${h(b)}</ins>`;
  const n = A.length;
  const m = B.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) {
    dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  }
  let out = '';
  let i = 0;
  let j = 0;
  let mode = '';
  let buf = '';
  const flush = () => { if (buf) out += mode ? `<${mode}>${h(buf)}</${mode}>` : h(buf); buf = ''; };
  const push = (md, ch) => { if (md !== mode) { flush(); mode = md; } buf += ch; };
  while (i < n && j < m) {
    if (A[i] === B[j]) { push('', A[i]); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { push('del', A[i]); i++; }
    else { push('ins', B[j]); j++; }
  }
  while (i < n) push('del', A[i++]);
  while (j < m) push('ins', B[j++]);
  flush();
  return out;
}

function changesHtml(list) {
  const out = [];
  const f = E.f;
  const f0 = E.f0;
  const field = (label, a, b) => { if (a !== b) out.push(`<div class="diff"><div class="h">${label}</div><div class="b">${diffHtml(a || '', b || '')}</div></div>`); };
  if (E.kind === 'draft') {
    return `<div class="diff"><div class="h">新しい記事</div><div class="b"><b>${h(f.title)}</b>\n/column/${h(f.slug)}\n${h(f.short)}</div></div>`;
  }
  field('タイトル', f0.title, f.title);
  field('ひとこと紹介', f0.short, f.short);
  field('説明文（検索結果）', f0.desc, f.desc);
  const used = new Set(list.filter((x) => x.i != null).map((x) => x.i));
  let lastI = -1;
  let moved = false;
  for (const x of list) {
    if (x.i == null) { out.push(`<div class="diff"><div class="h">追加</div><div class="b"><ins>${h(blockText(x.src))}</ins></div></div>`); continue; }
    if (x.i < lastI) moved = true;
    lastI = x.i;
    if (x.changed) out.push(`<div class="diff"><div class="h">変更</div><div class="b">${diffHtml(blockText(E.blocks[x.i].src), blockText(x.src))}</div></div>`);
  }
  E.blocks.forEach((b, i) => { if (!used.has(i)) out.push(`<div class="diff"><div class="h">削除</div><div class="b"><del>${h(blockText(b.src))}</del></div></div>`); });
  if (moved) out.push('<div class="diff"><div class="h">並び</div><div class="b">段落などの並びを入れ替えました</div></div>');
  return out.join('');
}

async function review() {
  if (!E.doc) return;
  const { list, body } = collectBody();
  const f = E.f;
  const isDraft = E.kind === 'draft';
  const problems = [];
  const warns = [];
  if (!f.title.trim()) problems.push('タイトルが空です');
  if (!f.short.trim()) problems.push('ひとこと紹介が空です');
  if (!f.desc.trim()) problems.push('説明文が空です');
  const chars = L.countChars(body);
  if (isDraft) {
    const sp = slugProblem(f.slug);
    if (sp) problems.push(sp);
    if (chars < 300) problems.push('本文がほとんどありません');
    else if (chars < 2500) warns.push(`本文が ${chars.toLocaleString()}字で、目安（2,500字）より短めです`);
    if (!/無理のない範囲/.test(L.stripTags(body))) warns.push('最後の「無理のない範囲で、自己判断で」の一文が見当たりません');
    if (!(f.tools || []).length) warns.push('記事の下のツール案内が選ばれていません');
  }
  const changes = changesHtml(list);
  // 一覧・トップ・ほかのCOLUMN を書き換える予約が重なると、後から取り込む方がぶつかって止まる
  const touchesShared = isDraft || f.title !== E.f0.title || f.short !== E.f0.short;
  const others = S.ov.scheduled.filter((x) => x.branch !== E.from);
  if (touchesShared && others.length) {
    warns.push(`ほかにも予約があります（${others.map((x) => jpd(x.date)).join('、')}）。`
      + 'どちらもトップや一覧を書き換えるので、あとから取り込む方がぶつかって止まることがあります。'
      + '新しい記事やタイトルの変更は、前の予約が公開されてから予約するのが安全です');
  }
  if (!isDraft && !changes) return alertBox('変更がありません', 'まだ何も直していません。');
  if (problems.length) return alertBox('このままでは公開できません', problems.join('\n'));

  const tomorrow = tomorrowJst();
  const defDate = E.schDate || tomorrow;
  const nowLabel = E.from ? '予約をやめて、いますぐ公開' : 'いますぐ公開';
  const html = `
    ${warns.length ? `<div class="note warn">${warns.map(h).join('<br>')}</div>` : ''}
    <p style="font-size:13px;color:var(--ink-2)">${isDraft ? '公開する記事' : '変えたところ（<del>赤</del>が消した文字、<ins>緑</ins>が足した文字）'}</p>
    ${changes}
    <p style="font-size:13px;color:var(--ink-2);margin-top:16px">公開のしかた</p>
    <label class="opt"><input type="radio" name="mode" value="schedule" ${E.from || isDraft ? 'checked' : ''}><span><b>日付を指定して予約</b>
      <small>その日の朝 8時47分ごろに本番に出ます</small>
      <input type="date" id="sch-date" value="${defDate}" min="${tomorrow}" style="margin-top:8px;border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:16px;background:#fff"></span></label>
    <label class="opt"><input type="radio" name="mode" value="now" ${E.from || isDraft ? '' : 'checked'}><span><b>${nowLabel}</b>
      <small>2〜3分ほどで本番に反映されます</small></span></label>
    ${!isDraft && (f.title !== E.f0.title || f.short !== E.f0.short) ? '<p style="font-size:12.5px;color:var(--ink-3)">タイトルかひとこと紹介を変えたので、一覧・ほかの記事の「ほかのCOLUMN」・トップの表示も一緒に直します。</p>' : ''}
    ${isDraft ? '<p style="font-size:12.5px;color:var(--ink-3)">一覧・ほかの記事の「ほかのCOLUMN」・トップの新着・sitemap にも、この記事を足します。</p>' : ''}`;
  const choice = await dialog({
    title: isDraft ? '公開の準備' : '変更の確認',
    html,
    buttons: [{ label: 'もどって直す', value: null }, {
      label: '保存する', kind: 'pri',
      value: (ov) => ({ mode: $('input[name=mode]:checked', ov).value, date: $('#sch-date', ov).value }),
      check: (ov) => {
        const mode = $('input[name=mode]:checked', ov).value;
        const d = $('#sch-date', ov).value;
        if (mode === 'schedule' && !(d >= tomorrow)) { $('#sch-date', ov).style.borderColor = 'var(--danger)'; return false; }
        return true;
      },
    }],
  });
  if (!choice) return;
  const done = busy(choice.mode === 'now' ? '保存して公開しています…' : '予約しています…');
  try {
    if (isDraft) await publishDraft(choice, body);
    else await publishEdit(choice, body);
    done();
    E.dirty = false;
    goHome(choice.mode === 'now' ? PUBLISHED_MSG : `${h(jpd(choice.date))} の朝に公開するよう予約しました。予約中の一覧から、中身の直し・取り消しができます。`);
  } catch (e) { done(); showError(e); }
}

// ---------------------------------------------------------------- 保存（ファイル一式を作ってコミット）

const escText = (s) => L.esc(s.trim());

/** 一覧・全記事・トップをまとめて読み、一覧の中身（entries2）に合わせて直したファイルを返す */
async function relinkFiles(ref, entries2, opts) {
  const { skip = [], topFn, sitemapFn, idxFile } = opts;
  const paths = [...entries2.map((e) => `column/${e.slug}.html`).filter((p) => !skip.includes(p)), 'src/top.html', 'index.html'];
  if (sitemapFn) paths.push('sitemap.xml');
  const got = await readFiles(ref, paths);
  const files = [{ path: 'column/index.html', text: L.buildIndex(idxFile.text, entries2), sha: idxFile.sha }];
  for (const e of entries2) {
    const p = `column/${e.slug}.html`;
    if (skip.includes(p)) continue;
    const g = got[p];
    if (!g) throw new Error(`${p} が見つかりません`);
    const text = L.buildArticle(g.text, { related: L.relatedHtml(entries2, e.slug) });
    if (text !== g.text) files.push({ path: p, text, sha: g.sha });
  }
  const top = got['src/top.html'];
  const topText = L.buildTop(top.text, entries2, topFn(L.parseTop(top.text)));
  if (topText !== top.text) {
    files.push({ path: 'src/top.html', text: topText, sha: top.sha });
    files.push({ path: 'index.html', text: topText, sha: got['index.html'].sha });
  }
  if (sitemapFn) {
    const sm = got['sitemap.xml'];
    const t = sitemapFn(sm.text);
    if (t !== sm.text) files.push({ path: 'sitemap.xml', text: t, sha: sm.sha });
  }
  return files;
}

async function publishEdit(choice, body) {
  const f = E.f;
  const date = choice.mode === 'schedule' ? choice.date : L.todayJst();
  const path = `column/${E.slug}.html`;
  let html = L.buildArticle(E.html, { title: f.title.trim(), desc: f.desc.trim(), body, dateModified: date });
  let files;
  if (f.title !== E.f0.title || f.short !== E.f0.short) {
    const idx = (await readFiles(E.ref, ['column/index.html']))['column/index.html'];
    const entries2 = L.parseIndex(idx.text).map((e) => (e.slug === E.slug ? { ...e, title: escText(f.title), short: escText(f.short) } : e));
    html = L.buildArticle(html, { related: L.relatedHtml(entries2, E.slug) });
    files = [{ path, text: html, sha: E.file.sha },
      ...await relinkFiles(E.ref, entries2, { skip: [path], topFn: (m) => m, idxFile: idx })];
  } else {
    files = [{ path, text: html, sha: E.file.sha }];
  }
  await post('commit', {
    mode: choice.mode, date: choice.date, slug: E.slug, from: E.from, files,
    message: `COLUMN「${f.title.trim().slice(0, 40)}」を管理画面から直す`,
  });
}

function draftPayload(body) {
  const f = E.f;
  return {
    id: E.id, slug: f.slug || '', title: f.title || '', description: f.desc || '', short: f.short || '',
    body: body.trim(), cta: L.ctaHtml(f.tools || []), origin: E.origin || 'new', orig_date: E.origDate || '', after_slug: f.after || '',
  };
}

async function saveDraft(show) {
  const { body } = collectBody();
  const done = show ? busy('下書きを保存しています…') : () => {};
  try {
    const r = await post('drafts', draftPayload(body));
    E.id = r.id;
    E.dirty = false;
    done();
    if (show) {
      history.replaceState(null, '', '#/draft/' + r.id);
      $('#msg').textContent = '下書きを保存しました（本番には出ていません）';
    }
    return r.id;
  } catch (e) { done(); showError(e); throw e; }
}

async function publishDraft(choice, body) {
  const f = E.f;
  const date = choice.mode === 'schedule' ? choice.date : L.todayJst();
  const slug = f.slug;
  // 公開に失敗しても書いたものが残るよう、先に下書きとして保存しておく
  const id = await saveDraft(false);
  const main = S.ov.main;
  const idx = (await readFiles(main, ['column/index.html']))['column/index.html'];
  const entries = L.parseIndex(idx.text);
  if (entries.some((e) => e.slug === slug)) throw new Error('同じ名前の記事がすでにあります');
  const entry = { slug, date: L.jpDate(date), title: escText(f.title), short: escText(f.short) };
  const at = f.after ? entries.findIndex((e) => e.slug === f.after) : -1;
  const entries2 = [...entries];
  entries2.splice(at < 0 ? entries.length : at + 1, 0, entry);
  const tplSlug = entries.find((e) => e.slug !== slug).slug;
  const tpl = (await readFiles(main, [`column/${tplSlug}.html`]))[`column/${tplSlug}.html`].text;
  const html = L.newArticle(tpl, {
    slug, title: f.title.trim(), desc: f.desc.trim(), date, body,
    cta: L.ctaHtml(f.tools || []), related: L.relatedHtml(entries2, slug),
  });
  const files = [{ path: `column/${slug}.html`, text: html, sha: null },
    ...await relinkFiles(main, entries2, {
      skip: [`column/${slug}.html`], topFn: (m) => L.topAdd(m, slug), idxFile: idx,
      sitemapFn: (x) => L.sitemapAdd(x, slug, f.after || (at < 0 ? entries[entries.length - 1].slug : f.after)),
    })];
  await post('commit', {
    mode: choice.mode, date: choice.date, slug, from: null, files, draftId: id,
    message: `COLUMN「${f.title.trim().slice(0, 40)}」を管理画面から公開`,
  });
}

async function unpublish() {
  if (E.dirty) return alertBox('先に変更を片づけてください', '直している途中の変更があります。公開するか、戻って変更を捨ててから、非公開にしてください。');
  const ok = await confirmBox('この記事を非公開に戻しますか？', `<p>「${h(E.f0.title)}」を本番から外します。</p>
    <ul style="padding-left:1.2em;font-size:14px"><li>記事のページは開けなくなります（URL を知っている人にも見えなくなります）</li>
    <li>一覧・ほかの記事の「ほかのCOLUMN」・トップの新着・sitemap からも外します</li>
    <li>中身は下書きとして残るので、あとで公開し直せます</li></ul>
    <p>2〜3分ほどで本番に反映されます。</p>`, '非公開に戻す', 'dan fill');
  if (!ok) return;
  const done = busy('非公開に戻しています…');
  try {
    const main = S.ov.main;
    const idx = (await readFiles(main, ['column/index.html']))['column/index.html'];
    const entries = L.parseIndex(idx.text);
    const i = entries.findIndex((e) => e.slug === E.slug);
    const entries2 = entries.filter((e) => e.slug !== E.slug);
    const cur = (await readFiles(main, [`column/${E.slug}.html`]))[`column/${E.slug}.html`];
    const a = L.parseArticle(cur.text);
    const r = await post('drafts', {
      slug: E.slug, title: a.title, description: a.desc, short: L.unesc(entries[i].short),
      body: a.body.trim(), cta: a.cta, origin: 'unpublished', orig_date: a.date, after_slug: i > 0 ? entries[i - 1].slug : '',
    });
    const files = [{ path: `column/${E.slug}.html`, text: null, sha: cur.sha },
      ...await relinkFiles(main, entries2, {
        topFn: (m) => L.topRemove(m, E.slug, entries2), idxFile: idx, sitemapFn: (x) => L.sitemapRemove(x, E.slug),
      })];
    try {
      await post('commit', { mode: 'now', slug: E.slug, from: null, files, message: `COLUMN「${a.title.slice(0, 40)}」を管理画面から非公開に戻す` });
    } catch (e) {
      await api('drafts?id=' + encodeURIComponent(r.id), { method: 'DELETE' }).catch(() => {});
      throw e;
    }
    done();
    goHome('非公開に戻しました。<b>2〜3分ほどで本番から外れます。</b>中身は「下書き」に残っています。');
  } catch (e) { done(); showError(e); }
}

// ---------------------------------------------------------------- 画面の切り替え

async function route() {
  const m = location.hash.match(/^#\/(article|draft)\/([\w-]+)$/);
  if (m && m[1] === 'article') return openArticle(m[2]);
  if (m && m[1] === 'draft') return openDraft(m[2]);
  return renderHome();
}

let lastHash = location.hash;
window.addEventListener('hashchange', async () => {
  if (E && E.dirty) {
    const leave = await confirmBox('変更を捨てますか？', '<p>保存していない変更があります。このまま移ると、直したところは消えます。</p>', '捨てて移る', 'dan fill');
    if (!leave) { history.replaceState(null, '', lastHash); return; }
    E.dirty = false;
  }
  lastHash = location.hash;
  route();
});
app.addEventListener('click', homeClick);
window.addEventListener('beforeunload', (e) => { if (E && E.dirty) { e.preventDefault(); e.returnValue = ''; } });

if (/[?&]login=/.test(location.search)) {
  const st = new URLSearchParams(location.search).get('login');
  history.replaceState(null, '', location.pathname + location.hash);
  if (st !== 'ok') renderLogin({ invalid: 'ログインのリンクが正しくありません', used: 'このリンクはもう使われています', expired: 'リンクの期限が切れています' }[st] || 'ログインできませんでした');
  else route();
} else {
  route();
}
