/**
 * 管理画面の API（/api/admin/*）の入口。ここを通らないと中の処理は動かない。
 *
 * 画面を隠すだけでは守りにならないので、API の1回ごとに次を確かめる。
 * - 既存のメールログインでログインしていること
 * - そのメールアドレスが ADMIN_EMAIL（Cloudflare Pages の秘密の設定）に入っていること
 * - ログインしてから ADMIN_SESSION_DAYS 日以内であること（スマホをなくしたときの備え）
 * - 書き込み（GET 以外）は、同じサイトの画面から送られたこと（ほかのサイトからの成りすまし送信を防ぐ）
 */
import { json, readCookie, SESSION_COOKIE } from '../_auth.js';

export const ADMIN_SESSION_DAYS = 14;

function adminEmails(env) {
  return String(env.ADMIN_EMAIL || '')
    .split(',').map((s) => s.trim().toLowerCase()).filter(Boolean);
}

async function check({ request, env, next, data }) {
  const headers = { 'cache-control': 'no-store', 'x-robots-tag': 'noindex' };
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です（DB）' }, 503, headers);
  const allow = adminEmails(env);
  if (!allow.length) return json({ ok: false, error: 'サーバー側の設定が未完了です（ADMIN_EMAIL）' }, 503, headers);

  const token = readCookie(request, SESSION_COOKIE);
  const row = token && await env.DB.prepare(
    `SELECT u.email AS email, s.created_at AS created_at, s.expires_at AS expires_at
       FROM sessions s JOIN users u ON u.id = s.user_id
      WHERE s.token = ?`
  ).bind(token).first();
  if (!row || Date.parse(row.expires_at) < Date.now()) {
    return json({ ok: false, error: 'ログインしてください', need: 'login' }, 401, headers);
  }
  if (!allow.includes(String(row.email).toLowerCase())) {
    return json({ ok: false, error: 'このアドレスには管理画面の権限がありません', need: 'admin' }, 403, headers);
  }
  if (Date.now() - Date.parse(row.created_at) > ADMIN_SESSION_DAYS * 24 * 3600 * 1000) {
    return json({ ok: false, error: `ログインから${ADMIN_SESSION_DAYS}日たちました。ログインし直してください`, need: 'login' }, 401, headers);
  }

  if (request.method !== 'GET') {
    // 独自のヘッダーは、ほかのサイトのページからは付けて送れない（ブラウザが事前確認で止める）
    const origin = request.headers.get('origin');
    if (origin !== new URL(request.url).origin || request.headers.get('x-admin') !== '1') {
      return json({ ok: false, error: '送信元を確認できませんでした' }, 403, headers);
    }
  }

  data.admin = { email: row.email };
  let res;
  try {
    res = await next();
  } catch (e) {
    // 素の 500 だと画面に理由が出ない。GitHub とのやりとりの失敗などを文章で返す
    res = json({ ok: false, error: String(e && e.message || e) }, e && e.status || 500);
  }
  res = new Response(res.body, res);
  for (const [k, v] of Object.entries(headers)) res.headers.set(k, v);
  return res;
}

export const onRequest = [check];
