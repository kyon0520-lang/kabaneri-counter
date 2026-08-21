/**
 * みんなのスロットの集計。GET /api/stats?machine=kabaneri-unato
 *
 * 送信直後の見返りは records.js が返すので、こちらは画面から集計を見るとき用。
 * 実体は machine_stats に貯めた1行を読むだけ。全件走査はしない
 * （走査していた頃は、件数が増えるほど1日の読み取り上限に早く当たった）。
 */
import { freshStats, STEP } from './_stats.js';

const MACHINES = ['kabaneri-unato'];

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      // 集計はすぐに変わらないので少しだけ持たせる
      'cache-control': 'public, max-age=60',
    },
  });

export async function onRequestGet({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const machine = new URL(request.url).searchParams.get('machine') || MACHINES[0];
  if (!MACHINES.includes(machine)) return json({ ok: false, error: '未対応の機種です' }, 400);

  const s = await freshStats(env.DB, machine);

  return json({
    ok: true,
    machine,
    records: s.records,
    clients: s.clients,
    games: s.games,
    avgPtMedian: s.avgPtMedian,
    glowRateMedian: s.glowRateMedian,
    dist: { step: STEP, buckets: s.dist, total: s.czRows },
    settingReports: s.settingReports,
  });
}

export function onRequest() {
  return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET' } });
}
