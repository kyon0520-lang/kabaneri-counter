/**
 * みんなのスロットの集計。GET /api/stats?machine=kabaneri-unato
 *
 * 送信直後の見返りは records.js が返すので、こちらは画面から集計を見るとき用。
 */

const MACHINES = ['kabaneri-unato'];
const STEP = 15;      // 規定ptの刻み。アプリの分布グラフと合わせる
const BUCKETS = 10;   // 15,30,...,150。150以上は最後にまとめる

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      // 集計はすぐに変わらないので少しだけ持たせる
      'cache-control': 'public, max-age=60',
    },
  });

async function median(db, machine, col) {
  const q = `SELECT ${col} AS v FROM records WHERE machine = ? AND ${col} IS NOT NULL
             ORDER BY ${col}
             LIMIT 1 OFFSET (SELECT COUNT(*) / 2 FROM records WHERE machine = ? AND ${col} IS NOT NULL)`;
  const row = await db.prepare(q).bind(machine, machine).first();
  return row ? row.v : null;
}

export async function onRequestGet({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const machine = new URL(request.url).searchParams.get('machine') || MACHINES[0];
  if (!MACHINES.includes(machine)) return json({ ok: false, error: '未対応の機種です' }, 400);

  const db = env.DB;

  const total = await db.prepare('SELECT COUNT(*) AS n FROM records WHERE machine = ?')
    .bind(machine).first();

  // 規定ptの分布。無名・生駒の突入だけ（銅藍の周期は混ぜない）
  // 刻みと段数はサーバー側の定数なので、そのまま式に埋める。
  // 値の結び付けは書いた番号ではなく出現順なので、? の並びと bind の並びを必ず揃えること
  const rows = await db.prepare(
    `SELECT MIN(pt / ${STEP}, ${BUCKETS}) AS b, COUNT(*) AS n
       FROM cz_points
      WHERE machine = ? AND chara IN ('red','green')
      GROUP BY b ORDER BY b`
  ).bind(machine).all();

  const dist = new Array(BUCKETS + 1).fill(0);
  for (const row of (rows.results || [])) dist[row.b] = row.n;

  const czTotal = await db.prepare(
    `SELECT COUNT(*) AS n FROM cz_points WHERE machine = ? AND chara IN ('red','green')`
  ).bind(machine).first();

  // 設定の申告がどれだけあるか（根拠の強さ別）
  const ev = await db.prepare(
    `SELECT evidence, COUNT(*) AS n FROM records
      WHERE machine = ? AND setting IS NOT NULL GROUP BY evidence`
  ).bind(machine).all();

  return json({
    ok: true,
    machine,
    records: total ? total.n : 0,
    avgPtMedian: await median(db, machine, 'avg_pt'),
    glowRateMedian: await median(db, machine, 'glow_rate'),
    dist: { step: STEP, buckets: dist, total: czTotal ? czTotal.n : 0 },
    settingReports: (ev.results || []).reduce((a, r) => (a[r.evidence || 'unknown'] = r.n, a), {}),
  });
}

export function onRequest() {
  return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET' } });
}
