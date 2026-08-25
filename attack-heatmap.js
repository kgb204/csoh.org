(function () {
  // Canonical MITRE ATT&CK Enterprise tactic order - this is fixed framework
  // structure (column order), not site content, so it stays a constant here.
  // Every actual technique/chain/count on this page comes from the fetched
  // JSON, not from anything hardcoded in this file.
  var TACTIC_ORDER = [
    "Reconnaissance", "Resource Development", "Initial Access", "Execution",
    "Persistence", "Privilege Escalation", "Defense Evasion", "Credential Access",
    "Discovery", "Lateral Movement", "Collection", "Command and Control",
    "Exfiltration", "Impact"
  ];

  var statusEl = document.getElementById('ah-status');
  var dwgEl = document.getElementById('ah-dwg-no');
  var tableEl = document.getElementById('ah-matrix');
  var legendEl = document.getElementById('ah-legend');
  var readoutEl = document.getElementById('ah-readout');

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function fetchJSON(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (res) {
      if (!res.ok) throw new Error(url + ': HTTP ' + res.status);
      return res.json();
    });
  }

  function fmtDate(iso) {
    try {
      var d = new Date(iso);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' }) + ' UTC';
    } catch (e) { return iso; }
  }

  function colorForCount(count, maxCount) {
    if (!count) return '#122544';
    var ratio = maxCount > 0 ? count / maxCount : 0;
    var r1 = 18, g1 = 37, b1 = 68;
    var r2 = 255, g2 = 176, b2 = 46;
    var r = Math.round(r1 + (r2 - r1) * ratio);
    var g = Math.round(g1 + (g2 - g1) * ratio);
    var b = Math.round(b1 + (b2 - b1) * ratio);
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }

  function showDetail(row) {
    var chainsList = row.chains
      .slice()
      .sort(function (a, b) { return a.name.localeCompare(b.name); })
      .map(function (c) { return '<li><a href="' + escapeHtml(c.url) + '">' + escapeHtml(c.name) + '</a></li>'; })
      .join('');
    var warn = row.inferred
      ? '<span class="ah-warn">🚩 This technique is valid under more than one ATT&amp;CK tactic; ' +
        'its placement here was inferred from the kill-chain step\'s context rather than an explicit ' +
        'single-tactic tag. Worth a human check.</span>'
      : '';
    readoutEl.innerHTML =
      '<span class="ah-hdr">' + escapeHtml(row.id) + ' - ' + escapeHtml(row.name) + ' &middot; ' + escapeHtml(row.tactic) + '</span>' +
      '<a class="ah-mitre-link" href="https://attack.mitre.org/techniques/' + encodeURIComponent(row.id.replace('.', '/')) + '/" target="_blank" rel="noopener">View on attack.mitre.org ↗</a>' +
      warn +
      ' Appears in ' + row.chains.length + ' of ' + row.totalChains + ' documented kill chains:' +
      '<ul>' + chainsList + '</ul>';
  }

  function renderMatrix(tactics, rowList) {
    var maxCount = rowList.reduce(function (m, r) { return Math.max(m, r.chains.length); }, 0);

    var thead = document.createElement('thead');
    var headRow = document.createElement('tr');
    headRow.innerHTML = '<th style="border:none;"></th>' + tactics.map(function (t) { return '<th>' + escapeHtml(t) + '</th>'; }).join('');
    thead.appendChild(headRow);

    var tbody = document.createElement('tbody');
    rowList.forEach(function (row) {
      var tr = document.createElement('tr');
      var th = document.createElement('th');
      th.innerHTML = '<span class="ah-tid">' + escapeHtml(row.id) + '</span>' + escapeHtml(row.name);
      tr.appendChild(th);
      tactics.forEach(function (tac) {
        var td = document.createElement('td');
        td.className = 'ah-cell';
        if (tac === row.tactic) {
          var count = row.chains.length;
          td.classList.add('has-data');
          td.style.background = colorForCount(count, maxCount);
          td.tabIndex = 0;
          td.setAttribute('role', 'button');
          td.setAttribute('aria-label', row.id + ' ' + row.name + ', ' + tac + ', used in ' + count + ' chains');
          td.innerHTML = '<span class="ah-count">' + count + '</span>' + (row.inferred ? '<span class="ah-flag" title="Inferred tactic placement">🚩</span>' : '');
          td.addEventListener('click', function () { showDetail(row); });
          td.addEventListener('mouseenter', function () { showDetail(row); });
          td.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); showDetail(row); }
          });
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    tableEl.innerHTML = '';
    tableEl.appendChild(thead);
    tableEl.appendChild(tbody);

    var swatches = [0, 1, 2, 3, 4].map(function (i) {
      var c = maxCount > 0 ? Math.round((i / 4) * maxCount) : 0;
      return '<span class="ah-swatch" style="background:' + colorForCount(c, maxCount) + '"></span>';
    }).join('');
    legendEl.innerHTML = '<span>fewer chains</span>' + swatches + '<span>more chains</span>' +
      '<span class="ah-flag-note">🚩 inferred tactic placement</span>';
  }

  function aggregate(chainDocs) {
    var rows = {};
    var tacticsPresent = {};
    chainDocs.forEach(function (doc) {
      (doc.techniques || []).forEach(function (t) {
        var key = t.id + '::' + t.tactic;
        if (!rows[key]) {
          rows[key] = { id: t.id, name: t.name, tactic: t.tactic, chains: [], inferred: false };
        }
        rows[key].chains.push({ name: doc.name, url: doc.url });
        if (t.inferred) rows[key].inferred = true;
        tacticsPresent[t.tactic] = true;
      });
    });

    var tactics = TACTIC_ORDER.filter(function (t) { return tacticsPresent[t]; });
    var rowList = Object.keys(rows).map(function (k) { return rows[k]; });
    rowList.forEach(function (r) { r.totalChains = chainDocs.length; });
    rowList.sort(function (a, b) {
      var ta = tactics.indexOf(a.tactic), tb = tactics.indexOf(b.tactic);
      if (ta !== tb) return ta - tb;
      if (b.chains.length !== a.chains.length) return b.chains.length - a.chains.length;
      return a.name.localeCompare(b.name);
    });
    return { tactics: tactics, rowList: rowList };
  }

  fetchJSON('/data/chains-index.json').then(function (index) {
    var chains = (index.chains || []);
    statusEl.textContent = 'Loading ' + chains.length + ' kill chains…';

    return Promise.all(chains.map(function (c) {
      return fetchJSON('/data/chains/' + c.file)
        .then(function (doc) { return { ok: true, doc: doc }; })
        .catch(function (err) { return { ok: false, error: err, meta: c }; });
    })).then(function (results) {
      var docs = results.filter(function (r) { return r.ok; }).map(function (r) { return r.doc; });
      var failed = results.filter(function (r) { return !r.ok; });

      if (docs.length === 0) {
        throw new Error('no chain files could be loaded');
      }

      var agg = aggregate(docs);
      renderMatrix(agg.tactics, agg.rowList);

      var inferredCount = agg.rowList.filter(function (r) { return r.inferred; }).length;
      var generated = index.generated ? fmtDate(index.generated) : 'unknown';
      dwgEl.innerHTML = 'CHAINS: ' + docs.length + '<br>UPDATED: ' + generated;

      var statusMsg = 'Live: ' + docs.length + ' kill chains, ' + agg.rowList.length + ' technique-tactic pairs' +
        (inferredCount ? ', ' + inferredCount + ' flagged for review' : '') + '.';
      if (failed.length) {
        statusMsg += ' (' + failed.length + ' chain file' + (failed.length === 1 ? '' : 's') + ' failed to load.)';
        statusEl.classList.add('is-error');
      }
      statusEl.textContent = statusMsg;
    });
  }).catch(function (err) {
    statusEl.textContent = 'Could not load kill chain data: ' + err.message;
    statusEl.classList.add('is-error');
    readoutEl.innerHTML = '<span class="ah-empty">Matrix unavailable - /data/chains-index.json failed to load or returned no usable chains.</span>';
  });
})();
