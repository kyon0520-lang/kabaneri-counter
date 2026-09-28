-- COLUMN 管理画面（/admin）の下書き置き場（Cloudflare D1）
--
--   npx wrangler d1 execute minnanoslot --remote --file=src/schema-admin.sql
--
-- リポジトリは誰でも見られるので、書きかけの記事と、非公開に戻した記事はここに置く。
-- 公開すると行は消える（公開された中身は GitHub の column/ にある）。

CREATE TABLE IF NOT EXISTS column_drafts (
  id          TEXT PRIMARY KEY,
  slug        TEXT NOT NULL DEFAULT '',   -- URL の名前（/column/<slug>）
  title       TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',   -- 検索結果に出る説明文（meta description）
  short       TEXT NOT NULL DEFAULT '',   -- 一覧・ほかのCOLUMN・トップに出るひとこと紹介
  body        TEXT NOT NULL DEFAULT '',   -- 本文の HTML
  cta         TEXT NOT NULL DEFAULT '',   -- 記事の下のツール案内の HTML
  origin      TEXT NOT NULL DEFAULT 'new',-- 'new'（新しく書いた） | 'unpublished'（非公開に戻した）
  orig_date   TEXT NOT NULL DEFAULT '',   -- 非公開に戻した記事の、もとの公開日
  after_slug  TEXT NOT NULL DEFAULT '',   -- 一覧でこの記事の後ろに並べる（空なら末尾）
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL
);
