const $ = (id) => document.getElementById(id);
const two = (n) => String(n).padStart(2, '0');
const nums = (values) => Array.isArray(values) ? values.map(two).join(' ') : '—';
const shortHash = (value) => typeof value === 'string' ? value.slice(0, 20) : '—';

const rows = (target, entries) => {
  target.replaceChildren();
  for (const [key, value] of entries) {
    const dt = document.createElement('dt');
    const dd = document.createElement('dd');
    dt.textContent = key;
    dd.textContent = value ?? '—';
    target.append(dt, dd);
  }
};

const renderBalls = (target, values) => {
  target.replaceChildren();
  if (!Array.isArray(values)) return;
  for (const value of values) {
    const ball = document.createElement('span');
    ball.className = 'ball';
    ball.textContent = two(value);
    target.append(ball);
  }
};

const renderProtocol = (protocol) => {
  $('protocol-badge').textContent = `${protocol.protocol_version || 'UNKNOWN'} · SOFTWARE ${protocol.software_version || '—'}`;
  $('key-badge').textContent = `KEY FP ${shortHash(protocol.key_fingerprint)}`;
};

const renderStatus = (status) => {
  const rx = status.latest_reception;
  if (rx) {
    $('rx-state').textContent = rx.authenticated ? 'AUTHENTICATED FRAME' : 'NO AUTHENTICATED FRAME';
    $('rx-state').className = `state ${rx.authenticated ? 'good' : 'muted'}`;
    rows($('rx-details'), [
      ['DATE', rx.date],
      ['ELIGIBLE', rx.eligible_for_temporal_claim ? 'YES' : 'NO'],
      ['RANK', `${rx.rank ?? '—'} / ${rx.population ?? '—'}`],
      ['STRENGTH', rx.strength],
      ['DECODED', rx.decoded ? nums(rx.decoded.main) : '—'],
      ['NOISE SHA', shortHash(rx.noise?.sha256)],
      ['CAPTURED', rx.collected_at_jst],
    ]);
  } else {
    $('rx-state').textContent = 'AWAITING FIRST FRIDAY';
    $('rx-state').className = 'state pending';
    rows($('rx-details'), []);
  }

  const tx = status.latest_transmission;
  if (tx) {
    $('result-state').textContent = 'OFFICIAL RESULT ACQUIRED';
    $('result-state').className = 'state good';
    $('result-draw').textContent = `第${tx.draw}回 · ${tx.date}`;
    renderBalls($('result-main'), tx.main);
    $('result-bonus').textContent = nums(tx.bonus);
    $('result-checked').textContent = `自動確認: ${tx.checked_at_jst ?? '—'}`;
    const source = $('result-source');
    if (tx.official_source) {
      source.href = tx.official_source;
      source.classList.remove('hidden');
    }

    $('tx-state').textContent = tx.completed ? 'TRANSMISSION EXECUTED' : 'PENDING';
    $('tx-state').className = `state ${tx.completed ? 'good' : 'pending'}`;
    rows($('tx-details'), [
      ['DRAW', `第${tx.draw}回`],
      ['DATE', tx.date],
      ['MAIN', nums(tx.main)],
      ['BONUS', nums(tx.bonus)],
      ['RX/TX HAMMING', tx.received_target_hamming_distance],
      ['FRAME SHA', shortHash(tx.frame_sha256)],
      ['ACTUATOR SHA', shortHash(tx.actuation?.transcript_sha256)],
      ['NETWORK WRITES', tx.actuation?.network_writes],
    ]);
  } else {
    $('result-state').textContent = 'AWAITING OFFICIAL RESULT';
    $('result-state').className = 'state pending';
    $('result-draw').textContent = '金曜20:00以降に自動更新';
    $('result-bonus').textContent = '—';
    $('tx-state').textContent = 'AWAITING OFFICIAL RESULT';
    $('tx-state').className = 'state pending';
    rows($('tx-details'), []);
  }
  $('updated').textContent = status.updated_at_jst || 'NOT UPDATED YET';
};

const renderHistory = (history) => {
  const body = $('history-body');
  body.replaceChildren();
  const records = Array.isArray(history.transmissions) ? [...history.transmissions].reverse() : [];
  if (records.length === 0) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 6;
    cell.textContent = 'まだ送信記録はありません。最初の金曜20:00以降に自動追加されます。';
    row.append(cell);
    body.append(row);
    return;
  }
  for (const item of records) {
    const row = document.createElement('tr');
    const values = [
      item.date,
      `第${item.draw}回`,
      nums(item.main),
      nums(item.bonus),
      item.received_target_hamming_distance ?? '—',
      item.completed ? 'EXECUTED' : 'PENDING',
    ];
    for (const value of values) {
      const cell = document.createElement('td');
      cell.textContent = value;
      row.append(cell);
    }
    body.append(row);
  }
};

const json = (name) => fetch(`${name}?t=${Date.now()}`, {cache: 'no-store'}).then((response) => {
  if (!response.ok) throw new Error(`${name}: ${response.status}`);
  return response.json();
});

Promise.all([json('status.json'), json('history.json'), json('protocol.json')])
  .then(([status, history, protocol]) => {
    renderProtocol(protocol);
    renderStatus(status);
    renderHistory(history);
  })
  .catch((error) => {
    $('result-state').textContent = 'STATUS LOAD ERROR';
    $('rx-state').textContent = 'STATUS LOAD ERROR';
    $('tx-state').textContent = 'STATUS LOAD ERROR';
    $('history-body').innerHTML = '<tr><td colspan="6">データを読み込めませんでした。GitHub PagesまたはHTTPサーバー経由で開いてください。</td></tr>';
    console.error(error);
  });
