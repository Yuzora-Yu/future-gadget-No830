# FUTURE GADGET No.830 — AUTO TEMPORAL TRANSCEIVER

人間が結果確認や送信操作を忘れても、毎週同じ手順を自動実行するための公開実験リポジトリです。

- 金曜09:00 JST：受信ノイズを取得し、結果判明前にGitへ固定
- 金曜20:00 JST：みずほ銀行の公式ロト7結果ページを自動確認
- 未掲載：15分ごとに再確認（最長 土曜03:00 JST）
- 掲載済み：本数字・ボーナス数字を検証し、秘密鍵付き128ビットフレームへ変換
- 送信試行：秘密鍵で拡散した8,192チップを外部書き込みゼロのローカル計算として実行
- 完了後：公式ページ本文ハッシュ、フレーム、実行記録、受信フレームとの距離をコミット
- GitHub Pages：同じ受信・送信ワークフロー内で再デプロイし、最新結果と全履歴を表示

## 最初に読むもの

**新規リポジトリへの導入は [SETUP_GUIDE_JA.md](SETUP_GUIDE_JA.md) の順に進めてください。**

最短コマンド：

```bash
python -m temporal_mailbox setup-key --save-local --write-fingerprint
python -m unittest discover -s tests -v
python -m temporal_mailbox simulate
```

その後、空のGitHubリポジトリへ一式をpushし、Actions Secret `TEMPORAL_KEY`、Actionsの書き込み権限、GitHub PagesのSource=`GitHub Actions`を設定します。詳しい画面操作は `START_HERE_JA.txt` と `SETUP_GUIDE_JA.md` にあります。

## 結果を見る場所

GitHub Pagesを有効にすると、通常は次のURLです。

```text
https://<GitHubユーザー名>.github.io/<リポジトリ名>/
```

元データ：

```text
docs/status.json                    最新状態
docs/history.json                   受信・送信履歴
docs/integrity.json                 公開JSONのハッシュ
data/noise/YYYY-MM-DD.bin.zlib      結果前の受信ノイズ
data/receptions/YYYY-MM-DD.json     受信・復号記録
data/transmissions/YYYY-MM-DD.json  公式結果・送信試行記録
```

## ローカル画面

```bash
python -m temporal_mailbox build-site
python -m http.server 8000
```

`http://localhost:8000/docs/` を開きます。

## 重要な境界

このコードは、既知の物理学で過去通信が実現することを保証しません。実際に自動化するのは、結果前データの固定、公式結果の取得、秘密鍵による認証符号化、外部へ迷惑をかけないローカル計算、事後照合です。部分一致や「惜しい番号」は成功扱いにしません。

詳細： [PROTOCOL.md](PROTOCOL.md) / [TRANSMISSION_COVENANT.md](TRANSMISSION_COVENANT.md)
