/**
 * GitHub とのやりとり。管理画面の保存は、すべてリポジトリへのコミットになる。
 *
 * 使う秘密の設定（Cloudflare Pages の環境変数。リポジトリには絶対に書かない）:
 *   ADMIN_GH_TOKEN … fine-grained token。このリポジトリだけ・Contents の読み書きだけ
 * 試験用の設定（手元の試験でだけ使う。本番では設定しない）:
 *   ADMIN_GH_API   … GitHub の代わりをする試験用サーバーの URL
 *   ADMIN_BRANCH   … main の代わりに使うブランチ
 *
 * 読み込みは GraphQL でまとめて1回にする。Pages Functions は1回の呼び出しで外へ出せる
 * 通信の数に上限（無料プランで50）があり、記事が増えると1ファイル1通信では足りなくなるため。
 */

export const REPO_OWNER = 'kyon0520-lang';
export const REPO_NAME = 'kabaneri-counter';
export const SCHEDULE_PREFIX = 'scheduled/';

export function mainBranch(env) {
  return env.ADMIN_BRANCH || 'main';
}

export class GhError extends Error {
  constructor(message, status = 502) { super(message); this.status = status; }
}

function api(env) {
  return (env.ADMIN_GH_API || 'https://api.github.com').replace(/\/$/, '');
}

async function gh(env, method, path, body) {
  const token = String(env.ADMIN_GH_TOKEN || '').trim();
  if (!token) throw new GhError('サーバー側の設定が未完了です（ADMIN_GH_TOKEN）', 503);
  let res;
  try {
    res = await fetch(api(env) + path, {
      method,
      headers: {
        authorization: `Bearer ${token}`,
        accept: 'application/vnd.github+json',
        'x-github-api-version': '2022-11-28',
        'user-agent': 'minnanoslot-admin',
        ...(body ? { 'content-type': 'application/json' } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (e) {
    throw new GhError('GitHub に接続できませんでした: ' + (e && e.message || e));
  }
  if (res.status === 204) return { status: 204, body: null };
  let out = null;
  try { out = await res.json(); } catch (e) {}
  return { status: res.status, body: out };
}

function fail(what, r) {
  const msg = r.body && r.body.message ? `（${r.body.message}）` : '';
  if (r.status === 401) return new GhError(`GitHub のトークンが使えません。期限切れかもしれません${msg}`, 502);
  if (r.status === 403 || r.status === 404) return new GhError(`${what}ができませんでした。トークンの権限を確認してください${msg}`, 502);
  return new GhError(`${what}ができませんでした（GitHub ${r.status}）${msg}`, 502);
}

/** ブランチの先頭のコミット。無ければ null */
export async function refSha(env, branch) {
  const r = await gh(env, 'GET', `/repos/${REPO_OWNER}/${REPO_NAME}/git/ref/heads/${branch}`);
  if (r.status === 404) return null;
  if (r.status !== 200) throw fail('ブランチの確認', r);
  return r.body.object.sha;
}

/**
 * 複数のファイルをまとめて読む。ref はブランチ名かコミット。
 * 返り値: { [path]: { text, sha } | null }（sha はファイルの版を表す値。保存のときの衝突確認に使う）
 */
export async function readFiles(env, ref, paths) {
  if (!paths.length) return {};
  const esc = (s) => JSON.stringify(s);
  const fields = paths.map((p, i) =>
    `f${i}: object(expression: ${esc(`${ref}:${p}`)}) { ... on Blob { oid text isTruncated } }`
  ).join('\n');
  const query = `query { repository(owner: ${esc(REPO_OWNER)}, name: ${esc(REPO_NAME)}) {\n${fields}\n} }`;
  const r = await gh(env, 'POST', '/graphql', { query });
  if (r.status !== 200 || !r.body || r.body.errors || !r.body.data) {
    const m = r.body && r.body.errors ? r.body.errors.map((e) => e.message).join(' / ') : '';
    throw new GhError(`ファイルを読めませんでした（GitHub ${r.status}）${m}`);
  }
  const repo = r.body.data.repository || {};
  const out = {};
  paths.forEach((p, i) => {
    const o = repo[`f${i}`];
    if (!o) { out[p] = null; return; }
    if (o.isTruncated || o.text == null) throw new GhError(`${p} が大きすぎて読めません`);
    out[p] = { text: o.text, sha: o.oid };
  });
  return out;
}

/** 名前が prefix で始まるブランチの一覧 */
export async function listBranches(env, prefix) {
  const r = await gh(env, 'GET', `/repos/${REPO_OWNER}/${REPO_NAME}/git/matching-refs/heads/${prefix}`);
  if (r.status !== 200) throw fail('ブランチの一覧の取得', r);
  return (r.body || []).map((x) => ({ name: x.ref.replace(/^refs\/heads\//, ''), sha: x.object.sha }));
}

export async function createBranch(env, name, sha) {
  const r = await gh(env, 'POST', `/repos/${REPO_OWNER}/${REPO_NAME}/git/refs`, { ref: `refs/heads/${name}`, sha });
  if (r.status === 422) throw new GhError(`${name} はすでにあります`, 409);
  if (r.status !== 201) throw fail('ブランチの作成', r);
}

export async function deleteBranch(env, name) {
  const r = await gh(env, 'DELETE', `/repos/${REPO_OWNER}/${REPO_NAME}/git/refs/heads/${name}`);
  if (r.status !== 204 && r.status !== 422 && r.status !== 404) throw fail('ブランチの削除', r);
}

/** head を base に取り込む（予約中の変更をすぐ公開するとき） */
export async function mergeBranch(env, base, head, message) {
  const r = await gh(env, 'POST', `/repos/${REPO_OWNER}/${REPO_NAME}/merges`, { base, head, commit_message: message });
  if (r.status === 409) throw new GhError('本番の内容とぶつかって取り込めませんでした。Mac での手直しが必要です', 409);
  if (r.status !== 201 && r.status !== 204) throw fail('取り込み', r);
}

/**
 * 複数のファイルの変更を1つのコミットにしてブランチに積む。
 * files: [{ path, text | null(消す), sha | null(新しいファイル) }]
 *   sha は画面が読み込んだときの版。いまのブランチの版と違えば、ほかで変更されたとみなして止める。
 *   ほかのファイル（毎日のデータ更新など）が変わっているだけなら、そのまま上に積む。
 */
export async function commitFiles(env, branch, files, message) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const head = await refSha(env, branch);
    if (!head) throw new GhError(`${branch} が見つかりません`, 404);

    const now = await readFiles(env, head, files.map((f) => f.path));
    const stale = files.filter((f) => ((now[f.path] && now[f.path].sha) || null) !== (f.sha || null));
    if (stale.length) {
      throw new GhError('ほかの場所で先に変更されたファイルがあります。読み込み直してから、もう一度直してください: '
        + stale.map((f) => f.path).join('、'), 409);
    }
    const changed = files.filter((f) => !(now[f.path] && f.text != null && now[f.path].text === f.text)
      && !(now[f.path] == null && f.text == null));
    if (!changed.length) return { sha: head, unchanged: true };

    const c = await gh(env, 'GET', `/repos/${REPO_OWNER}/${REPO_NAME}/git/commits/${head}`);
    if (c.status !== 200) throw fail('コミットの確認', c);

    const tree = changed.map((f) => (f.text == null
      ? { path: f.path, mode: '100644', type: 'blob', sha: null }
      : { path: f.path, mode: '100644', type: 'blob', content: f.text }));
    const t = await gh(env, 'POST', `/repos/${REPO_OWNER}/${REPO_NAME}/git/trees`, { base_tree: c.body.tree.sha, tree });
    if (t.status !== 201) throw fail('ファイルの書き込み', t);

    const k = await gh(env, 'POST', `/repos/${REPO_OWNER}/${REPO_NAME}/git/commits`, { message, tree: t.body.sha, parents: [head] });
    if (k.status !== 201) throw fail('コミット', k);

    const u = await gh(env, 'PATCH', `/repos/${REPO_OWNER}/${REPO_NAME}/git/refs/heads/${branch}`, { sha: k.body.sha, force: false });
    if (u.status === 200) return { sha: k.body.sha };
    if (u.status !== 422) throw fail('ブランチの更新', u);
    // 読んでから書くまでの間に、毎日のデータ更新などが先に積まれた。取り直してやり直す
  }
  throw new GhError('混み合っていて保存できませんでした。少し待ってからもう一度お試しください', 503);
}
