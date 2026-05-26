/* business-fullstack-creater portal — preview.js (generated) */
(function () {
  'use strict';

  function init() {
    setupTabs();
    setupLaneRadios();
    setupCopyButtons();
  }

  /* --- Tab switching ---------------------------------------------------- */
  function setupTabs() {
    var tabBar = document.querySelector('.tab-bar[role="tablist"]');
    if (!tabBar) return;

    tabBar.addEventListener('click', function (e) {
      var btn = e.target.closest('[role="tab"]');
      if (!btn) return;

      var tabName = btn.getAttribute('data-tab');

      // Update aria-selected
      tabBar.querySelectorAll('[role="tab"]').forEach(function (t) {
        t.setAttribute('aria-selected', t === btn ? 'true' : 'false');
      });

      // Show/hide preview blocks for the active tab
      var activeLane = getActiveLane();
      document.querySelectorAll('.preview-block').forEach(function (block) {
        var matchTab = block.getAttribute('data-tab') === tabName;
        var matchLane = block.getAttribute('data-lane') === activeLane;
        block.hidden = !(matchTab && matchLane);
      });
    });
  }

  /* --- Lane radio change ------------------------------------------------ */
  function setupLaneRadios() {
    document.querySelectorAll('input[name="lane"]').forEach(function (radio) {
      radio.addEventListener('change', function () {
        var lane = radio.value;
        var activeTab = getActiveTab();

        // Filter preview blocks
        document.querySelectorAll('.preview-block').forEach(function (block) {
          var matchTab = block.getAttribute('data-tab') === activeTab;
          var matchLane = block.getAttribute('data-lane') === lane;
          block.hidden = !(matchTab && matchLane);
        });

        // Update download href
        document.querySelectorAll('.btn-download').forEach(function (a) {
          var href = a.getAttribute('href') || '';
          // Replace lane segment: ../scaffolds/<slug>/<old-lane>/project.zip
          a.setAttribute('href', href.replace(/\/scaffolds\/([^/]+)\/[^/]+\/project\.zip/, '/scaffolds/$1/' + lane + '/project.zip'));
        });
      });
    });
  }

  /* --- Copy to clipboard ------------------------------------------------ */
  function setupCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var targetId = btn.getAttribute('data-target');
        var el = targetId ? document.getElementById(targetId) : null;
        if (!el) return;

        var text = el.textContent || '';
        if (!navigator.clipboard) return;

        navigator.clipboard.writeText(text).then(function () {
          var orig = btn.textContent;
          btn.textContent = 'Copied!';
          setTimeout(function () { btn.textContent = orig; }, 1500);
        });
      });
    });
  }

  /* --- Helpers ---------------------------------------------------------- */
  function getActiveLane() {
    var checked = document.querySelector('input[name="lane"]:checked');
    return checked ? checked.value : 'jakarta';
  }

  function getActiveTab() {
    var active = document.querySelector('[role="tab"][aria-selected="true"]');
    return active ? active.getAttribute('data-tab') : 'ddl';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
