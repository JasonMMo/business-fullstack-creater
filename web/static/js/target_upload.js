// Growth-82: XHR upload with progress indicator
(function () {
  'use strict';
  var form = document.getElementById('upload-form');
  var progressWrap = document.getElementById('upload-progress');
  var progressBar = document.getElementById('upload-progress-bar');
  var resultArea = document.getElementById('extraction-result-area');

  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var data = new FormData(form);
    var xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', function (evt) {
      if (evt.lengthComputable) {
        var pct = Math.round((evt.loaded / evt.total) * 100);
        progressWrap.style.display = 'block';
        progressBar.style.width = pct + '%';
        progressBar.textContent = pct + '%';
      }
    });

    xhr.addEventListener('load', function () {
      progressWrap.style.display = 'none';
      progressBar.style.width = '0%';
      resultArea.innerHTML = xhr.responseText;
    });

    xhr.addEventListener('error', function () {
      progressWrap.style.display = 'none';
      resultArea.innerHTML = '<p class="error-msg">네트워크 오류가 발생했습니다.</p>';
    });

    xhr.open('POST', form.action || '/target/upload');
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.send(data);
  });
})();
