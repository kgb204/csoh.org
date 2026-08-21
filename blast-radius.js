/* ============================================================================
   Blast Radius Visualizer — page controller.

   Responsibilities (the reusable graph in blast-radius-graph.js owns none of
   this):
     - fetch /data/chains/chains-index.json and populate the scenario picker,
       so new chains added to the index appear here with no code change;
     - honour ?scenario=<id> in the URL for deep-links from kill chain pages,
       and keep the URL in sync as the user switches scenarios;
     - fetch the selected scenario file and hand it to the graph;
     - render the hop legend, type legend, blast readout, and an accessible
       text fallback list of what is reachable.
   ============================================================================ */
(function () {
  'use strict';

  var els = {};
  var index = null;
  var graph = null;
  var currentScenario = null;

  function $(id) { return document.getElementById(id); }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function fetchJSON(url) {
    return fetch(url, { credentials: 'same-origin' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + url);
      return r.json();
    });
  }

  function showEmpty(msg) {
    if (els.empty) {
      els.empty.textContent = msg;
      els.empty.style.display = 'flex';
    }
  }
  function hideEmpty() {
    if (els.empty) els.empty.style.display = 'none';
  }

  // ---- Picker ------------------------------------------------------------
  function buildPicker(scenarios) {
    els.select.innerHTML = '';
    scenarios.forEach(function (s) {
      var opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.title + (s.provider ? '  ·  ' + s.provider : '');
      els.select.appendChild(opt);
    });
  }

  function scenarioMeta(id) {
    return index.scenarios.filter(function (s) { return s.id === id; })[0] || null;
  }

  // ---- Load + render a scenario -----------------------------------------
  function loadScenario(id, pushUrl) {
    var meta = scenarioMeta(id);
    if (!meta) {
      showEmpty('Scenario "' + id + '" not found.');
      return;
    }
    els.select.value = id;
    showEmpty('Loading ' + meta.title + '…');

    fetchJSON('/' + meta.file).then(function (scenario) {
      currentScenario = scenario;
      hideEmpty();
      renderDescription(meta, scenario);
      if (!graph) {
        graph = new BlastRadiusGraph(els.svg, {
          onSelect: onSelect,
          onEdgeHover: onEdgeHover
        });
      }
      graph.setData(scenario);

      if (pushUrl) {
        var url = new URL(window.location.href);
        url.searchParams.set('scenario', id);
        window.history.replaceState({}, '', url);
      }
      document.title = meta.title + ' — Blast Radius Visualizer · CSOH';
    }).catch(function (err) {
      showEmpty('Could not load this scenario. ' + err.message);
    });
  }

  function renderDescription(meta, scenario) {
    var html = '';
    if (scenario.description) html += escapeHtml(scenario.description) + ' ';
    if (meta.page) {
      html += '<a href="/' + escapeAttr(meta.page) + '">Read the full ' +
        escapeHtml(meta.title) + ' kill chain →</a>';
    }
    els.desc.innerHTML = html;
  }

  // ---- Graph callbacks ---------------------------------------------------
  function onSelect(originId, result) {
    var node = nodeById(originId);
    renderReadout(node, result);
    renderHopLegend(result);
    renderA11yList(originId, result);
  }

  var hideTooltipTimer = null;
  function onEdgeHover(link, event) {
    if (!link) {
      els.tooltip.classList.remove('show');
      return;
    }
    var s = typeof link.source === 'object' ? link.source : nodeById(link.source);
    var t = typeof link.target === 'object' ? link.target : nodeById(link.target);
    els.tooltip.innerHTML =
      '<div>' + escapeHtml(s.label) + ' <span aria-hidden="true">→</span> ' +
      escapeHtml(t.label) + '</div>' +
      '<div class="br-tt-tech">' + escapeHtml(link.tech || '') + '</div>';
    var stageRect = els.stage.getBoundingClientRect();
    var x = event.clientX - stageRect.left + 12;
    var y = event.clientY - stageRect.top + 12;
    // Keep the tooltip inside the stage horizontally.
    els.tooltip.style.left = Math.min(x, stageRect.width - 20) + 'px';
    els.tooltip.style.top = y + 'px';
    els.tooltip.classList.add('show');
  }

  // ---- Panels ------------------------------------------------------------
  function renderReadout(originNode, result) {
    if (!originNode) return;
    var total = currentScenario.nodes.length;
    var reached = result.reached.size;                 // includes origin
    var downstream = reached - 1;
    var pct = total > 1 ? Math.round((downstream / (total - 1)) * 100) : 0;

    var html = 'Origin: <span class="br-origin-name">' + escapeHtml(originNode.label) +
      '</span> <span class="br-metric">(' + escapeHtml(originNode.type || 'node') + ')</span>. ';

    if (downstream === 0) {
      html += 'Nothing downstream — this is a terminal node in the chain.';
    } else {
      html += 'Compromise here reaches <strong class="br-metric">' + downstream +
        '</strong> of ' + (total - 1) + ' other assets (<span class="br-metric">' +
        pct + '%</span> of the graph), across <strong class="br-metric">' +
        result.maxHop + '</strong> hop' + (result.maxHop === 1 ? '' : 's') + '.';
    }
    els.readout.innerHTML = html;
  }

  function renderHopLegend(result) {
    // Count nodes at each hop distance.
    var counts = {};
    Object.keys(result.distance).forEach(function (id) {
      var d = result.distance[id];
      counts[d] = (counts[d] || 0) + 1;
    });
    var maxHop = result.maxHop;
    var rows = '';
    for (var d = 0; d <= maxHop; d++) {
      var color = BlastRadiusGraph.hopColor(d);
      var label = d === 0 ? 'Origin' : (d + ' hop' + (d === 1 ? '' : 's') + ' away');
      rows += '<div class="br-hoprow' + (d === 0 ? ' zero' : '') + '">' +
        '<span class="br-swatch" style="background:' + color + '"></span>' +
        '<span>' + label + '</span>' +
        '<span class="br-hopcount">' + (counts[d] || 0) + '</span></div>';
    }
    els.hoplegend.innerHTML = rows;
  }

  function renderA11yList(originId, result) {
    // Ordered, text-only reachability for screen readers and no-graph fallback.
    var byHop = {};
    Object.keys(result.distance).forEach(function (id) {
      if (id === originId) return;
      var d = result.distance[id];
      (byHop[d] = byHop[d] || []).push(nodeById(id).label);
    });
    var items = '';
    Object.keys(byHop).map(Number).sort(function (a, b) { return a - b; }).forEach(function (d) {
      items += '<li><strong>Hop ' + d + ':</strong> ' +
        byHop[d].map(escapeHtml).join(', ') + '</li>';
    });
    els.a11yList.innerHTML = items || '<li>No downstream assets from this origin.</li>';
  }

  function renderTypeLegend() {
    var html = '';
    BlastRadiusGraph.TYPE_ORDER.forEach(function (type) {
      var meta = BlastRadiusGraph.typeMeta(type);
      html += '<span class="br-typeitem">' +
        '<span class="br-typedot" style="background:' + meta.fill + '"></span>' +
        type + '</span>';
    });
    els.typelegend.innerHTML = html;
  }

  // ---- Helpers -----------------------------------------------------------
  function nodeById(id) {
    if (!currentScenario) return null;
    return currentScenario.nodes.filter(function (n) { return n.id === id; })[0] || null;
  }
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function escapeAttr(s) { return escapeHtml(s); }

  function getScenarioParam() {
    try {
      return new URL(window.location.href).searchParams.get('scenario');
    } catch (e) { return null; }
  }

  // ---- Boot --------------------------------------------------------------
  ready(function () {
    els.select = $('br-scenario');
    els.svg = $('br-graph');
    els.stage = $('br-stage');
    els.empty = $('br-empty');
    els.desc = $('br-desc');
    els.readout = $('br-readout');
    els.hoplegend = $('br-hoplegend');
    els.typelegend = $('br-typelegend');
    els.a11yList = $('br-a11y-list');
    els.tooltip = $('br-tooltip');
    els.reset = $('br-reset');

    if (!els.svg || typeof BlastRadiusGraph === 'undefined') {
      showEmpty('The visualizer needs JavaScript and the D3 library to run.');
      return;
    }

    renderTypeLegend();

    els.select.addEventListener('change', function () {
      loadScenario(els.select.value, true);
    });
    if (els.reset) {
      els.reset.addEventListener('click', function () {
        if (currentScenario) {
          var origin = currentScenario.defaultOrigin || currentScenario.nodes[0].id;
          graph.selectNode(origin);
        }
      });
    }

    fetchJSON('/data/chains/chains-index.json').then(function (data) {
      index = data;
      if (!index.scenarios || !index.scenarios.length) {
        showEmpty('No scenarios are configured yet.');
        return;
      }
      buildPicker(index.scenarios);

      var requested = getScenarioParam();
      var initial = (requested && scenarioMeta(requested))
        ? requested
        : index.scenarios[0].id;
      loadScenario(initial, false);
    }).catch(function (err) {
      showEmpty('Could not load the scenario index. ' + err.message);
    });
  });
})();
