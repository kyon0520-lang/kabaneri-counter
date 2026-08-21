/**
 * アカウントと記録をすべて消す。
 *
 * 苦情を苦情のまま終わらせないための装置なので、迷わせない場所に置くこと。
 * 消したものは戻せないので、画面側で必ず一度確認を取る。
 */
import { json, currentUser, cookieHeader, readCookie, SESSION_COOKIE } from '../_auth.js';

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const user = await currentUser(request, env.DB);
  if (!user) return json({ ok: false, error: 'ログインしていません' }, 401);

  const db = env.DB;
  // 集計に混ぜた分も含めて、その人の記録は全部消す。
  // cz_points は records への外部キーだが、D1では明示的に消すほうが確実
  const { results } = await db.prepare(
    `SELECT id FROM records WHERE user_id = ?`
  ).bind(user.id).all();
  const ids = (results || []).map((r) => r.id);

  if (ids.length) {
    const marks = ids.map(() => '?').join(',');
    await db.prepare(`DELETE FROM cz_points WHERE record_id IN (${marks})`).bind(...ids).run();
    await db.prepare(`DELETE FROM records WHERE user_id = ?`).bind(user.id).run();
  }
  await db.prepare(`DELETE FROM sessions WHERE user_id = ?`).bind(user.id).run();
  await db.prepare(`DELETE FROM login_tokens WHERE email = (SELECT email FROM users WHERE id = ?)`)
    .bind(user.id).run();
  await db.prepare(`DELETE FROM users WHERE id = ?`).bind(user.id).run();

  return json({ ok: true, deleted: ids.length }, 200, { 'set-cookie': cookieHeader('', 0) });
}
