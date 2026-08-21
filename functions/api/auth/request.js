/**
 * ログイン用のリンクをメールで送る。
 *
 * 「そのアドレスは登録されていません」とは返さない。返すと、
 * どのアドレスが登録済みかを外から調べられてしまうため、
 * 登録済みでも未登録でも同じ応答にする（未登録なら初回登録を兼ねる）。
 */
import {
  json, normalizeEmail, randomToken, LOGIN_TTL_MIN, addMinutes,
} from '../_auth.js';

const SUBJECT = 'みんなのスロット ログイン';

function mailHtml(link) {
  return `<div style="font-family:-apple-system,BlinkMacSystemFont,'Hiragino Sans',sans-serif;line-height:1.9;color:#16283f">
  <p>下のボタンを押すと、みんなのスロットにログインします。</p>
  <p style="margin:24px 0">
    <a href="${link}" style="background:#2f6bd8;color:#fff;text-decoration:none;
       border-radius:10px;padding:14px 22px;font-weight:700;display:inline-block">ログインする</a>
  </p>
  <p style="font-size:13px;color:#667">このリンクは${LOGIN_TTL_MIN}分で使えなくなります。1回だけ使えます。</p>
  <p style="font-size:13px;color:#667">心当たりがない場合は、このメールを捨ててください。押さなければ何も起きません。</p>
</div>`;
}

async function sendMail(env, to, link) {
  const key = env.RESEND_API_KEY;
  const from = env.MAIL_FROM || 'みんなのスロット <login@minnanoslot.com>';
  if (!key) return { sent: false, reason: 'no-key' };

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${key}`,
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      from, to: [to], subject: SUBJECT,
      html: mailHtml(link),
      text: `みんなのスロットにログインします。\n${link}\n\nこのリンクは${LOGIN_TTL_MIN}分で使えなくなります。`,
    }),
  });
  if (!res.ok) {
    return { sent: false, reason: `resend-${res.status}`, detail: await res.text() };
  }
  return { sent: true };
}

export async function onRequestPost({ request, env }) {
  if (!env.DB) return json({ ok: false, error: 'サーバー側の設定が未完了です' }, 503);

  let body;
  try { body = await request.json(); } catch (e) { return json({ ok: false, error: '形式が不正です' }, 400); }

  const email = normalizeEmail(body && body.email);
  if (!email) return json({ ok: false, error: 'メールアドレスの形式が正しくありません' }, 400);

  const db = env.DB;

  // 同じアドレスへ立て続けに送らない。踏み台にされるのを防ぐ
  const recent = await db.prepare(
    `SELECT COUNT(*) AS n FROM login_tokens WHERE email = ? AND created_at > ?`
  ).bind(email, new Date(Date.now() - 10 * 60 * 1000).toISOString()).first();
  if (recent && recent.n >= 3) {
    return json({ ok: false, error: '送信が続いています。少し待ってからお試しください' }, 429);
  }

  const token = randomToken(32);
  await db.prepare(
    `INSERT INTO login_tokens (token, email, created_at, expires_at) VALUES (?,?,?,?)`
  ).bind(token, email, new Date().toISOString(), addMinutes(LOGIN_TTL_MIN)).run();

  const origin = new URL(request.url).origin;
  const link = `${origin}/api/auth/verify?t=${token}`;

  const r = await sendMail(env, email, link);

  // メール基盤を用意する前でも通しで試せるようにする。
  // DEV_LOGIN を明示的に立てたときだけ、リンクをそのまま返す。
  // 立てたままだと誰でも他人になりすませるので、本番では絶対に設定しない
  if (!r.sent && env.DEV_LOGIN === '1') {
    return json({ ok: true, sent: false, devLink: link, note: 'DEV_LOGIN が有効です' });
  }
  if (!r.sent) {
    return json({ ok: false, error: 'メールを送れませんでした。時間をおいてお試しください' }, 502);
  }
  return json({ ok: true, sent: true });
}
