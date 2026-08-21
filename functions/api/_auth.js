/**
 * ログインまわりの共通部品。
 *
 * パスワードは持たない。メールに届いた使い捨てリンクを押せた人を本人とみなす。
 * セッションは HttpOnly の Cookie に入れる。JS から読めないようにして、
 * 万一ページに他人のスクリプトが混ざっても持ち出されないようにする。
 */

export const SESSION_COOKIE = 'ms_session';
export const SESSION_DAYS = 180;      // 打つ頻度が低い人でも、次に来たとき入り直さずに済む長さ
export const LOGIN_TTL_MIN = 30;      // メールのリンクの有効時間
export const CONSENT_VERSION = '2026-08-21';

/** 推測されない文字列。ログインリンクとセッションの両方に使う */
export function randomToken(bytes = 32) {
  const a = new Uint8Array(bytes);
  crypto.getRandomValues(a);
  return [...a].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function newId(prefix) {
  return prefix + randomToken(8);
}

export function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...headers },
  });
}

/** メールアドレスの形だけ見る。実在確認はリンクが届くかどうかで足りる */
export function normalizeEmail(raw) {
  const e = String(raw || '').trim().toLowerCase();
  if (e.length > 254) return null;
  if (!/^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/.test(e)) return null;
  return e;
}

export function cookieHeader(token, maxAgeSec) {
  const parts = [
    `${SESSION_COOKIE}=${token}`,
    'Path=/',
    'HttpOnly',
    'Secure',
    'SameSite=Lax',
    `Max-Age=${maxAgeSec}`,
  ];
  return parts.join('; ');
}

export function readCookie(request, name) {
  const raw = request.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const i = part.indexOf('=');
    if (i < 0) continue;
    if (part.slice(0, i).trim() === name) return part.slice(i + 1).trim();
  }
  return null;
}

/** いまログインしている人。していなければ null */
export async function currentUser(request, db) {
  const token = readCookie(request, SESSION_COOKIE);
  if (!token) return null;
  const row = await db.prepare(
    `SELECT u.id AS id, u.email AS email, s.expires_at AS expires_at
       FROM sessions s JOIN users u ON u.id = s.user_id
      WHERE s.token = ?`
  ).bind(token).first();
  if (!row) return null;
  if (Date.parse(row.expires_at) < Date.now()) return null;
  return { id: row.id, email: row.email };
}

export function addDays(days) {
  return new Date(Date.now() + days * 24 * 3600 * 1000).toISOString();
}

export function addMinutes(min) {
  return new Date(Date.now() + min * 60 * 1000).toISOString();
}
