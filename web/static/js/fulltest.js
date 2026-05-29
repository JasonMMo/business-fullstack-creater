// Growth-83: full-test background runner + polling UI
(function () {
  'use strict';
  var btn = document.getElementById('fulltest-btn');
  if (!btn) return;

  var runId = btn.getAttribute('data-run-id');
  var statusBox = document.getElementById('fulltest-status');
  var labelEl = document.getElementById('fulltest-label');
  var layersEl = document.getElementById('fulltest-layers');
  var hintEl = document.getElementById('fulltest-hint');
  var errorEl = document.getElementById('fulltest-error');
  var greenBadge = document.getElementById('green-badge');

  var LAYER_LABELS = {
    L1: 'L1 단위 테스트',
    L2: 'L2 JDBC smoke',
    L3: 'L3 Maven 빌드',
    L4_full: 'L4 라이브 WAS (전체)',
    L4_partial: 'L4 라이브 WAS (부분)',
  };

  var pollInterval = null;

  function renderLayers(layers) {
    if (!layers) return;
    layersEl.innerHTML = '';
    Object.keys(LAYER_LABELS).forEach(function (key) {
      if (!(key in layers)) return;
      var li = document.createElement('li');
      var val = layers[key];
      li.className = 'fulltest-layer fulltest-layer-' + (val ? 'pass' : 'fail');
      li.textContent = (val ? '✅ ' : '❌ ') + LAYER_LABELS[key];
      layersEl.appendChild(li);
    });
  }

  function stopPolling() {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
  }

  function poll() {
    fetch('/domain/' + runId + '/fulltest/status')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.label) labelEl.textContent = data.label;
        renderLayers(data.layers);
        if (data.next_hint) { hintEl.textContent = data.next_hint; hintEl.style.display = 'block'; }
        if (data.error) { errorEl.textContent = data.error; errorEl.style.display = 'block'; }
        if (data.status !== 'running') {
          stopPolling();
          btn.disabled = false;
          btn.textContent = '풀테스트 다시 실행';
          if (data.green) {
            if (greenBadge) greenBadge.style.display = 'inline';
          }
        }
      })
      .catch(function () { /* ignore transient errors */ });
  }

  btn.addEventListener('click', function () {
    btn.disabled = true;
    btn.textContent = '실행 중...';
    statusBox.style.display = 'block';
    labelEl.textContent = '풀테스트 시작 중...';
    layersEl.innerHTML = '';
    hintEl.textContent = '';
    errorEl.style.display = 'none';
    if (greenBadge) greenBadge.style.display = 'none';

    fetch('/domain/' + runId + '/fulltest', { method: 'POST' })
      .then(function (r) {
        if (r.status === 409) {
          labelEl.textContent = '이미 실행 중입니다. 잠시 후 다시 시도해 주세요.';
          btn.disabled = false;
          btn.textContent = '풀테스트 실행';
          return;
        }
        // 202 accepted — start polling every 3s
        pollInterval = setInterval(poll, 3000);
        poll();
      })
      .catch(function () {
        labelEl.textContent = '시작 오류. 페이지를 새로고침 후 다시 시도해 주세요.';
        btn.disabled = false;
        btn.textContent = '풀테스트 실행';
      });
  });
})();
