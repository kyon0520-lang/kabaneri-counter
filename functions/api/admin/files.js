/** ファイルをまとめて読む。?ref=main か予約用ブランチ、&paths=a,b,c */
import { json } from '../_auth.js';
import { readFiles, refSha, mainBranch, SCHEDULE_PREFIX } from './_github.js';

export async function onRequestGet({ request, env }) {
  const url = new URL(request.url);
  const main = mainBranch(env);
  const ref = url.searchParams.get('ref') || main;
  if (ref !== main && !(ref.startsWith(SCHEDULE_PREFIX) && /^[\w\-/.]+$/.test(ref))) {
    return json({ ok: false, error: '読めないブランチです' }, 400);
  }
  const paths = (url.searchParams.get('paths') || '').split(',').filter(Boolean);
  if (!paths.length || paths.length > 200 || paths.some((p) => !/^[\w\-/.]+$/.test(p) || p.includes('..'))) {
    return json({ ok: false, error: 'ファイルの指定が不正です' }, 400);
  }
  // 同じ版から読むために、先にコミットを決めてから読む
  const head = await refSha(env, ref);
  if (!head) return json({ ok: false, error: `${ref} が見つかりません（取り消されたか、公開済みかもしれません）` }, 404);
  const files = await readFiles(env, head, paths);
  return json({ ok: true, ref, head, files });
}
