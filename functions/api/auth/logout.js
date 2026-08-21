/** この端末のセッションだけ切る。ほかの端末は入ったまま */
import { json, readCookie, cookieHeader, SESSION_COOKIE } from '../_auth.js';

export async function onRequestPost({ request, env }) {
  const token = readCookie(request, SESSION_COOKIE);
  if (token && env.DB) {
    await env.DB.prepare(`DELETE FROM sessions WHERE token = ?`).bind(token).run();
  }
  return json({ ok: true }, 200, { 'set-cookie': cookieHeader('', 0) });
}
