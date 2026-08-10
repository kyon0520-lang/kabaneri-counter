-- みんなのスロット 実戦データの保管先（Cloudflare D1）
--
--   npx wrangler d1 execute minnanoslot --remote --file=src/schema.sql
--
-- 機種ごとに違う項目は payload（JSON）に入れる。列を機種に合わせると
-- 2機種目で作り直しになるため。集計に使う値だけ列として持つ。

CREATE TABLE IF NOT EXISTS records (
  id           TEXT PRIMARY KEY,   -- 端末が採番。再送しても重複しない
  client_id    TEXT NOT NULL,      -- 端末ごとの匿名ID
  machine      TEXT NOT NULL,      -- 'kabaneri-unato'
  played_at    TEXT NOT NULL,      -- 実戦日時（端末の時計）
  received_at  TEXT NOT NULL,      -- サーバーが受けた時刻
  games        INTEGER NOT NULL,
  bell         INTEGER NOT NULL,
  setting      INTEGER,            -- 1〜6。未申告は NULL
  evidence     TEXT,               -- 'public' | 'confirmed' | 'guess' | NULL
  -- 集計でそのまま使う値。クライアントの申告ではなくサーバーで計算して入れる
  avg_pt       REAL,               -- CZ 1回あたりの平均ポイント（無名＋生駒）
  glow_rate    REAL,               -- 発光率（％。無名＋生駒、高確は含まない）
  payload      TEXT NOT NULL,      -- キャラ別の回数（JSON）
  app_version  TEXT
);

CREATE INDEX IF NOT EXISTS idx_records_machine ON records(machine, received_at);
CREATE INDEX IF NOT EXISTS idx_records_client  ON records(client_id, received_at);

-- 規定ptの分布を出すために、CZ突入1回を1行に展開しておく
CREATE TABLE IF NOT EXISTS cz_points (
  record_id TEXT NOT NULL,
  machine   TEXT NOT NULL,
  chara     TEXT NOT NULL,        -- 'red' | 'green' | 'blue'
  pt        INTEGER NOT NULL,
  FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cz_machine ON cz_points(machine, chara);
