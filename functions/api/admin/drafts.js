/**
 * 下書き（新しい記事・非公開に戻した記事）。
 * リポジトリは誰でも見られるので、書きかけの文章は GitHub ではなく D1 に置く。
 */
import { json, newId } from '../_auth.js';

const FIELDS = ['slug', 'title', 'description', 'short', 'body', 'cta', 'origin', 'orig_date', 'after_slug'];
const MAX = { body: 200000, cta: 20000 };

export async function onRequestGet({ request, env }) {
  const id = new URL(request.url).searchParams.get('id');
  if (!id) {
    const r = await env.DB.prepare(
      `SELECT id, slug, title, origin, updated_at FROM column_drafts ORDER BY updated_at DESC`
    ).all();
    return json({ ok: true, drafts: r.results || [] });
  }
  const row = await env.DB.prepare(`SELECT * FROM column_drafts WHERE id = ?`).bind(id).first();
  if (!row) return json({ ok: false, error: '下書きが見つかりません' }, 404);
  return json({ ok: true, draft: row });
}

export async function onRequestPost({ request, env }) {
  let b;
  try { b = await request.json(); } catch (e) { return json({ ok: false, error: '形式が不正です' }, 400); }
  const v = {};
  for (const k of FIELDS) {
    const s = b[k] == null ? '' : String(b[k]);
    if (s.length > (MAX[k] || 2000)) return json({ ok: false, error: `${k} が長すぎます` }, 400);
    v[k] = s;
  }
  if (!['new', 'unpublished'].includes(v.origin)) v.origin = 'new';
  const now = new Date().toISOString();
  let id = b.id ? String(b.id) : null;
  if (id) {
    const r = await env.DB.prepare(
      `UPDATE column_drafts SET ${FIELDS.map((k) => `${k} = ?`).join(', ')}, updated_at = ? WHERE id = ?`
    ).bind(...FIELDS.map((k) => v[k]), now, id).run();
    if (!r.meta || !r.meta.changes) return json({ ok: false, error: '下書きが見つかりません' }, 404);
  } else {
    id = newId('d_');
    await env.DB.prepare(
      `INSERT INTO column_drafts (id, ${FIELDS.join(', ')}, created_at, updated_at) VALUES (?, ${FIELDS.map(() => '?').join(', ')}, ?, ?)`
    ).bind(id, ...FIELDS.map((k) => v[k]), now, now).run();
  }
  return json({ ok: true, id, updated_at: now });
}

export async function onRequestDelete({ request, env }) {
  const id = new URL(request.url).searchParams.get('id');
  if (!id) return json({ ok: false, error: '下書きの指定がありません' }, 400);
  await env.DB.prepare(`DELETE FROM column_drafts WHERE id = ?`).bind(id).run();
  return json({ ok: true });
}
