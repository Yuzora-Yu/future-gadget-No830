# Optional systemd runner

GitHub Actionsのcron遅延に備える、常時稼働Linux用の任意構成です。最初はGitHub Actionsだけで動かし、必要になってから追加してください。

## 前提

- リポジトリを `/opt/fg830` にclone済み
- `/opt/fg830/.venv` にPython仮想環境を作成済み
- `.env.local` に `TEMPORAL_KEY` を保存済み
- `git push`できるSSH鍵またはcredential helperを設定済み
- Playwright Chromiumを導入済み

```bash
cd /opt/fg830
python3 -m venv .venv
.venv/bin/pip install -e '.[transmit]'
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python -m temporal_mailbox doctor
```

## 導入

```bash
sudo cp ops/fg830-*.service ops/fg830-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fg830-receive.timer fg830-transmit.timer
systemctl list-timers 'fg830-*'
```

## 注意

`commit_and_push.sh`は `data/` と公開用JSONだけをcommitします。GitHub Actionsと同時に動かすとpush競合の可能性があるため、二重運用時はログを監視してください。
