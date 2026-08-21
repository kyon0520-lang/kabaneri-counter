/** いまログインしている人を返す。画面の出し分けに使う */
import { json, currentUser } from '../_auth.js';

export async function onRequestGet({ request, env }) {
  if (!env.DB) return json({ ok: true, user: null });
  const user = await currentUser(request, env.DB);
  if (!user) return json({ ok: true, user: null });

  const n = await env.DB.prepare(
    `SELECT COUNT(*) AS n FROM records WHERE user_id = ?`
  ).bind(user.id).first();

  return json({ ok: true, user: { email: user.email, records: (n && n.n) || 0 } });
}
