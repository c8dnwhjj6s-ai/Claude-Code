<?php
declare(strict_types=1);

header('Content-Type: text/html; charset=UTF-8');

const TO_EMAIL   = 'info@jpcreate.com';
const FROM_EMAIL = 'info@jpcreate.com';
const SITE_NAME  = 'LED VISION';

function h(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}
function post_text(string $key, int $max = 4000): string {
    $v = $_POST[$key] ?? '';
    if (!is_string($v)) return '';
    $v = trim(str_replace("\0", '', $v));
    return mb_substr($v, 0, $max, 'UTF-8');
}
function one_line(string $key, int $max = 200): string {
    return trim(preg_replace('/[\r\n]+/u', ' ', post_text($key, $max)) ?? '');
}
function fail_page(string $message, int $status = 400): never {
    http_response_code($status);
    $msg = h($message);
    echo '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">';
    echo '<title>送信できませんでした｜LED VISION</title>';
    echo '<style>body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;background:#0a0e14;color:#f5f7fa;margin:0}.box{max-width:720px;margin:10vh auto;background:#12181f;padding:40px;border-radius:12px;border:1px solid #262d38}h1{font-size:26px}.btn{display:inline-block;margin-top:18px;padding:13px 22px;border-radius:3px;background:#ff3d3d;color:#fff;text-decoration:none;font-weight:700}@media(max-width:640px){.box{margin:30px 16px;padding:26px}}</style></head><body>';
    echo '<main class="box"><h1>送信できませんでした</h1><p>'.$msg.'</p><p>入力内容をご確認のうえ、もう一度お試しください。</p><a class="btn" href="javascript:history.back()">入力画面へ戻る</a></main></body></html>';
    exit;
}
function send_utf8_mail(string $to, string $subject, string $body, string $headers): bool {
    if (function_exists('mb_language')) mb_language('Japanese');
    if (function_exists('mb_internal_encoding')) mb_internal_encoding('UTF-8');
    if (function_exists('mb_send_mail')) {
        return mb_send_mail($to, $subject, $body, $headers);
    }
    $encoded = function_exists('mb_encode_mimeheader')
        ? mb_encode_mimeheader($subject, 'UTF-8')
        : '=?UTF-8?B?'.base64_encode($subject).'?=';
    return mail($to, $encoded, $body, $headers);
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    fail_page('このページはフォームから送信してください。', 405);
}

// Honeypot
if (post_text('website', 500) !== '') {
    // Botには成功したように見せる
    header('Location: thanks.html', true, 303);
    exit;
}

// 最低入力時間（JS無効環境は空なので許可）
$started = post_text('form_started', 30);
if ($started !== '' && ctype_digit($started)) {
    $elapsed = (int)(microtime(true) * 1000) - (int)$started;
    if ($elapsed >= 0 && $elapsed < 2500) {
        fail_page('送信が早すぎます。数秒待ってから再度お試しください。', 429);
    }
}

// 簡易レート制限: 同一IPから10分に6回まで
$ip = (string)($_SERVER['REMOTE_ADDR'] ?? 'unknown');
$key = hash('sha256', $ip . '|led-vision-lp-contact');
$rateFile = rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR . 'jpcreate_' . $key . '.json';
$now = time();
$attempts = [];
if (is_file($rateFile)) {
    $decoded = json_decode((string)@file_get_contents($rateFile), true);
    if (is_array($decoded)) $attempts = $decoded;
}
$attempts = array_values(array_filter($attempts, fn($t) => is_int($t) && $t > $now - 600));
if (count($attempts) >= 6) {
    fail_page('短時間に送信回数が多くなっています。しばらく時間を空けてからお試しください。', 429);
}
$attempts[] = $now;
@file_put_contents($rateFile, json_encode($attempts), LOCK_EX);

// Fields
$company  = one_line('company', 150);
$name     = one_line('name', 100);
$email    = one_line('email', 254);
$tel      = one_line('tel', 50);
$venue    = one_line('venue', 150);
$message  = post_text('message', 5000);
$formPage = one_line('form_page', 100);

if ($company === '') fail_page('会社名を入力してください。');
if ($name === '') fail_page('ご担当者名を入力してください。');
if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) fail_page('正しいメールアドレスを入力してください。');
if (preg_match('/[\r\n]/', $email)) fail_page('メールアドレスの形式が正しくありません。');
if ($message === '') fail_page('お問い合わせ内容を入力してください。');

$subject = '【LED VISION】導入お問い合わせ';
$adminBody =
"Webサイト(LED VISION)からお問い合わせがありました。\n\n".
"■ 送信元ページ\n".($formPage !== '' ? $formPage : 'Webフォーム')."\n\n".
"■ 会社名\n".$company."\n\n".
"■ ご担当者名\n".$name."\n\n".
"■ メールアドレス\n".$email."\n\n".
"■ 電話番号\n".($tel !== '' ? $tel : '未入力')."\n\n".
"■ 施設名・設置場所\n".($venue !== '' ? $venue : '未入力')."\n\n".
"■ お問い合わせ内容\n".$message."\n\n".
"------------------------------\n".
"送信日時: ".date('Y-m-d H:i:s')."\n".
"送信元IP: ".$ip."\n";

$adminHeaders =
"From: ".SITE_NAME." <".FROM_EMAIL.">\r\n".
"Reply-To: ".$email."\r\n".
"MIME-Version: 1.0\r\n".
"Content-Type: text/plain; charset=UTF-8\r\n".
"Content-Transfer-Encoding: 8bit";

if (!send_utf8_mail(TO_EMAIL, $subject, $adminBody, $adminHeaders)) {
    fail_page('メール送信処理でエラーが発生しました。お急ぎの場合は 0120-339-114 までお電話ください。', 500);
}

// Auto reply
$userSubject = '【JPクリエイト】お問い合わせを受け付けました';
$userBody =
$name." 様\n\n".
"このたびはLED VISIONへお問い合わせいただき、ありがとうございます。\n".
"以下の内容でお問い合わせを受け付けました。\n".
"担当者より内容を確認のうえご連絡いたします。\n\n".
"------------------------------\n".
"会社名: ".$company."\n".
"ご担当者名: ".$name."\n".
"メールアドレス: ".$email."\n".
"電話番号: ".($tel !== '' ? $tel : '未入力')."\n".
"施設名・設置場所: ".($venue !== '' ? $venue : '未入力')."\n\n".
"お問い合わせ内容:\n".$message."\n".
"------------------------------\n\n".
"株式会社JPクリエイト\n".
"フリーダイヤル: 0120-339-114（受付時間 平日9:00-18:00）\n".
"E-mail: ".TO_EMAIL."\n\n".
"※このメールはWebフォームからの受付確認として自動送信しています。";

$userHeaders =
"From: 株式会社JPクリエイト <".FROM_EMAIL.">\r\n".
"Reply-To: ".TO_EMAIL."\r\n".
"MIME-Version: 1.0\r\n".
"Content-Type: text/plain; charset=UTF-8\r\n".
"Content-Transfer-Encoding: 8bit";

send_utf8_mail($email, $userSubject, $userBody, $userHeaders);

header('Location: thanks.html', true, 303);
exit;
