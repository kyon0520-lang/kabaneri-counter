/**
 * 実戦データの受け口。POST /api/records
 *
 * 同じオリジンからしか呼ばれないので CORS ヘッダーは付けない（付けないことが制限になる）。
 * レコードのIDは端末が採番しているので、再送で二重に届いても INSERT OR IGNORE で弾ける。
 */

import { currentUser } from './_auth.js';
import { bumpStats, freshStats } from './_stats.js';

const MACHINES = {
  'kabaneri-unato': {
    chars: ['red', 'green', 'blue'],
    avgChars: ['red', 'green'],   // 平均pt/CZ と発光率に使うキャラ
    noPt: 1, glowPt: 15, hiPt: 15,
  },
};

const EVIDENCE = ['public', 'confirmed', 'guess'];

const LIMITS = {
  body: 16 * 1024,      // 1件の上限
  games: 300000,
  bell: 30000,
  count: 100000,        // 各カウンターの上限
  pt: 3000,             // CZ突入時のポイントの上限
  perDay: 60,           // 同じ端末からの1日の上限
};

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
  });

const bad = (msg) => json({ ok: false, error: msg }, 400);

const isInt = (v, max) => Number.isInteger(v) && v >= 0 && v <= max;

/** 受け取った値をひととおり検算する。おかしければ理由を返す */
function validate(r) {
  if (!r || typeof r !== 'object') return '形式が不正です';

  const m = MACHINES[r.machine];
  if (!m) return '未対応の機種です';

  if (!/^r_[a-z0-9]{4,32}$/i.test(r.id || '')) return 'idが不正です';
  if (!/^c_[a-z0-9]{4,40}$/i.test(r.clientId || '')) return 'clientIdが不正です';

  const t = Date.parse(r.playedAt);
  if (!t) return '日時が不正です';
  const diff = Math.abs(Date.now() - t);
  if (diff > 400 * 24 * 3600 * 1000) return '日時が離れすぎています';

  if (!isInt(r.games, LIMITS.games)) return 'ゲーム数が不正です';
  if (!isInt(r.bell, LIMITS.bell)) return '下段ベルが不正です';
  if (r.games > 0 && r.bell > r.games) return '下段ベルがゲーム数を超えています';

  if (!r.chars || typeof r.chars !== 'object') return 'カウントがありません';
  let czTotal = 0;
  for (const id of m.chars) {
    const c = r.chars[id];
    if (!c || typeof c !== 'object') return `${id} のカウントがありません`;
    for (const k of ['no', 'glow', 'hi', 'cz']) {
      if (!isInt(c[k], LIMITS.count)) return `${id}.${k} が不正です`;
    }
    // 突入は、出現した回数より多くはならない
    if (c.cz > c.no + c.glow + c.hi) return `${id} の突入回数が出現回数を超えています`;
    czTotal += c.cz;
  }

  if (!Array.isArray(r.czPointsBy)) return 'CZ突入時のポイントがありません';
  if (r.czPointsBy.length !== czTotal) return '突入回数とポイントの件数が一致しません';
  for (const p of r.czPointsBy) {
    if (!p || !m.chars.includes(p.c)) return 'ポイントのキャラ指定が不正です';
    if (!isInt(p.pt, LIMITS.pt)) return 'ポイントの値が不正です';
  }

  if (r.setting != null && !(Number.isInteger(r.setting) && r.setting >= 1 && r.setting <= 6)) {
    return '設定の値が不正です';
  }
  if (r.evidence != null && !EVIDENCE.includes(r.evidence)) return '根拠の値が不正です';
  if (r.appVersion != null && String(r.appVersion).length > 24) return 'バージョン表記が長すぎます';

  return null;
}

/** 集計に使う2つの値をサーバー側で計算する（申告された値は信用しない） */
function derive(r) {
  const m = MACHINES[r.machine];
  let no = 0, glow = 0;
  for (const id of m.avgChars) {
    no += r.chars[id].no;
    glow += r.chars[id].glow;
  }
  const appear = no + glow;
  const pts = r.czPointsBy.filter((p) => m.avgChars.includes(p.c)).map((p) => p.pt);
  return {
    glowRate: appear ? +(glow / appear * 100).toFixed(2) : null,
    avgPt: pts.length ? +(pts.reduce((a, b) => a + b, 0) / pts.length).toFixed(2) : null,
  };
}

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  const len = Number(request.headers.get('content-length') || 0);
  if (len > LIMITS.body) return bad('データが大きすぎます');

  let r;
  try {
    r = await request.json();
  } catch (e) {
    return bad('JSONとして読めません');
  }

  const err = validate(r);
  if (err) return bad(err);

  const db = env.DB;

  // 同じ端末からの投稿が多すぎないか
  const since = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  const cnt = await db.prepare(
    'SELECT COUNT(*) AS n FROM records WHERE client_id = ? AND received_at > ?'
  ).bind(r.clientId, since).first();
  if (cnt && cnt.n >= LIMITS.perDay) {
    return json({ ok: false, error: '1日の送信上限に達しました' }, 429);
  }

  const d = derive(r);
  const now = new Date().toISOString();

  // ログインしている人の記録として結び付ける。端末IDだけだと
  // 機種変更やブラウザの違いで別人になり、あとから読み出せない
  const user = await currentUser(request, db);

  const ins = await db.prepare(
    `INSERT OR IGNORE INTO records
       (id, client_id, machine, played_at, received_at, games, bell,
        setting, evidence, avg_pt, glow_rate, payload, app_version,
        user_id, memo, wins)
     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
  ).bind(
    r.id, r.clientId, r.machine, new Date(r.playedAt).toISOString(), now,
    r.games, r.bell,
    r.setting ?? null, r.evidence ?? null,
    d.avgPt, d.glowRate,
    JSON.stringify(r.chars), r.appVersion ?? null,
    user ? user.id : null,
    // メモは読み出しのために預かるだけ。集計には一切使わない
    typeof r.memo === 'string' ? r.memo.slice(0, 2000) : null,
    Array.isArray(r.wins) ? JSON.stringify(r.wins) : null
  ).run();

  const isNew = ins.meta && ins.meta.changes > 0;

  if (isNew && r.czPointsBy.length) {
    const stmt = db.prepare('INSERT INTO cz_points (record_id, machine, chara, pt) VALUES (?,?,?,?)');
    await db.batch(r.czPointsBy.map((p) => stmt.bind(r.id, r.machine, p.c, p.pt)));
  }

  // 新しく入った分だけ数え上げる。全件を数え直さない
  if (isNew) {
    await bumpStats(db, {
      machine: r.machine,
      clientId: r.clientId,
      games: r.games,
      // 分布に使うのは無名・生駒の突入だけ（銅藍の周期は混ぜない）
      czRows: r.czPointsBy.filter((p) => p.c === 'red' || p.c === 'green').length,
    });
  }

  // 貯めてある集計を返す。中央値は少し前のもので構わない
  // （「みんなの平均」の見せ方に、1件ぶんの差は効いてこない）
  const s = await freshStats(db, r.machine);

  return json({
    ok: true,
    duplicate: !isNew,
    stats: {
      n: s.records,
      avgPt: { you: d.avgPt, median: s.avgPtMedian },
      glowRate: { you: d.glowRate, median: s.glowRateMedian },
    },
  });
}

export function onRequest() {
  return new Response('Method Not Allowed', { status: 405, headers: { allow: 'POST' } });
}
