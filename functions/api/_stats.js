/**
 * 集計の貯め込み。
 *
 * これまでは送信のたびに records を全件走査して件数と中央値を出していた。
 * D1は走査した行数を読み取りとして数えるので、貯まるほど1送信が重くなり、
 * 容量の上限より先に「1日の読み取り上限」で受け付けられなくなる。
 *
 * そこで、
 *   - 件数・合計は挿入のときに1行へ足し込む（読み取り1行）
 *   - 中央値と分布は毎回作らず、ときどきだけ作り直して貯めておく
 * という形にして、1送信あたりの読み取りを件数によらず一定にする。
 */

export const STEP = 15;       // 規定ptの刻み。アプリの分布グラフと合わせる
export const BUCKETS = 10;    // 15,30,...,150。150以上は最後にまとめる

// 重い集計を作り直す間隔。件数が増えるほど1回の走査は重くなるが、
// この件数に1回しか走らないので、1件あたりの負担は 1/REAGG_EVERY に薄まる
const REAGG_EVERY = 50;
const REAGG_HOURS = 12;       // 件数が伸びなくても、この時間で作り直す

const parse = (s, fallback) => {
  try { return s ? JSON.parse(s) : fallback; } catch (e) { return fallback; }
};

/** 貯めてある集計を1行読む。無ければ空の形を返す */
export async function readStats(db, machine) {
  const row = await db.prepare(`SELECT * FROM machine_stats WHERE machine = ?`)
    .bind(machine).first();
  if (!row) {
    return {
      machine, records: 0, clients: 0, games: 0, czRows: 0,
      avgPtMedian: null, glowRateMedian: null,
      dist: new Array(BUCKETS + 1).fill(0), settingReports: {},
      aggRecords: 0, aggAt: null,
    };
  }
  return {
    machine,
    records: row.records,
    clients: row.clients,
    games: row.games,
    czRows: row.cz_rows,
    avgPtMedian: row.avg_pt_median,
    glowRateMedian: row.glow_rate_median,
    dist: parse(row.dist_json, new Array(BUCKETS + 1).fill(0)),
    settingReports: parse(row.setting_json, {}),
    aggRecords: row.agg_records,
    aggAt: row.agg_at,
  };
}

/** 1件受け取ったぶんを足し込む。走査はしない */
export async function bumpStats(db, { machine, clientId, games, czRows }) {
  // 初めて見た端末かどうかは、主キーの衝突で判定する。
  // COUNT(DISTINCT) を使うと、そこだけ全件走査になってしまう
  const seen = await db.prepare(
    `INSERT OR IGNORE INTO seen_clients (machine, client_id) VALUES (?,?)`
  ).bind(machine, clientId).run();
  const isNewClient = seen.meta && seen.meta.changes > 0 ? 1 : 0;

  await db.prepare(
    `INSERT INTO machine_stats (machine, records, clients, games, cz_rows)
     VALUES (?,1,?,?,?)
     ON CONFLICT(machine) DO UPDATE SET
       records = records + 1,
       clients = clients + ?,
       games   = games + ?,
       cz_rows = cz_rows + ?`
  ).bind(machine, isNewClient, games, czRows, isNewClient, games, czRows).run();
}

function needsReagg(s) {
  if (!s.aggAt) return true;
  if (s.records - s.aggRecords >= REAGG_EVERY) return true;
  return Date.parse(s.aggAt) < Date.now() - REAGG_HOURS * 3600 * 1000;
}

/**
 * 中央値と分布を作り直して貯める。ここだけ全件を走査する。
 * 走らせるのは REAGG_EVERY 件に1回なので、1件あたりの負担はその分だけ薄まる。
 */
export async function reaggregate(db, machine, stats) {
  // 件数は貯めてあるので、中央値は「並べて真ん中を1件取る」だけでよい。
  // 数え直しの副問い合わせを外せるぶん、走査が半分になる
  const median = async (col) => {
    const n = await db.prepare(
      `SELECT COUNT(*) AS n FROM records WHERE machine = ? AND ${col} IS NOT NULL`
    ).bind(machine).first();
    if (!n || !n.n) return null;
    const row = await db.prepare(
      `SELECT ${col} AS v FROM records WHERE machine = ? AND ${col} IS NOT NULL
        ORDER BY ${col} LIMIT 1 OFFSET ?`
    ).bind(machine, Math.floor(n.n / 2)).first();
    return row ? row.v : null;
  };

  const avgPt = await median('avg_pt');
  const glow = await median('glow_rate');

  const rows = await db.prepare(
    `SELECT MIN(pt / ${STEP}, ${BUCKETS}) AS b, COUNT(*) AS n
       FROM cz_points
      WHERE machine = ? AND chara IN ('red','green')
      GROUP BY b ORDER BY b`
  ).bind(machine).all();
  const dist = new Array(BUCKETS + 1).fill(0);
  for (const r of rows.results || []) dist[r.b] = r.n;

  const ev = await db.prepare(
    `SELECT evidence, COUNT(*) AS n FROM records
      WHERE machine = ? AND setting IS NOT NULL GROUP BY evidence`
  ).bind(machine).all();
  const settingReports = (ev.results || [])
    .reduce((a, r) => (a[r.evidence || 'unknown'] = r.n, a), {});

  await db.prepare(
    `UPDATE machine_stats SET
       avg_pt_median = ?, glow_rate_median = ?, dist_json = ?, setting_json = ?,
       agg_at = ?, agg_records = records
     WHERE machine = ?`
  ).bind(avgPt, glow, JSON.stringify(dist), JSON.stringify(settingReports),
         new Date().toISOString(), machine).run();

  return { ...stats, avgPtMedian: avgPt, glowRateMedian: glow, dist, settingReports };
}

/** 必要なら作り直してから返す */
export async function freshStats(db, machine) {
  const s = await readStats(db, machine);
  if (!needsReagg(s)) return s;
  try {
    return await reaggregate(db, machine, s);
  } catch (e) {
    return s;      // 作り直しに失敗しても、貯めてある分で答える
  }
}
