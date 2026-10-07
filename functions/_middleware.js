/**
 * www.minnanoslot.com で来たリクエストを、minnanoslot.com の同じ場所へ 301 で転送する。
 *
 * www 付きでもサイト全体がそのまま表示されていて、Google が www 版のトップを
 * 別のページとして登録していた（2026-10-07 に Search Console で確認。同じ中身が2つある状態）。
 *
 * このファイルを置くと、画像や CSS も含めた全リクエストが Functions を通る（無料枠は1日10万回）。
 * 枠を使い切っても、既定の「fail open」で静的なページはそのまま配信される。
 */
export async function onRequest(context) {
  const url = new URL(context.request.url);
  if (url.hostname === 'www.minnanoslot.com') {
    url.hostname = 'minnanoslot.com';
    url.protocol = 'https:';
    return Response.redirect(url.toString(), 301);
  }
  return context.next();
}
