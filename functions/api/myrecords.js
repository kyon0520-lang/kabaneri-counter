/**
 * 自分の実戦記録を読み出す（メニューの「実戦履歴を読み出す」）。
 *
 * 端末に貯め込むのではなく、サーバーから取り直すための口。
 * 集計用の列のままではなく、アプリが履歴として描ける形に組み直して返す。
 *
 * 置き場所を /api/records/mine にしなかったのは、同じ名前のファイルと
 * ディレクトリが並ぶ形を避けるため。
 */
import { json, currentUser } from './_auth.js';

const MAX = 500;   // 一度に返す上限。古いものから省く

export async function onRequestGet({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const user = await currentUser(request, env.DB);
  if (!user) return json({ ok: false, error: 'ログインしていません' }, 401);

  const url = new URL(request.url);
  const machine = url.searchParams.get('machine') || 'kabaneri-unato';

  const { results } = await env.DB.prepare(
    `SELECT id, played_at, games, bell, setting, evidence, payload, memo, wins
       FROM records
      WHERE user_id = ? AND machine = ?
      ORDER BY played_at DESC
      LIMIT ?`
  ).bind(user.id, machine, MAX).all();

  const rows = results || [];
  const ids = rows.map((r) => r.id);

  // CZ突入時のポイントは別テーブルなので、まとめて引いてから配り直す
  const byRecord = {};
  if (ids.length) {
    const marks = ids.map(() => '?').join(',');
    const pts = await env.DB.prepare(
      `SELECT record_id, chara, pt FROM cz_points WHERE record_id IN (${marks})`
    ).bind(...ids).all();
    for (const p of pts.results || []) {
      (byRecord[p.record_id] = byRecord[p.record_id] || []).push({ c: p.chara, pt: p.pt });
    }
  }

  const parse = (s, fallback) => {
    try { return s ? JSON.parse(s) : fallback; } catch (e) { return fallback; }
  };

  const records = rows.map((r) => ({
    id: r.id,
    date: r.played_at,
    machine,
    games: r.games,
    bell: r.bell,
    setting: r.setting,
    evidence: r.evidence,
    chars: parse(r.payload, {}),
    czPointsBy: byRecord[r.id] || [],
    memo: r.memo || '',
    wins: parse(r.wins, []),
    sent: true,
  }));

  return json({ ok: true, records, count: records.length, truncated: rows.length >= MAX });
}
