/**
 * メールのリンクを踏んだときの受け口。
 * トークンを1回だけ使わせ、セッションのCookieを付けてアプリへ戻す。
 */
import {
  cookieHeader, newId, randomToken, addDays, SESSION_DAYS, CONSENT_VERSION,
} from '../_auth.js';

function back(origin, status, next) {
  // 戻り先はここでもう一度確かめる。リンクの中身は書き換えられうるので、
  // 同じサイトのパス以外はカウンターに戻す（外への踏み台にしない）
  const safe = typeof next === 'string' && /^\/[A-Za-z0-9/_\-.]*$/.test(next)
    ? next : '/kabaneri-unato/';
  return `${origin}${safe}?login=${status}`;
}

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const origin = url.origin;
  if (!env.DB) return Response.redirect(back(origin, 'error', ''), 302);

  const token = url.searchParams.get('t') || '';
  const next = url.searchParams.get('next') || '';
  const db = env.DB;

  const row = await db.prepare(
    `SELECT email, expires_at, used_at FROM login_tokens WHERE token = ?`
  ).bind(token).first();

  if (!row) return Response.redirect(back(origin, 'invalid', next), 302);
  if (row.used_at) return Response.redirect(back(origin, 'used', next), 302);
  if (Date.parse(row.expires_at) < Date.now()) {
    return Response.redirect(back(origin, 'expired', next), 302);
  }

  const now = new Date().toISOString();
  await db.prepare(`UPDATE login_tokens SET used_at = ? WHERE token = ?`).bind(now, token).run();

  // 初めてのアドレスならここで登録になる。
  // 保存と提供の同意は、登録する時点で得ている前提（画面側でまとめて示す）
  let user = await db.prepare(`SELECT id FROM users WHERE email = ?`).bind(row.email).first();
  if (!user) {
    const id = newId('u_');
    await db.prepare(
      `INSERT INTO users (id, email, created_at, consent_at, consent_version) VALUES (?,?,?,?,?)`
    ).bind(id, row.email, now, now, CONSENT_VERSION).run();
    user = { id };
  }

  const session = randomToken(32);
  await db.prepare(
    `INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?,?,?,?)`
  ).bind(session, user.id, now, addDays(SESSION_DAYS)).run();

  return new Response(null, {
    status: 302,
    headers: {
      location: back(origin, 'ok', next),
      'set-cookie': cookieHeader(session, SESSION_DAYS * 24 * 3600),
    },
  });
}
