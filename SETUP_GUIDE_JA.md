# FG830 新規GitHubリポジトリ導入手順

この手順は、ZIPを展開し、**完全に新しい公開GitHubリポジトリ**として動かす場合のものです。

## 0. 必要なもの

- GitHubアカウント
- Git
- Python 3.11以上
- ZIPを展開できる環境

## 1. ZIPを展開する

展開後、ターミナルでフォルダへ移動します。

```bash
cd future-gadget-No830-auto-temporal-transceiver
```

Windows PowerShellでも同じく、展開したフォルダでターミナルを開けば構いません。

## 2. 秘密鍵を一度だけ生成する

```bash
python -m temporal_mailbox setup-key --save-local --write-fingerprint
```

環境によっては `python3` を使います。

表示された以下を保存してください。

```text
name : TEMPORAL_KEY
value: 長い秘密文字列
```

同時に次が行われます。

- `.env.local` にローカル用秘密鍵を保存（Git除外済み）
- `data/protocol.json` に公開可能な鍵フィンガープリントを記録

**`.env.local` は絶対にGitへ追加しないでください。**

## 3. ローカルテスト

```bash
python -m unittest discover -s tests -v
python -m temporal_mailbox doctor
python -m temporal_mailbox simulate
python -m temporal_mailbox build-site
```

`simulate`は同梱fixtureを使うオフライン試験で、`data/transmissions/`へ本番記録を書きません。

画面の確認：

```bash
python -m http.server 8000
```

ブラウザで `http://localhost:8000/docs/` を開きます。初期状態では `AWAITING FIRST FRIDAY` と表示されます。

## 4. GitHubで空のリポジトリを作る

GitHubで `New repository` を選びます。

推奨設定：

- Repository name: `future-gadget-No830-auto-temporal-transceiver`
- Visibility: Public
- Add a README: オフ
- Add .gitignore: None
- Choose a license: None

ローカルにすでに全部入っているため、GitHub側では空のリポジトリにします。

## 5. 最初のpush

GitHubが表示するURLを使い、次を実行します。

```bash
git init
git add .
git status
git commit -m "Pre-commit FG830-ATX-v1"
git branch -M main
git remote add origin https://github.com/YOUR_NAME/future-gadget-No830-auto-temporal-transceiver.git
git push -u origin main
```

`git status`で `.env.local` が一覧に出ていないことを必ず確認してください。

## 6. GitHub Actions Secretを登録する

リポジトリで：

`Settings → Secrets and variables → Actions → New repository secret`

- Name: `TEMPORAL_KEY`
- Secret: 手順2で表示された `value`

秘密鍵は公開ファイルへ書かず、Actions Secretだけに置きます。

## 7. Actionsにコミット権限を与える

`Settings → Actions → General → Workflow permissions`

- `Read and write permissions` を選択
- Save

これがないと、受信・送信結果をActionsがリポジトリへpushできません。

## 8. GitHub Pagesを有効にする

`Settings → Pages → Build and deployment → Source`

`GitHub Actions` を選択します。

その後、`Actions`タブから `Deploy status page` を一度手動実行します。以後は、受信・送信ワークフロー自身がコミット直後にPagesも再デプロイするため、botのpushが別ワークフローを起動することに依存しません。

公開URLは通常次の形です。

```text
https://YOUR_NAME.github.io/future-gadget-No830-auto-temporal-transceiver/
```

正確なURLは `Deploy status page` の実行結果にも表示されます。

## 9. 初回のActions確認

`Actions`タブで次を確認します。

1. `Test protocol` を手動実行 → 緑色で完了
2. `Deploy status page` を手動実行 → 公開ページが開く
3. `Friday temporal reception` は**金曜日18:00 JSTより前だけ**手動実行可能
4. `Automatic Loto7 temporal transmission` は通常、自動スケジュールに任せる

金曜以外に受信Actionを実行すると、事後データの捏造を防ぐため意図的に失敗します。

## 10. 毎週の自動動作

- 金曜09:00 JST：受信データ取得・復号・コミット
- 金曜20:00 JST：公式結果確認
- 未掲載の場合：15分間隔で再確認
- 結果取得時：128ビット化・ローカル送信計算・コミット
- 受信・送信コミット直後：同じワークフロー内でPagesも自動更新

GitHub Actionsのcronは指定時刻ぴったりの開始を保証しません。混雑時の遅延に備え、送信側は20:00から15分間隔で土曜03:00直前まで再試行します。厳密な時刻が必要な場合は、末尾のsystemd案を併用してください。

## 11. 結果を見る場所

### 見やすい画面

GitHub PagesのURL。

### 最新状態

```text
docs/status.json
```

### 全履歴

```text
docs/history.json
```

### 各週の詳細

```text
data/receptions/YYYY-MM-DD.json
data/transmissions/YYYY-MM-DD.json
data/noise/YYYY-MM-DD.bin.zlib
```

## 12. よくあるエラー

### `TEMPORAL_KEY is not configured`

GitHub Secretの名前が正確に `TEMPORAL_KEY` か確認します。ローカルでは `.env.local` が存在するか確認します。

### `Permission denied` / push失敗

`Settings → Actions → General → Workflow permissions` を `Read and write permissions` にします。

### Pagesが404

`Settings → Pages → Source` が `GitHub Actions` か確認し、`Deploy status page` を手動実行します。

### 公式結果ページの解析に失敗

みずほ銀行側のページ構造変更の可能性があります。Actionsログに `ResultPageChanged` が出た場合、パーサーを修正するまでは偽の結果を記録しません。

### スケジュールが止まった

公開リポジトリは長期間活動がないとscheduled workflowが無効になる場合があります。Actionsタブでワークフローが有効か確認してください。正常稼働中は毎週の自動コミットが活動記録になります。

## 13. 常時稼働Linuxを併用する場合

GitHub cronの遅延を避けたい場合、`ops/`にsystemdの例があります。`ops/README.md`に従い、パス `/opt/fg830`、Python環境、Gitのpush資格情報を設定してください。ローカル実行後は同梱の `scripts/commit_and_push.sh` がデータをcommit/pushします。GitHub Actionsと同時運用するとpush競合が起きる可能性があるため、最初はGitHub Actions単独を推奨します。
