/**
 * 変更を保存して、公開する（すぐ／予約）。
 *
 * body: {
 *   mode: 'now' | 'schedule',
 *   date: 'YYYY-MM-DD'（予約のとき）, slug: 記事の名前（予約用ブランチの名前に使う）,
 *   from: 読み込んだ予約用ブランチ（予約中の記事を直したとき）| null,
 *   files: [{ path, text | null, sha }], message: コミットの説明,
 *   draftId: 公開したら消す下書き | null,
 * }
 *
 * すぐ公開: main にコミットする。main に column/ などの変更が入ると、
 *   GitHub Actions（column-publish.yml）が本番へデプロイする。
 * 予約: scheduled/<日付>-<slug> ブランチにコミットする。
 *   その日の 08:47 に column-scheduled.yml が main へ取り込んでデプロイする。
 */
import { json } from '../_auth.js';
import {
  readFiles, refSha, commitFiles, createBranch, deleteBranch, mergeBranch,
  mainBranch, SCHEDULE_PREFIX, GhError,
} from './_github.js';
import { checkFiles, todayJst, SLUG_RE } from './_guard.js';

export async function onRequestPost({ request, env, data }) {
  let b;
  try { b = await request.json(); } catch (e) { return json({ ok: false, error: '形式が不正です' }, 400); }
  const main = mainBranch(env);
  const { mode, date, slug, from, files, draftId } = b || {};
  const message = String((b && b.message) || '管理画面から更新').slice(0, 200) + `\n\n管理画面から（${data.admin.email}）`;

  if (!SLUG_RE.test(String(slug || ''))) return json({ ok: false, error: '記事の名前が不正です' }, 400);
  if (from != null && !(typeof from === 'string' && from.startsWith(SCHEDULE_PREFIX))) {
    return json({ ok: false, error: '予約の指定が不正です' }, 400);
  }
  const base = from || main;
  const current = await readFiles(env, base, (files || []).map((f) => f && f.path).filter(Boolean));
  checkFiles(files, current);

  let result;
  if (mode === 'now') {
    if (from) {
      await commitFiles(env, from, files, message);
      await mergeBranch(env, main, from, `予約をすぐ公開: ${from}`);
      await deleteBranch(env, from);
    } else {
      await commitFiles(env, main, files, message);
    }
    result = { published: true };
  } else if (mode === 'schedule') {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(date || '')) || isNaN(Date.parse(date))) {
      return json({ ok: false, error: '日付が不正です' }, 400);
    }
    if (date <= todayJst()) return json({ ok: false, error: '予約は明日以降の日付にしてください' }, 400);
    const target = `${SCHEDULE_PREFIX}${date}-${slug}`;
    if (from) {
      const r = await commitFiles(env, from, files, message);
      if (from !== target) {
        await createBranch(env, target, r.sha);
        await deleteBranch(env, from);
      }
    } else {
      if (await refSha(env, target)) {
        throw new GhError(`${date} の「${slug}」はすでに予約があります。予約の一覧から開いて直してください`, 409);
      }
      await createBranch(env, target, await refSha(env, main));
      try {
        await commitFiles(env, target, files, message);
      } catch (e) {
        await deleteBranch(env, target).catch(() => {});
        throw e;
      }
    }
    result = { scheduled: target };
  } else {
    return json({ ok: false, error: '公開のしかたが不正です' }, 400);
  }

  if (draftId) {
    await env.DB.prepare(`DELETE FROM column_drafts WHERE id = ?`).bind(String(draftId)).run().catch(() => {});
  }
  return json({ ok: true, ...result });
}
