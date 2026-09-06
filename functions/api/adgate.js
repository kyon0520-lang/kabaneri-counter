/**
 * リワード広告ゲートの解除状態。GET /api/adgate, POST /api/adgate
 *
 * localStorage が使えない環境（プライベートモード等）だけが呼ぶフォールバック。
 * 通常の利用者（localStorageが使える）はここに一切アクセスしない
 * （圏外でも起動できることを売りにしているので、ここを主経路にはしない）。
 *
 * 解除は「日をまたいだら再度必要」という、クライアント側(todayStr())と同じ
 * カレンダー日基準にする。JSTの日付をキーに含めて保存し、TTLは
 * 掃除のためだけに使う（キーが日ごとに変わるので、TTLの長さ自体は判定に効かない）。
 * IPアドレスはそのまま保存せず、日付・ソルトと合わせてハッシュ化する
 * （privacy.htmlの「接続元の情報から作る一時的な識別子」に対応）。
 */
import { json } from './_auth.js';

const SALT = 'kabaneri-adgate-2026-09';
const TTL_SEC = 24 * 3600;

function todayJST(){
  const now = new Date(Date.now() + 9 * 3600 * 1000);
  const y = now.getUTCFullYear();
  const m = String(now.getUTCMonth() + 1).padStart(2, '0');
  const d = String(now.getUTCDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}

async function keyFor(request){
  const ip = request.headers.get('cf-connecting-ip') || '0.0.0.0';
  const data = new TextEncoder().encode(`${ip}:${todayJST()}:${SALT}`);
  const digest = await crypto.subtle.digest('SHA-256', data);
  const hex = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
  return `adgate:${hex}`;
}

export async function onRequestGet({ request, env }) {
  // 設定漏れでカウンターを止めない。解除済み扱いにして通す
  if (!env.ADGATE_KV) return json({ ok: true, unlocked: true });
  const key = await keyFor(request);
  const v = await env.ADGATE_KV.get(key);
  return json({ ok: true, unlocked: !!v });
}

export async function onRequestPost({ request, env }) {
  if (!env.ADGATE_KV) return json({ ok: true });
  const key = await keyFor(request);
  await env.ADGATE_KV.put(key, '1', { expirationTtl: TTL_SEC });
  return json({ ok: true });
}

export function onRequest() {
  return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET, POST' } });
}
