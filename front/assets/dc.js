/* Static runtime for the Crestpoint / QuantumPulse pages.
   The pages were authored as components: a template (<template id="dc-tpl">) with
   {{ path }} placeholders, <sc-for list as> and <sc-if value>, and a logic class
   (script[data-dc-script]) that extends DCLogic and returns its values from renderVals().
   This file compiles the template to Preact vnodes and mounts the class. */
(function () {
  'use strict';
  var P = window.preact, h = P.h, Fragment = P.Fragment;
  var ONE = /^\s*\{\{([\s\S]*?)\}\}\s*$/, ANY = /\{\{([\s\S]*?)\}\}/g;

  function lookup(scope, path) {
    path = path.trim();
    if (path === 'true') return true;
    if (path === 'false') return false;
    if (path === 'null') return null;
    if (/^-?\d+(\.\d+)?$/.test(path)) return +path;
    var v = scope, ks = path.split('.');
    for (var i = 0; i < ks.length; i++) { if (v == null) return undefined; v = v[ks[i]]; }
    return v;
  }
  function text(v) { return v == null || v === false ? '' : String(v); }
  function interp(str) {
    var one = str.match(ONE);
    if (one) { var p = one[1]; return function (s) { return lookup(s, p); }; }
    if (str.indexOf('{{') < 0) return function () { return str; };
    return function (s) { return str.replace(ANY, function (_, p) { return text(lookup(s, p)); }); };
  }

  function compileChildren(node) {
    var out = [];
    for (var c = node.firstChild; c; c = c.nextSibling) { var f = compile(c); if (f) out.push(f); }
    return function (s) { var r = []; for (var i = 0; i < out.length; i++) r.push(out[i](s)); return r; };
  }

  function compile(node) {
    if (node.nodeType === 3) {
      var t = node.data;
      if (t.indexOf('{{') < 0) return function () { return t; };
      var f = interp(t);
      return function (s) { var v = f(s); return text(v); };
    }
    if (node.nodeType !== 1) return null;
    var tag = node.localName;
    if (tag === 'script') return null;
    if (tag === 'sc-for') {
      var list = interp(node.getAttribute('list') || ''), as = node.getAttribute('as') || 'item';
      var kids = compileChildren(node);
      return function (s) {
        var L = list(s); if (!L) return null;
        if (!Array.isArray(L)) L = Object.keys(L).map(function (k) { return L[k]; });
        return L.map(function (item, i) {
          var sc = Object.create(s); sc[as] = item;
          return h(Fragment, { key: i }, kids(sc));
        });
      };
    }
    if (tag === 'sc-if') {
      var cond = interp(node.getAttribute('value') || '');
      var kids2 = compileChildren(node);
      return function (s) { return cond(s) ? kids2(s) : null; };
    }
    var attrs = [];
    var isField = (tag === 'input' && !/^(checkbox|radio|file|submit|button)$/i.test(node.getAttribute('type') || '')) || tag === 'textarea';
    for (var i = 0; i < node.attributes.length; i++) {
      var a = node.attributes[i], name = a.name;
      if (name.indexOf('hint-placeholder') === 0) continue;
      var low = name.toLowerCase();
      if (low.slice(0, 2) === 'on') {
        // React semantics: onChange on text/range fields fires on every input; onFocus/onBlur bubble.
        if (low === 'onchange' && isField) name = 'oninput';
        else if (low === 'onfocus') name = 'onfocusin';
        else if (low === 'onblur') name = 'onfocusout';
        else name = low;
      }
      attrs.push([name, interp(a.value)]);
    }
    var kids3 = compileChildren(node);
    return function (s) {
      var props = {};
      for (var j = 0; j < attrs.length; j++) {
        var v = attrs[j][1](s), n = attrs[j][0];
        if (v == null) continue;
        if (v === false && n.slice(0, 5) !== 'aria-' && n.slice(0, 5) !== 'data-') continue;
        props[n] = v;
      }
      return h(tag, props, kids3(s));
    };
  }

  function DCLogic(props) { P.Component.call(this, props); }
  DCLogic.prototype = Object.create(P.Component.prototype);
  DCLogic.prototype.constructor = DCLogic;
  DCLogic.prototype.render = function () {
    return h(Fragment, null, window.__dcRender(this.renderVals ? this.renderVals() : {}));
  };
  window.DCLogic = DCLogic;

  function boot() {
    var tpl = document.getElementById('dc-tpl');
    var sc = document.querySelector('script[data-dc-script]');
    var root = document.getElementById('dc-root');
    if (!tpl || !sc || !root) return;
    window.__dcRender = compileChildren(tpl.content);
    var Component = new Function('DCLogic', sc.textContent + '\n;return Component;')(DCLogic);
    var props = {};
    try {
      var spec = JSON.parse(sc.getAttribute('data-props') || '{}');
      Object.keys(spec).forEach(function (k) { if (k[0] !== '$' && spec[k] && 'default' in spec[k]) props[k] = spec[k]['default']; });
    } catch (e) {}
    var q = /[?&]motion=(full|still)/.exec(location.search); if (q) props.motion = q[1];
    root.textContent = '';
    P.render(h(Component, props), root);
    document.documentElement.classList.add('dc-ready');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
