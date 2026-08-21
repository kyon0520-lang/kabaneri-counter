-- 集計を1行に貯めておくための表。
--
--   npx wrangler d1 execute minnanoslot --remote --file=src/schema-stats.sql
--
-- なぜ要るか: これまで送信1件ごとに records を全件走査していた。
-- D1は「走査した行数」を読み取りとして数えるので、貯まるほど1送信が重くなり、
-- 2〜3万件で1日数十件しか受け付けられなくなる（容量の上限より先に頭打ち）。
-- 件数と合計は挿入時に足し込み、重い集計はときどきだけ作り直して、
-- 1送信あたりの読み取りを件数によらず一定にする。

CREATE TABLE IF NOT EXISTS machine_stats (
  machine          TEXT PRIMARY KEY,
  records          INTEGER NOT NULL DEFAULT 0,
  clients          INTEGER NOT NULL DEFAULT 0,
  games            INTEGER NOT NULL DEFAULT 0,
  cz_rows          INTEGER NOT NULL DEFAULT 0,   -- 無名・生駒の突入回数
  -- ここから下は重い集計の結果。agg_records 件の時点のもの
  avg_pt_median    REAL,
  glow_rate_median REAL,
  dist_json        TEXT,
  setting_json     TEXT,
  agg_at           TEXT,
  agg_records      INTEGER NOT NULL DEFAULT 0
);

-- 参加端末数を数えるため。COUNT(DISTINCT) は全件走査になるので、
-- 初めて見た端末かどうかを主キーの衝突で判定して数え上げる
CREATE TABLE IF NOT EXISTS seen_clients (
  machine   TEXT NOT NULL,
  client_id TEXT NOT NULL,
  PRIMARY KEY (machine, client_id)
);

-- 中央値の取り直しを、並べ替えなしで済ませるための索引
CREATE INDEX IF NOT EXISTS idx_records_avgpt ON records(machine, avg_pt);
CREATE INDEX IF NOT EXISTS idx_records_glow  ON records(machine, glow_rate);

-- いまある行から初期値を作る（1回だけ。以降は挿入時に足し込む）
INSERT OR REPLACE INTO machine_stats (machine, records, clients, games, cz_rows, agg_records)
SELECT r.machine,
       COUNT(*),
       (SELECT COUNT(DISTINCT client_id) FROM records x WHERE x.machine = r.machine),
       COALESCE(SUM(r.games), 0),
       (SELECT COUNT(*) FROM cz_points c WHERE c.machine = r.machine AND c.chara IN ('red','green')),
       0
  FROM records r GROUP BY r.machine;

INSERT OR IGNORE INTO seen_clients (machine, client_id)
SELECT DISTINCT machine, client_id FROM records;
