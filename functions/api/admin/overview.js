/** 管理画面のはじめの画面：公開中の記事・予約中の公開・下書きの一覧 */
import { json } from '../_auth.js';
import { readFiles, listBranches, mainBranch, SCHEDULE_PREFIX } from './_github.js';

const ROW = /<a href="\/column\/([\w-]+)"><span class="d">([^<]*)<\/span><span class="n disp">([^<]*)<\/span><span class="s">([^<]*)<\/span><\/a>/g;

export async function onRequestGet({ env, data }) {
  const main = mainBranch(env);
  const [files, branches, drafts] = await Promise.all([
    readFiles(env, main, ['column/index.html']),
    listBranches(env, SCHEDULE_PREFIX),
    env.DB.prepare(
      `SELECT id, slug, title, origin, updated_at FROM column_drafts ORDER BY updated_at DESC`
    ).all().then((r) => r.results || []).catch(() => null),
  ]);
  const idx = files['column/index.html'];
  const articles = idx ? [...idx.text.matchAll(ROW)].map((m) => ({ slug: m[1], date: m[2], title: m[3], short: m[4] })) : [];
  const scheduled = branches.map((b) => {
    const m = b.name.slice(SCHEDULE_PREFIX.length).match(/^(\d{4}-\d{2}-\d{2})-?(.*)$/);
    return { branch: b.name, date: m ? m[1] : '', slug: m ? m[2] : '' };
  }).sort((a, b) => a.date.localeCompare(b.date));
  return json({
    ok: true, email: data.admin.email, main, articles, scheduled,
    drafts, draftsReady: drafts !== null,
  });
}
