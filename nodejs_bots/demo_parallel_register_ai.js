// =============================================================================
// ポートフォリオ：【技術デモ】並列Web登録システム (Node.js版)
// =============================================================================
//
// 目的：
// このスクリプトは、「Node.js」と「Puppeteer（ブラウザ自動化）」を使い、
// 「並列処理（Promise.all）」で、
// 「reCAPTCHA（AI連携）」のあるフォームに自動入力する
// 「技術（アーキテクチャ）」を実証するためのデモです。
//
// =============================================================================

require("dotenv").config(); // APIキーなどを .env ファイルから読み込むため
const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
const fs = require("fs");
const axios = require("axios"); // 2Captcha連携（AI連携）に使用

puppeteer.use(StealthPlugin()); // Bot検知回避

// ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
// ★ 安全化 1：固有名詞を「ダミーのデモサイト」に変更 ★
// ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
const TARGET_URL = "https://www.google.com/recaptcha/api2/demo"; // Googleの公式デモサイト
const CAPTCHA_API_KEY = process.env.CAPTCHA_API_KEY; // 2CaptchaのAPIキー (.envファイルから読み込む)
const CONCURRENCY = 3; // 並列実行数
const OUTPUT_FILE = "demo_output.csv";
const EMAIL_LIST_FILE = "demo_create_list.csv";

// -------------------- ユーティリティ --------------------

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// AI（2Captcha）連携ロジック
const solveRecaptcha = async (page, sitekey, url) => {
  if (!CAPTCHA_API_KEY) {
    console.warn("   > [デモ] 2Captcha APIキー未設定のため、reCAPTCHA解析をスキップします。");
    // キーが無い場合は、ダミーのトークンを返す（デモ用）
    const dummyToken = "DUMMY_TOKEN_FOR_PORTFOLIO_" + Date.now();
    await page.evaluate(token => {
      let textarea = document.querySelector("textarea[name='g-recaptcha-response']");
      if (!textarea) {
        textarea = document.createElement("textarea");
        textarea.name = "g-recaptcha-response";
        textarea.style.display = "none";
        document.body.appendChild(textarea);
      }
      textarea.value = token;
    }, dummyToken);
    return true;
  }
  
  // 2Captcha APIに「発注」
  const res = await axios.get("http://2captcha.com/in.php", {
    params: {
      key: CAPTCHA_API_KEY,
      method: "userrecaptcha",
      googlekey: sitekey,
      pageurl: url,
      json: 1,
    },
  });

  if (res.data.status !== 1) throw new Error("2Captcha送信失敗: " + res.data.request);
  const requestId = res.data.request;

  for (let i = 0; i < 24; i++) { // 24回 (約2分) 待機
    await sleep(5000); // 5秒待機
    const result = await axios.get("http://2captcha.com/res.php", {
      params: {
        key: CAPTCHA_API_KEY,
        action: "get",
        id: requestId,
        json: 1,
      },
    });
    if (result.data.status === 1) {
      // 成功
      const token = result.data.request;
      // ページ内の解答欄（g-recaptcha-response）にトークンを書き込む
      await page.evaluate(token => {
        let textarea = document.querySelector("textarea[name='g-recaptcha-response']");
        if (!textarea) {
          textarea = document.createElement("textarea");
          textarea.name = "g-recaptcha-response";
          textarea.style.display = "none";
          document.body.appendChild(textarea);
        }
        textarea.value = token;
      }, token);
      return true; // 成功
    }
    if (result.data.request !== "CAPCHA_NOT_READY") {
      // AIが「まだ解けてない」以外のエラーを返した
      throw new Error("2Captchaエラー: " + result.data.request);
    }
    // (まだ解けていない場合は、ループを続行)
  }
  throw new Error("2Captchaタイムアウト"); // 2分待ってもAIが解けなかった
};

// ★ 安全化 2：「faker.js」を削除し、ダミーデータに変更
const getDemoData = () => {
    return {
        name: "Demo User",
        birth: { year: "1990", month: "01", day: "01" }
    };
};

const appendToCsv = (row) => {
  const header = '"氏名","メールアドレス","生年月日"\n';
  const writeHeader = !fs.existsSync(OUTPUT_FILE);
  const line = row + "\n";
  if (writeHeader) fs.writeFileSync(OUTPUT_FILE, header);
  fs.appendFileSync(OUTPUT_FILE, line);
};

const readEmailList = () => {
  if (!fs.existsSync(EMAIL_LIST_FILE)) {
      console.log(`   > [デモ] ${EMAIL_LIST_FILE} が無い為、ダミーのEmailリストを生成します。`);
      return ["demo1@example.com", "demo2@example.com", "demo3@example.com"];
  }
  const raw = fs.readFileSync(EMAIL_LIST_FILE, "utf-8");
  return raw.trim().split("\n").map(line => line.trim()).filter(line => line);
};

// -------------------- アカウント作成（デモ） --------------------

// ★ 安全化 3：関数名を「技術デモ」らしく変更
const executeRegistrationDemo = async (browser, email) => {
  const data = getDemoData(); // ダミーデータを取得
  const page = await browser.newPage();

  try {
    console.log(`🚀 [技術デモ] 開始: ${email}`);
    await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)");

    await page.goto(TARGET_URL, { waitUntil: "domcontentloaded", timeout: 30000 });
    
    // ★ 安全化 4：Googleデモサイトのフォームに入力する
    await page.waitForSelector('#recaptcha-demo-form [type="text"]');
    await page.type('#recaptcha-demo-form [type="text"]', data.name);
    await page.type('#recaptcha-demo-form [type="email"]', email);
    
    // AI連携の実行
    const sitekey = await page.$eval('div.g-recaptcha', el => el.getAttribute('data-sitekey'));
    if (!sitekey) throw new Error("reCAPTCHA sitekey 取得失敗");

    const solved = await solveRecaptcha(page, sitekey, TARGET_URL);
    if (!solved) throw new Error("reCAPTCHA 解決失敗");

    // ★ 安全化 5：Googleデモサイトのフォームを送信する
    await Promise.all([
      page.waitForNavigation({ waitUntil: "networkidle2", timeout: 30000 }),
      page.evaluate(() => document.querySelector("#recaptcha-demo-form").submit()),
    ]);

    const currentUrl = page.url();
    // ★ 安全化 6：Googleデモサイトの「成功ページ」を検証する
    if (!currentUrl.includes("recaptcha-demo-results")) {
      throw new Error("デモ登録失敗：URLが遷移していません -> " + currentUrl);
    }
    
    // 成功したらCSVに書き出す
    appendToCsv(`"${data.name}","${email}","${data.birth.year}-${data.birth.month}-${data.birth.day}"`);
    console.log(`✅ [技術デモ] 成功 (${email}) 🍒🍥`);
    return true;

  } catch (err) {
    console.error(`❌ [技術デモ] エラー (${email}): ${err.message}`);
    await page.screenshot({ path: `error_demo_${email.replace(/[^a-zA-Z0-9]/g, "_")}.png` });
    return false; // リトライロジックは簡略化
  
  } finally {
    await page.close();
  }
};

// -------------------- メイン処理 --------------------

(async () => {
  const emails = readEmailList();
  if (emails.length === 0) {
    console.log("📭 処理対象のメールアドレスがありません");
    return;
  }

  const browser = await puppeteer.launch({
    headless: true, // デフォルトを headless=true に変更（サーバ実行用）
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-blink-features=AutomationControlled", // Bot検知回避
    ],
  });

  let index = 0;
  
  // 並列処理（バッチ実行）
  while (index < emails.length) {
    const batch = emails.slice(index, index + CONCURRENCY);
    console.log(`🧵 バッチ開始: ${index + 1}〜${index + batch.length} を並列実行`);

    const results = await Promise.allSettled(
      batch.map(email => executeRegistrationDemo(browser, email))
    );

    index += CONCURRENCY;
  }

  await browser.close();
  console.log("🎉 [技術デモ] 全処理終了");
})();