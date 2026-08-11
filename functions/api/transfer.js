/**
 * 端末の引き継ぎ。会員登録の代わりに、短命なコードで記録を受け渡す。
 *
 *   POST /api/transfer         … 記録を預けてコードを受け取る
 *   GET  /api/transfer?code=…  … コードで記録を取り出す
 *
 * 個人情報は持たない。期限（3日）を過ぎたものは取り出せず、掃除で消える。
 * コードは総当たりされないよう、まぎらわしい文字を除いた32種×8桁にしている。
 */

const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';   // I,O,0,1 は除く
const CODE_LEN = 8;
const TTL_DAYS = 3;
const MAX_BODY = 2 * 1024 * 1024;   // 2MB。実戦500件でも1MBに満たない

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });

function newCode() {
  const buf = new Uint8Array(CODE_LEN);
  crypto.getRandomValues(buf);
  let s = '';
  for (const b of buf) s += ALPHABET[b % ALPHABET.length];
  return s;
}

/** 見た目の区切りや小文字のゆらぎを吸収する */
const normalize = (s) => String(s || '').toUpperCase().replace(/[^A-Z0-9]/g, '');

/** 期限切れを片づける。掃除のためだけに定期実行は用意しない */
const sweep = (db) =>
  db.prepare('DELETE FROM transfers WHERE expires_at < ?').bind(new Date().toISOString()).run();

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const len = Number(request.headers.get('content-length') || 0);
  if (len > MAX_BODY) return json({ ok: false, error: '記録が大きすぎます' }, 400);

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return json({ ok: false, error: 'JSONとして読めません' }, 400);
  }

  const records = body && body.records;
  if (!Array.isArray(records) || !records.length) {
    return json({ ok: false, error: '引き継ぐ記録がありません' }, 400);
  }
  if (records.length > 500) return json({ ok: false, error: '記録が多すぎます' }, 400);

  const payload = JSON.stringify({ records, machine: body.machine || null });
  if (payload.length > MAX_BODY) return json({ ok: false, error: '記録が大きすぎます' }, 400);

  const db = env.DB;
  await sweep(db);

  const now = new Date();
  const exp = new Date(now.getTime() + TTL_DAYS * 24 * 3600 * 1000);

  // まず起きないが、コードがぶつかったら引き直す
  for (let i = 0; i < 5; i++) {
    const code = newCode();
    const res = await db.prepare(
      'INSERT OR IGNORE INTO transfers (code, payload, created_at, expires_at) VALUES (?,?,?,?)'
    ).bind(code, payload, now.toISOString(), exp.toISOString()).run();
    if (res.meta && res.meta.changes > 0) {
      return json({ ok: true, code, expiresAt: exp.toISOString(), count: records.length });
    }
  }
  return json({ ok: false, error: 'コードを作れませんでした。もう一度お試しください' }, 500);
}

export async function onRequestGet({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const code = normalize(new URL(request.url).searchParams.get('code'));
  if (code.length !== CODE_LEN) return json({ ok: false, error: 'コードの形式が違います' }, 400);

  const db = env.DB;
  const row = await db.prepare(
    'SELECT payload, expires_at FROM transfers WHERE code = ?'
  ).bind(code).first();

  if (!row) return json({ ok: false, error: 'このコードは見つかりません' }, 404);
  if (row.expires_at < new Date().toISOString()) {
    await db.prepare('DELETE FROM transfers WHERE code = ?').bind(code).run();
    return json({ ok: false, error: 'このコードは期限が切れています' }, 410);
  }

  let data;
  try {
    data = JSON.parse(row.payload);
  } catch (e) {
    return json({ ok: false, error: '記録を読み出せませんでした' }, 500);
  }

  return json({ ok: true, records: data.records || [], expiresAt: row.expires_at });
}

export function onRequest() {
  return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET, POST' } });
}
