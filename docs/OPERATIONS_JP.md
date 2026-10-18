# 管理職向け運用手順（試行用）

**重要:** 本リポジトリは匿名・架空データによる検証用です。個人情報・人事考課の実データは組織の承認前に入力しないでください。

## 1. 初期準備
Windows に Python 3.11 以上と組織が許可した Rust ツールチェーンを準備します。管理者権限なしで実行できるか、IT部門に確認してください。

```powershell
cargo test --manifest-path rust-core\Cargo.toml
cargo build --release --manifest-path rust-core\Cargo.toml
$env:PYTHONPATH = "$PWD\python"
python -m unittest discover -s tests -v
```

## 2. 架空データで試行
```powershell
python -m edu_workflow.cli --db .\data\demo.sqlite import-json --file .\examples\cases.json
python -m edu_workflow.cli --db .\data\demo.sqlite tick --backend rust --rust-bin .\rust-core\target\release\edu_rules.exe --at 2026-10-19T09:00:00+09:00
python -m edu_workflow.cli --db .\data\demo.sqlite alerts
python -m edu_workflow.cli --db .\data\demo.sqlite deliver --channel file --out-dir .\notifications
```

## 3. 締切確認と承認
- メールから推定した締切は必ず確認し、確定するまで仮登録にする
- 根拠資料が不足する案件は承認不可にする
- 人事判断と公式文書の提出は必ず管理職本人が行う
- `cases` で revision を確認して `confirm-deadline` または `decide` を実行する
- `audit` で判断履歴を確認する

## 4. 定期実行とアラート
Rust 実行ファイルを準備後、承認された端末で `windows/install_task.ps1` を実行します。初期状態はローカルファイル通知のみ。メール送信・Outlook読取は明示許可まで無効です。

## 5. 障害時
- 送信結果が UNKNOWN の通知は自動再送しない。運用担当者が送信先の受信状況を照合する
- 二重登録や期限の異常があれば、元メールと内部 `case_id` を照合する
- 制度改正により根拠が古くなった場合は、人が規程の現行版を確認してから再試行する
