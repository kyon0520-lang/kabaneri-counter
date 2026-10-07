/**
 * 管理画面から保存される内容の確認。
 *
 * 画面側でも形を整えてから送るが、ここでもう一度確かめる。
 * - 書き換えてよいファイルを決めておく（functions/ や設定ファイルには触らせない）
 * - 記事のページには、決まった3つ（構造化データ、アクセス解析のタグ、AdSense のコード）以外のスクリプトを入れさせない
 * - トップページは、スクリプトなどが増えていないことを、いまの版と比べて確かめる
 */
import { GhError } from './_github.js';

const ARTICLE = /^column\/[a-z0-9]+(?:-[a-z0-9]+)*\.html$/;
const FIXED = ['column/index.html', 'src/top.html', 'index.html', 'sitemap.xml'];

export const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

const ALLOWED_SCRIPTS = [
  /<script type="application\/ld\+json">[^<]*<\/script>/g,
  /<script defer src="https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js" data-cf-beacon='\{"token": "[0-9a-f]+"\}'><\/script>/g,
  /<script async src="https:\/\/pagead2\.googlesyndication\.com\/pagead\/js\/adsbygoogle\.js\?client=ca-pub-8933350487899087" crossorigin="anonymous"><\/script>/g,
];
const DANGER = [
  /<script/gi, /<[^>]*\son[a-z]+\s*=/gi, /javascript:/gi,
  /<(?:iframe|object|embed|form|base)\b/gi, /<meta[^>]+http-equiv/gi,
];

function dangerCount(text, stripAllowed) {
  let s = text;
  if (stripAllowed) for (const re of ALLOWED_SCRIPTS) s = s.replace(re, '');
  return DANGER.reduce((n, re) => n + (s.match(re) || []).length, 0);
}

function bad(msg) { return new GhError(msg, 400); }

/**
 * files: [{ path, text | null, sha }]、current: いまの版（readFiles の結果）
 */
export function checkFiles(files, current) {
  if (!Array.isArray(files) || !files.length) throw bad('保存するファイルがありません');
  if (files.length > 200) throw bad('ファイルが多すぎます');
  const seen = new Set();
  for (const f of files) {
    if (!f || typeof f.path !== 'string') throw bad('形式が不正です');
    if (seen.has(f.path)) throw bad(`${f.path} が重複しています`);
    seen.add(f.path);
    const isArticle = ARTICLE.test(f.path) && f.path !== 'column/index.html';
    if (!isArticle && !FIXED.includes(f.path)) throw bad(`${f.path} は管理画面から変更できません`);
    if (f.text == null) {
      if (!isArticle) throw bad(`${f.path} は消せません`);
      continue;
    }
    if (typeof f.text !== 'string' || f.text.length > 900000) throw bad(`${f.path} の中身が不正です`);

    if (f.path.startsWith('column/')) {
      if (!f.text.includes('<main class="wrap">') || !f.text.trimEnd().endsWith('</html>')) {
        throw bad(`${f.path} のページの形が崩れています`);
      }
      if (dangerCount(f.text, true)) throw bad(`${f.path} に使えないタグ（スクリプトなど）が入っています`);
    } else {
      const cur = current[f.path];
      if (!cur) throw bad(`${f.path} が見つかりません`);
      if (dangerCount(f.text, false) > dangerCount(cur.text, false)) {
        throw bad(`${f.path} に使えないタグ（スクリプトなど）が増えています`);
      }
    }
  }
  // 公開されるトップ（index.html）は src/top.html と同じ中身（src/top-mode.py full の書き出し）
  const top = files.find((f) => f.path === 'src/top.html');
  const idx = files.find((f) => f.path === 'index.html');
  if (!!top !== !!idx || (top && top.text !== idx.text)) {
    throw bad('src/top.html と index.html は同じ中身で一緒に保存してください');
  }
}

/** 日本時間の今日（YYYY-MM-DD） */
export function todayJst() {
  return new Date(Date.now() + 9 * 3600 * 1000).toISOString().slice(0, 10);
}
