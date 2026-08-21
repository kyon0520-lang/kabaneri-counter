-- 保存の会員制化で足すテーブル。
--
--   npx wrangler d1 execute minnanoslot --remote --file=src/schema-auth.sql
--
-- 方針: 数えるのは登録不要。保存だけ登録制。
-- パスワードは持たない。メールに届くリンクを押すことだけで本人とみなす。
-- 「忘れた」の事故が構造的に起きないため。

CREATE TABLE IF NOT EXISTS users (
  id         TEXT PRIMARY KEY,   -- u_xxxxx
  email      TEXT NOT NULL UNIQUE COLLATE NOCASE,
  created_at TEXT NOT NULL,
  -- みんなの集計への提供に同意した日時。保存と同時に得るので実質必須だが、
  -- いつの版の同意文で得たかを残せるように列で持つ
  consent_at TEXT,
  consent_version TEXT
);

-- ログイン用の使い捨てリンク。短命で、1回使ったら無効にする
CREATE TABLE IF NOT EXISTS login_tokens (
  token      TEXT PRIMARY KEY,
  email      TEXT NOT NULL COLLATE NOCASE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_login_exp ON login_tokens(expires_at);

-- ログイン後の合言葉。Cookie に入れる本体はこれ
CREATE TABLE IF NOT EXISTS sessions (
  token      TEXT PRIMARY KEY,
  user_id    TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_exp  ON sessions(expires_at);

-- 記録を人に結び付ける。端末IDだけだと機種変更のたびに別人になる。
-- 既存の行は user_id が NULL のまま（登録前に届いた分）
ALTER TABLE records ADD COLUMN user_id TEXT;
CREATE INDEX IF NOT EXISTS idx_records_user ON records(user_id, played_at);

-- 読み出しのために、端末が持っていた項目もサーバーに預かる。
-- 集計には使わない。メモは特に、保管はするが提供には含めない
ALTER TABLE records ADD COLUMN memo TEXT;
ALTER TABLE records ADD COLUMN wins TEXT;   -- 当選履歴（JSON）
