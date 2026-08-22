/* ============================================================================
   BlastRadiusGraph — a reusable D3 force-directed graph component.

   Vanilla JS, no framework. Depends only on a global `d3` (v7) being loaded
   first. Renders a scenario's nodes/links, and on node select runs a
   breadth-first search from that origin along link direction, colouring every
   reachable node and edge by hop distance ("blast radius").

   Scenario schema (see data/chains/README.md):
     { id, title, description, defaultOrigin,
       nodes: [ { id, label, type } ],
       links: [ { source, target, tech } ] }

   Usage:
     const graph = new BlastRadiusGraph(svgElement, {
       onSelect(origin, result) { ... },   // result: see computeBlastRadius()
       onEdgeHover(link, event) { ... },    // null link on hover-out
     });
     graph.setData(scenario);
     graph.selectNode('attacker');

   The component owns only the <svg> it is given. Legend, readout and picker
   are the page controller's job — it subscribes via the callbacks above.
   ============================================================================ */
(function (global) {
  'use strict';

  // Hop-distance colour ramp, read from CSS custom properties so the graph
  // stays in sync with the stylesheet / theme. Index 0 = origin.
  var HOP_VARS = ['--hop-0', '--hop-1', '--hop-2', '--hop-3', '--hop-4', '--hop-5'];
  var HOP_FAR_VAR = '--hop-far';

  // Node type → single-character glyph + fill. Fill is only used for the
  // "unreached" resting state; reachable nodes are recoloured by hop distance.
  var TYPE_META = {
    attacker:   { glyph: '☠', fill: '#ef4444' }, // skull
    identity:   { glyph: '@', fill: '#f59e0b' }, // @
    endpoint:   { glyph: '■', fill: '#8b5cf6' }, // filled square
    credential: { glyph: '⚿', fill: '#eab308' }, // key-ish
    service:    { glyph: '⚙', fill: '#0ea5e9' }, // gear
    compute:    { glyph: '▣', fill: '#6366f1' }, // server
    network:    { glyph: '⇄', fill: '#14b8a6' }, // arrows
    storage:    { glyph: '◓', fill: '#0891b2' }, // cylinder-ish
    data:       { glyph: '◈', fill: '#10b981' }, // diamond
    impact:     { glyph: '✹', fill: '#dc2626' }, // burst
    control:    { glyph: '⛨', fill: '#059669' }  // shield — a defensive measure, not an asset
  };
  var TYPE_ORDER = ['attacker', 'identity', 'endpoint', 'credential', 'service',
    'compute', 'network', 'storage', 'data', 'impact', 'control'];
  var DEFAULT_TYPE = { glyph: '●', fill: '#94a3b8' };

  function typeMeta(type) {
    return TYPE_META[type] || DEFAULT_TYPE;
  }

  function cssVar(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name);
      return (v && v.trim()) || fallback;
    } catch (e) {
      return fallback;
    }
  }

  // Colour for a given hop distance (0 = origin). Distances beyond the ramp
  // collapse to the "far" colour so arbitrarily deep chains still render.
  function hopColor(dist) {
    if (dist == null || dist < 0) return null;
    if (dist < HOP_VARS.length) return cssVar(HOP_VARS[dist], '#ef4444');
    return cssVar(HOP_FAR_VAR, '#0e7490');
  }

  /**
   * Breadth-first search from `originId` following link direction.
   * Pure function — exposed as a static so it can be unit-tested and reused.
   * Returns { distance: {id: hops}, order: [ids by hop], edges: Set("s|t"),
   *           reached: Set(ids), maxHop }.
   */
  function computeBlastRadius(nodes, links, originId) {
    var adjacency = {};
    nodes.forEach(function (n) { adjacency[n.id] = []; });
    links.forEach(function (l) {
      var s = typeof l.source === 'object' ? l.source.id : l.source;
      var t = typeof l.target === 'object' ? l.target.id : l.target;
      if (adjacency[s]) adjacency[s].push({ to: t, key: s + '|' + t });
    });

    var distance = {};
    var edges = {};        // "source|target" -> true for tree/cross edges within reach
    var order = [];
    var maxHop = 0;

    if (adjacency[originId] === undefined) {
      return { distance: distance, order: order, edges: new Set(),
        reached: new Set(), maxHop: 0 };
    }

    distance[originId] = 0;
    var queue = [originId];
    while (queue.length) {
      var cur = queue.shift();
      order.push(cur);
      var d = distance[cur];
      if (d > maxHop) maxHop = d;
      adjacency[cur].forEach(function (edge) {
        // Any edge from a reached node into the reachable set is "lit".
        if (distance[edge.to] === undefined) {
          distance[edge.to] = d + 1;
          queue.push(edge.to);
          edges[edge.key] = true;
        } else if (distance[edge.to] >= d + 1) {
          // A shorter-or-equal alternate path — still part of the blast picture.
          edges[edge.key] = true;
        }
      });
    }

    var reached = new Set(Object.keys(distance));
    return {
      distance: distance,
      order: order,
      edges: new Set(Object.keys(edges)),
      reached: reached,
      maxHop: maxHop
    };
  }

  function BlastRadiusGraph(svgEl, options) {
    if (!global.d3) throw new Error('BlastRadiusGraph requires d3 to be loaded first');
    this.d3 = global.d3;
    this.svgEl = svgEl;
    this.options = options || {};
    this.scenario = null;
    this.origin = null;
    this.simulation = null;
    this._built = false;
    this._onResize = this._debounce(this._resize.bind(this), 180);
    global.addEventListener('resize', this._onResize);
  }

  BlastRadiusGraph.computeBlastRadius = computeBlastRadius;
  BlastRadiusGraph.typeMeta = typeMeta;
  BlastRadiusGraph.hopColor = hopColor;
  BlastRadiusGraph.TYPE_ORDER = TYPE_ORDER;

  BlastRadiusGraph.prototype._debounce = function (fn, wait) {
    var t;
    return function () {
      var args = arguments, self = this;
      clearTimeout(t);
      t = setTimeout(function () { fn.apply(self, args); }, wait);
    };
  };

  BlastRadiusGraph.prototype._dims = function () {
    var rect = this.svgEl.getBoundingClientRect();
    return {
      width: Math.max(320, rect.width || 800),
      height: Math.max(360, rect.height || 560)
    };
  };

  /** Load a scenario and render it. Runs BFS from defaultOrigin (or first node). */
  BlastRadiusGraph.prototype.setData = function (scenario) {
    var d3 = this.d3;
    this.scenario = scenario;

    // Deep-copy so the force sim can mutate x/y/vx/vy without touching source data.
    this.nodes = scenario.nodes.map(function (n) { return Object.assign({}, n); });
    this.links = scenario.links.map(function (l) { return Object.assign({}, l); });

    var dims = this._dims();
    var svg = d3.select(this.svgEl);
    svg.selectAll('*').remove();
    svg.attr('viewBox', '0 0 ' + dims.width + ' ' + dims.height)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .attr('role', 'img');

    // Arrowhead marker for directed edges.
    var defs = svg.append('defs');
    defs.append('marker')
      .attr('id', 'br-arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-4L9,0L0,4')
      .attr('class', 'br-arrowhead')
      .attr('fill', cssVar('--br-border', '#cbd5e1'));

    this.linkG = svg.append('g').attr('class', 'br-links');
    this.nodeG = svg.append('g').attr('class', 'br-nodes');

    var self = this;

    this.linkSel = this.linkG.selectAll('line')
      .data(this.links)
      .enter().append('line')
      .attr('class', 'br-link')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#br-arrow)')
      .on('mousemove', function (event, d) {
        if (self.options.onEdgeHover) self.options.onEdgeHover(d, event);
      })
      .on('mouseleave', function () {
        if (self.options.onEdgeHover) self.options.onEdgeHover(null, null);
      });

    this.nodeSel = this.nodeG.selectAll('g')
      .data(this.nodes)
      .enter().append('g')
      .attr('class', 'br-node')
      .attr('tabindex', 0)
      .attr('role', 'button')
      .attr('aria-label', function (d) { return d.label + ' (' + (d.type || 'node') + ')'; })
      .on('click', function (event, d) { self.selectNode(d.id); })
      .on('keydown', function (event, d) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          self.selectNode(d.id);
        }
      })
      .call(d3.drag()
        .on('start', function (event, d) {
          if (!event.active) self.simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', function (event, d) { d.fx = event.x; d.fy = event.y; })
        .on('end', function (event, d) {
          if (!event.active) self.simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }));

    this.nodeSel.append('circle')
      .attr('r', function (d) { return d.type === 'attacker' || d.type === 'impact' ? 15 : 12; })
      .attr('fill', function (d) { return typeMeta(d.type).fill; });

    this.nodeSel.append('text')
      .attr('class', 'br-node-glyph')
      .text(function (d) { return typeMeta(d.type).glyph; });

    this.nodeSel.append('text')
      .attr('class', 'br-node-label')
      .attr('x', 0)
      .attr('y', function (d) {
        return (d.type === 'attacker' || d.type === 'impact' ? 15 : 12) + 12;
      })
      .attr('text-anchor', 'middle')
      .text(function (d) { return d.label; });

    // Force layout. Link distance scales a little with graph size.
    var linkDist = this.nodes.length > 10 ? 95 : 110;
    this.simulation = d3.forceSimulation(this.nodes)
      .force('link', d3.forceLink(this.links).id(function (d) { return d.id; })
        .distance(linkDist).strength(0.6))
      .force('charge', d3.forceManyBody().strength(-420))
      .force('center', d3.forceCenter(dims.width / 2, dims.height / 2))
      .force('collide', d3.forceCollide().radius(46))
      .force('x', d3.forceX(dims.width / 2).strength(0.05))
      .force('y', d3.forceY(dims.height / 2).strength(0.05))
      .on('tick', function () { self._tick(dims); });

    this._built = true;

    var origin = scenario.defaultOrigin && this._hasNode(scenario.defaultOrigin)
      ? scenario.defaultOrigin
      : (this.nodes[0] && this.nodes[0].id);
    this.selectNode(origin);
  };

  BlastRadiusGraph.prototype._hasNode = function (id) {
    return this.nodes.some(function (n) { return n.id === id; });
  };

  BlastRadiusGraph.prototype._tick = function (dims) {
    var pad = 40;
    this.nodes.forEach(function (d) {
      d.x = Math.max(pad, Math.min(dims.width - pad, d.x));
      d.y = Math.max(pad, Math.min(dims.height - pad, d.y));
    });
    this.linkSel
      .attr('x1', function (d) { return d.source.x; })
      .attr('y1', function (d) { return d.source.y; })
      .attr('x2', function (d) { return d.target.x; })
      .attr('y2', function (d) { return d.target.y; });
    this.nodeSel.attr('transform', function (d) {
      return 'translate(' + d.x + ',' + d.y + ')';
    });
  };

  /** Select a node as the blast origin and repaint reachability. */
  BlastRadiusGraph.prototype.selectNode = function (originId) {
    if (!this._built || !this._hasNode(originId)) return;
    this.origin = originId;

    var result = computeBlastRadius(this.nodes, this.links, originId);
    var distance = result.distance;
    var litEdges = result.edges;

    this.nodeSel
      .classed('origin', function (d) { return d.id === originId; })
      .classed('selected', function (d) { return d.id === originId; })
      .classed('dimmed', function (d) { return distance[d.id] === undefined; });

    this.nodeSel.select('circle')
      .attr('fill', function (d) {
        var dist = distance[d.id];
        return dist === undefined ? typeMeta(d.type).fill : hopColor(dist);
      });

    this.linkSel
      .classed('reachable', function (d) {
        return litEdges.has(edgeKey(d));
      })
      .classed('dimmed', function (d) {
        return !litEdges.has(edgeKey(d));
      })
      .attr('stroke', function (d) {
        if (!litEdges.has(edgeKey(d))) return null; // fall back to CSS
        var s = typeof d.source === 'object' ? d.source.id : d.source;
        return hopColor(distance[s] + 1);
      })
      .attr('stroke-width', function (d) {
        return litEdges.has(edgeKey(d)) ? 2.5 : 1.25;
      });

    if (this.options.onSelect) {
      this.options.onSelect(originId, result);
    }
  };

  function edgeKey(d) {
    var s = typeof d.source === 'object' ? d.source.id : d.source;
    var t = typeof d.target === 'object' ? d.target.id : d.target;
    return s + '|' + t;
  }

  BlastRadiusGraph.prototype._resize = function () {
    if (!this._built || !this.scenario) return;
    var dims = this._dims();
    this.d3.select(this.svgEl).attr('viewBox', '0 0 ' + dims.width + ' ' + dims.height);
    this.simulation
      .force('center', this.d3.forceCenter(dims.width / 2, dims.height / 2))
      .force('x', this.d3.forceX(dims.width / 2).strength(0.05))
      .force('y', this.d3.forceY(dims.height / 2).strength(0.05))
      .alpha(0.3).restart();
  };

  BlastRadiusGraph.prototype.destroy = function () {
    if (this.simulation) this.simulation.stop();
    global.removeEventListener('resize', this._onResize);
    this.d3.select(this.svgEl).selectAll('*').remove();
    this._built = false;
  };

  global.BlastRadiusGraph = BlastRadiusGraph;
})(window);
