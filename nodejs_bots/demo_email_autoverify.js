// =============================================================================
// ポートフォリオ：【技術デモ】IMAPメール自動認証システム (Node.js版)
// =============================================================================
//
// 目的：
// このスクリプトは、「Node.js」の「imap-simple（メールサーバー接続）」を使い、
// メールの「件名」や「本文（正規表現）」を解析し、
// 「puppeteer（ブラウザ自動化）」で認証URLをクリックする
// 「技術（アーキテクチャ）」を実証するためのデモです。
//
// =============================================================================

require("dotenv").config(); // .env ファイルから機密情報を読み込む
const imaps = require('imap-simple');
const { simpleParser } = require('mailparser');
const puppeteer = require('puppeteer'); // 抜き出したURLにアクセスするため

// .env ファイルからIMAP（メールサーバー）の接続情報を読み込む
const config = {
  imap: {
    user: process.env.IMAP_USER,       // (例: 'your-email@gmail.com')
    password: process.env.IMAP_PASSWORD, // (例: 'your-app-password')
    host: process.env.IMAP_HOST || 'imap.gmail.com', // デフォルトはGmail
    port: 993,
    tls: true,
    tlsOptions: { rejectUnauthorized: false }
  }
};

// 検索対象のメール件名（デモ用）
const TARGET_SUBJECT = '【デモ】システムからの認証メール';

/**
 * メールサーバーに接続し、未読メールを検索・解析・URLクリックを自動で行う関数
 */
async function checkMailAndClickUrl() {
  // 接続情報が .env に設定されていない場合はスキップ
  if (!config.imap.user || !config.imap.password) {
      console.log('[デモ] IMAP_USER または IMAP_PASSWORD が .env ファイルに設定されていません。デモをスキップします。');
      return;
  }

  let connection;

  try {
    console.log(`🚀 [技術デモ] ${config.imap.user} のINBOXに接続中...`);
    connection = await imaps.connect(config);
    await connection.openBox('INBOX');

    // 検索条件：「未読」かつ「件名」が一致
    const searchCriteria = [
      'UNSEEN',
      ['HEADER', 'SUBJECT', TARGET_SUBJECT]
    ];

    const fetchOptions = {
      bodies: [''],
      markSeen: true // 処理したら「既読」にする
    };

    const results = await connection.search(searchCriteria, fetchOptions);

    if (results.length === 0) {
      console.log(`▶ [デモ] 「${TARGET_SUBJECT}」の未読メールなし。`);
      await connection.end();
      return;
    }

    console.log(`✅ [デモ] ${results.length} 件の認証メールを発見。処理を開始します...`);

    // 1. IMAPでメール本文を解析
    for (const res of results) {
      const raw = res.parts[0].body;
      const parsed = await simpleParser(raw);
      const body = parsed.text || parsed.html || '';
      
      // 2. 正規表現でURLを抽出 (https?:// から始まり、空白や引用符以外が続く文字列)
      const match = body.match(/https?:\/\/[^\s"'<>]+/);

      if (match) {
        const url = match[0];
        console.log('   > [デモ] 認証URLを発見:', url);

        // 3. Puppeteer（ブラウザ）でURLにアクセス
        const browser = await puppeteer.launch({ headless: true });
        const page = await browser.newPage();
        await page.goto(url, { waitUntil: 'networkidle2' });

        console.log('   > ✅ [デモ] 認証URLにアクセス完了。タブを閉じます。');
        await browser.close();
      } else {
        console.log('   > ⚠ [デモ] メール本文中にURLが見つかりませんでした。');
      }
    }

    await connection.end();
  } catch (error) {
    console.error('❌ [デモ] エラー:', error.message);
    if (connection) {
      try {
        await connection.end();
      } catch (e) {
        console.error('❌ [デモ] 接続終了時エラー:', e.message);
      }
    }
  }
}

// -------------------- メイン処理 --------------------

// 起動直後に1回実行
checkMailAndClickUrl();

// 5分ごとに実行（300,000ms）
setInterval(checkMailAndClickUrl, 5 * 60 * 1000);