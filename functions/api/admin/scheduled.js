/** 予約中の公開の操作。body: { action: 'cancel' | 'publish', branch } */
import { json } from '../_auth.js';
import { refSha, deleteBranch, mergeBranch, mainBranch, SCHEDULE_PREFIX } from './_github.js';

export async function onRequestPost({ request, env }) {
  let b;
  try { b = await request.json(); } catch (e) { return json({ ok: false, error: '形式が不正です' }, 400); }
  const branch = String((b && b.branch) || '');
  if (!branch.startsWith(SCHEDULE_PREFIX) || !/^[\w\-/.]+$/.test(branch)) {
    return json({ ok: false, error: '予約の指定が不正です' }, 400);
  }
  if (!(await refSha(env, branch))) {
    return json({ ok: false, error: 'その予約は見つかりません（取り消されたか、公開済みかもしれません）' }, 404);
  }
  if (b.action === 'cancel') {
    await deleteBranch(env, branch);
    return json({ ok: true, canceled: branch });
  }
  if (b.action === 'publish') {
    await mergeBranch(env, mainBranch(env), branch, `予約をすぐ公開: ${branch}`);
    await deleteBranch(env, branch);
    return json({ ok: true, published: branch });
  }
  return json({ ok: false, error: '操作が不正です' }, 400);
}
