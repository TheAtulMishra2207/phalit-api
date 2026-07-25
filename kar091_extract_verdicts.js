// KAR-091 · Yoga verdict extractor v5 — scoped, provenanced, all-or-nothing,
// fingerprinted.
//
// v5 (QA v6 corrections):
//  - WRAPPER EXPRESSION RECONSTRUCTION: for a wrapper like
//      const ry = (v, cond, res=DEFAULT, src='') => add(..., res + (src ? ` [${src}]` : ''))
//    every call site substitutes its actual arguments into the wrapper's add()
//    expressions and resolves the COMPLETE runtime verdict (res + citation),
//    not a single parameter. Both conditional branches are emitted.
//  - CHART-TOKEN ROOTS RESTRICTED: a dynamic hole is a chart token only when
//    its expression is rooted in approved chart data (planets/houses/lagna),
//    a runtime-bound parameter, or a declaration chain of such. Method calls
//    are limited to an explicit operation set on approved roots. An authored
//    array/literal root (['harm'].join('')) THROWS.
//  - ENTRY IDENTITY FINGERPRINTS: every ⟨dyn⟩ substitution records the exact
//    normalized source of the hole expression. Entry identity = text + those
//    fingerprints, so ANY change inside a dynamic hole invalidates the stored
//    disposition even when the resolved text is unchanged.
//  - DESC CORPUS: desc operands are safety-classified at runtime, so they are
//    audited like verdicts (kind 'desc'), with BOTH branches of any
//    conditional expanded. Unknown desc wording lands in REVIEW_REQUIRED.
const fs = require('fs');
const crypto = require('crypto');
const acorn = require('acorn');

const COLLECTORS = ['collectMaleficYogas', 'collectBeneficYogas'];
const MIN_PLAUSIBLE_VERDICTS = 600;
const MIN_PER_COLLECTOR = { collectMaleficYogas: 250, collectBeneficYogas: 250 };
const REQUIRED_FIXTURES = [
  'Vulnerable to epilepsy', 'Dumb or speechless', 'terrorist or assassin', 'Underground confinement',
];
const ACCESSOR_ALLOWLIST = new Set(['lordOf', 'lord', 'myHouse', 'myConjunct', 'myAspectsHouse', 'mySign', 'countInSI']);
const CHART_ROOTS = new Set(['planets', 'houses', 'lagna']);
const METHOD_ALLOWLIST = new Set(['join', 'filter', 'includes', 'map', 'some', 'every', 'indexOf', 'slice', 'toFixed', 'toString', 'trim', 'find']);
const DYN = '\u27e8dyn\u27e9';
const PRODUCT_CAP = 200;

class ExtractionError extends Error {}

function getInlineScriptWithCollectors(html) {
  const blocks = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const block = blocks.find(b => COLLECTORS.every(c => b.includes('function ' + c)));
  if (!block) throw new ExtractionError('collector functions not found in any inline script');
  return block;
}
function parse(code) {
  try { return acorn.parse(code, { ecmaVersion: 'latest' }); }
  catch (e) { throw new ExtractionError('acorn parse failed: ' + e.message); }
}
function findFunction(ast, name) {
  let found = null;
  (function w(n) {
    if (!n || typeof n !== 'object' || found) return;
    if (n.type === 'FunctionDeclaration' && n.id && n.id.name === name) { found = n; return; }
    for (const k in n) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = n[k]; if (v && typeof v === 'object') w(v); }
  })(ast);
  return found;
}

// ── scope ────────────────────────────────────────────────────────────────────
function collectScope(fnNode, src) {
  const strings = new Map();
  const rowTables = new Map();
  const declInit = new Map();
  const paramNames = new Set();
  (function w(n) {
    if (!n || typeof n !== 'object') return;
    if ((n.type === 'FunctionDeclaration' || n.type === 'ArrowFunctionExpression' || n.type === 'FunctionExpression') && n.params) {
      for (const prm of n.params) {
        if (prm.type === 'Identifier') paramNames.add(prm.name);
        if (prm.type === 'AssignmentPattern' && prm.left.type === 'Identifier') {
          paramNames.add(prm.left.name);
          try { strings.set(prm.left.name, resolveOne(prm.right, { strings, src }, 'param-default')); } catch {}
        }
      }
    }
    if (n.type === 'VariableDeclarator' && n.id && n.id.type === 'Identifier' && n.init) {
      declInit.set(n.id.name, n.init);
      if (n.init.type === 'Literal' && typeof n.init.value === 'string') strings.set(n.id.name, n.init.value);
      else if (n.init.type === 'ArrayExpression' || n.init.type === 'ObjectExpression') rowTables.set(n.id.name, n.init);
    }
    for (const k in n) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = n[k]; if (v && typeof v === 'object') w(v); }
  })(fnNode);
  return { strings, rowTables, declInit, paramNames, src };
}

// ── chart-token policy (root-restricted) ─────────────────────────────────────
function rootOf(ex) {
  let n = ex;
  for (;;) {
    if (!n) return null;
    if (n.type === 'ChainExpression') { n = n.expression; continue; }
    if (n.type === 'MemberExpression') { n = n.object; continue; }
    if (n.type === 'CallExpression') { n = n.callee; continue; }
    return n;
  }
}
function isChartTokenExpr(ex, scope, seen) {
  if (!ex) return false;
  seen = seen || new Set();
  switch (ex.type) {
    case 'Literal': return true;
    case 'ChainExpression': return isChartTokenExpr(ex.expression, scope, seen);
    case 'UnaryExpression': return isChartTokenExpr(ex.argument, scope, seen);
    case 'BinaryExpression': case 'LogicalExpression':
      return isChartTokenExpr(ex.left, scope, seen) && isChartTokenExpr(ex.right, scope, seen);
    case 'ConditionalExpression':
      return isChartTokenExpr(ex.consequent, scope, seen) && isChartTokenExpr(ex.alternate, scope, seen);
    case 'MemberExpression': {
      const r = rootOf(ex);
      return !!r && r.type === 'Identifier' && isApprovedRoot(r.name, scope, seen);
    }
    case 'CallExpression': {
      if (ex.callee.type === 'Identifier') return ACCESSOR_ALLOWLIST.has(ex.callee.name);
      if (ex.callee.type === 'MemberExpression' || ex.callee.type === 'ChainExpression') {
        const calleeM = ex.callee.type === 'ChainExpression' ? ex.callee.expression : ex.callee;
        const method = calleeM.property && (calleeM.property.name || calleeM.property.value);
        if (!METHOD_ALLOWLIST.has(method)) return false;
        const r = rootOf(calleeM.object);
        return !!r && r.type === 'Identifier' && isApprovedRoot(r.name, scope, seen);
      }
      return false;   // authored roots like ['harm'].join('') are NOT chart tokens
    }
    case 'Identifier': return isApprovedRoot(ex.name, scope, seen);
    default: return false;
  }
}
function isApprovedRoot(name, scope, seen) {
  if (CHART_ROOTS.has(name)) return true;
  if (scope.paramNames && scope.paramNames.has(name)) return true;
  if (seen.has(name)) return false;
  seen.add(name);
  const init = scope.declInit && scope.declInit.get(name);
  return !!init && isChartTokenExpr(init, scope, seen);
}

function logDyn(ctx, scope, ex) {
  if (ctx && ctx.dynLog && scope.src) ctx.dynLog.push(scope.src.slice(ex.start, ex.end).replace(/\s+/g, ' ').trim());
  return DYN;
}

// ── strict single resolution ─────────────────────────────────────────────────
function resolveOne(node, scope, where, ctx) {
  if (!node) throw new ExtractionError(`missing node at ${where}`);
  if (node.type === 'Literal' && typeof node.value === 'string') return node.value;
  if (node.type === 'TemplateLiteral') {
    let out = '';
    node.quasis.forEach((q, i) => {
      out += q.value.cooked || '';
      if (i < node.expressions.length) {
        const ex = node.expressions[i];
        let piece = null;
        try { piece = resolveOne(ex, scope, where, ctx); } catch { piece = null; }
        if (piece != null) out += piece;
        else if (ctx && ex.type === 'Identifier' && ctx.env && ctx.env.has(ex.name)) out += ctx.env.get(ex.name)[0];
        else if (ctx && ex.type === 'Identifier' && ctx.bindings && ctx.bindings.has(ex.name)) out += ctx.bindings.get(ex.name)[0];
        else if (ctx && ex.type === 'Identifier' && ctx.tokens && ctx.tokens.has(ex.name)) out += logDyn(ctx, scope, ex);
        else if (isChartTokenExpr(ex, scope)) out += logDyn(ctx, scope, ex);
        else if (ctx && ctx.nonVerdict) out += logDyn(ctx, scope, ex);
        else throw new ExtractionError(
          `template hole (${ex.type}${ex.type === 'Identifier' ? ' ' + ex.name : ''}) at ${where} offset ${ex.start} ` +
          `is neither statically resolvable nor an approved chart token`);
      }
    });
    return out;
  }
  if (node.type === 'BinaryExpression' && node.operator === '+') {
    return resolveOne(node.left, scope, where, ctx) + resolveOne(node.right, scope, where, ctx);
  }
  if (node.type === 'Identifier') {
    if (ctx && ctx.env && ctx.env.has(node.name)) return ctx.env.get(node.name)[0];
    if (scope.strings.has(node.name)) return scope.strings.get(node.name);
    if (ctx && ctx.bindings && ctx.bindings.has(node.name)) return ctx.bindings.get(node.name)[0];
    if (ctx && ctx.tokens && ctx.tokens.has(node.name)) return logDyn(ctx, scope, node);
    if (scope.declInit && scope.declInit.has(node.name)) {
      const seen = (ctx && ctx.seen) || new Set();
      if (!seen.has(node.name)) {
        seen.add(node.name);
        return resolveOne(scope.declInit.get(node.name), scope, where + ':decl(' + node.name + ')', { ...(ctx || {}), seen });
      }
    }
    if (ctx && ctx.nonVerdict) return logDyn(ctx, scope, node);
    throw new ExtractionError(`identifier '${node.name}' at ${where} offset ${node.start} has no static string binding`);
  }
  if (ctx && ctx.nonVerdict) {
    if (node.type === 'ConditionalExpression') {
      try { return resolveOne(node.consequent, scope, where + ':cons', ctx); }
      catch { return resolveOne(node.alternate, scope, where + ':alt', ctx); }
    }
    return logDyn(ctx, scope, node);
  }
  throw new ExtractionError(`unresolvable ${node.type} at ${where} offset ${node.start}`);
}

// ── multi resolution ─────────────────────────────────────────────────────────
// Verdict positions: strict. Non-verdict positions (nonVerdict ctx): permissive
// dyn stand-ins BUT conditionals still expand BOTH branches — every runtime
// variant of a safety-classified field is emitted.
function resolveMulti(node, scope, where, ctx) {
  const B = ctx && ctx.bindings, T = ctx && ctx.tokens, E = ctx && ctx.env;
  if (node.type === 'ConditionalExpression') {
    return [...resolveMulti(node.consequent, scope, where + ':cons', ctx),
            ...resolveMulti(node.alternate, scope, where + ':alt', ctx)];
  }
  if (node.type === 'Identifier') {
    if (E && E.has(node.name)) return E.get(node.name);
    if (B && B.has(node.name)) return B.get(node.name);
    if (scope.strings.has(node.name)) return [scope.strings.get(node.name)];
    if (scope.rowTables.has(node.name)) return containerValues(scope.rowTables.get(node.name), scope, where + ':' + node.name, ctx);
    if (scope.declInit && scope.declInit.has(node.name)) {
      const seen = (ctx && ctx.seen) || new Set();
      if (!seen.has(node.name)) {
        seen.add(node.name);
        return resolveMulti(scope.declInit.get(node.name), scope, where + ':decl(' + node.name + ')', { ...(ctx || {}), seen });
      }
    }
    return [resolveOne(node, scope, where, ctx)];
  }
  if (node.type === 'MemberExpression' && node.object && node.object.type === 'Identifier'
      && scope.rowTables.has(node.object.name)) {
    return containerValues(scope.rowTables.get(node.object.name), scope, where + ':' + node.object.name, ctx);
  }
  if (node.type === 'TemplateLiteral') {
    let prefixes = [''];
    node.quasis.forEach((q, i) => {
      prefixes = prefixes.map(p => p + (q.value.cooked || ''));
      if (i < node.expressions.length) {
        const ex = node.expressions[i];
        let values;
        try { values = [resolveOne(ex, scope, where, { ...(ctx || {}), nonVerdict: false, dynLog: null })]; }
        catch {
          if (E && ex.type === 'Identifier' && E.has(ex.name)) values = E.get(ex.name);
          else if (B && ex.type === 'Identifier' && B.has(ex.name)) values = B.get(ex.name);
          else if (T && ex.type === 'Identifier' && T.has(ex.name)) values = [logDyn(ctx, scope, ex)];
          else if (isChartTokenExpr(ex, scope)) values = [logDyn(ctx, scope, ex)];
          else if (ctx && ctx.nonVerdict) values = [logDyn(ctx, scope, ex)];
          else throw new ExtractionError(
            `template hole (${ex.type}${ex.type === 'Identifier' ? ' ' + ex.name : ''}) at ${where} offset ${ex.start} ` +
            `is neither statically resolvable nor an approved chart token`);
        }
        const next = [];
        for (const p of prefixes) for (const v of values) { next.push(p + v); if (next.length > PRODUCT_CAP) throw new ExtractionError(`template expansion exceeds ${PRODUCT_CAP} at ${where}`); }
        prefixes = next;
      }
    });
    return prefixes;
  }
  if (node.type === 'BinaryExpression' && node.operator === '+') {
    const L = resolveMulti(node.left, scope, where + ':L', ctx);
    const R = resolveMulti(node.right, scope, where + ':R', ctx);
    const out = [];
    for (const l of L) for (const r of R) { out.push(l + r); if (out.length > PRODUCT_CAP) throw new ExtractionError(`concat expansion exceeds ${PRODUCT_CAP} at ${where}`); }
    return out;
  }
  return [resolveOne(node, scope, where, ctx)];
}
const resolveVerdict = resolveMulti;   // verdicts: same engine, strict ctx (no nonVerdict flag)

function containerValues(node, scope, where, ctx) {
  const out = [];
  if (node.type === 'ArrayExpression') {
    node.elements.forEach((e, i) => { out.push(resolveOne(e, scope, `${where}[${i}]`, ctx)); });
  } else if (node.type === 'ObjectExpression') {
    node.properties.forEach((p, i) => {
      if (!p || !p.value) throw new ExtractionError(`container ${where} has non-value property at index ${i}`);
      out.push(resolveOne(p.value, scope, `${where}.${p.key && (p.key.name || p.key.value)}`, ctx));
    });
  } else {
    throw new ExtractionError(`container ${where} is ${node.type}, not array/object`);
  }
  return out;
}

function tableBindings(n, scope) {
  const bindings = new Map();
  if (!(n.type === 'CallExpression' && n.callee && n.callee.type === 'MemberExpression'
        && n.callee.property && n.callee.property.name === 'forEach'
        && n.arguments[0] && (n.arguments[0].type === 'ArrowFunctionExpression' || n.arguments[0].type === 'FunctionExpression')
        && n.arguments[0].params[0])) return null;
  let tableNode = null;
  if (n.callee.object.type === 'ArrayExpression') tableNode = n.callee.object;
  else if (n.callee.object.type === 'Identifier' && scope.rowTables.has(n.callee.object.name)) tableNode = scope.rowTables.get(n.callee.object.name);
  if (!tableNode) return null;
  const param = n.arguments[0].params[0];
  const tokens = new Set();
  function columnVals(getter, name) {
    const vals = []; let nonString = 0;
    for (const row of tableNode.elements) {
      const cell = getter(row);
      if (cell == null) continue;
      try { vals.push(resolveOne(cell, scope, `table:${name}`)); }
      catch { nonString++; }
    }
    if (vals.length) bindings.set(name, vals);
    else if (nonString) tokens.add(name);
  }
  if (param.type === 'ArrayPattern') {
    param.elements.forEach((el, idx) => {
      if (el && el.type === 'Identifier')
        columnVals(row => (row && row.type === 'ArrayExpression') ? row.elements[idx] : null, el.name);
    });
  } else if (param.type === 'ObjectPattern') {
    for (const prop of param.properties) {
      if (!prop.key || prop.key.type !== 'Identifier') continue;
      columnVals(row => {
        if (!row || row.type !== 'ObjectExpression') return null;
        const rp = row.properties.find(x => x.key && (x.key.name === prop.key.name || x.key.value === prop.key.name));
        return rp ? rp.value : null;
      }, prop.key.name);
    }
  }
  return (bindings.size || tokens.size) ? { bindings, tokens } : null;
}

// ── wrappers: full expression dependency resolution ──────────────────────────
// A wrapper is const NAME = (params) => ...add(catE, nameE, descE, verdictE).
// At each call site we bind params to the caller's arguments (or defaults) and
// resolve the wrapper's OWN argument expressions under that environment. The
// verdict expression is resolved strictly; desc/name/cat with nonVerdict
// permissiveness. This reconstructs res + (src ? ` [${src}]` : '') completely.
function findWrappers(fnNode, scope) {
  const wrappers = new Map();
  (function w(n) {
    if (!n || typeof n !== 'object') return;
    if (n.type === 'VariableDeclarator' && n.id && n.id.type === 'Identifier' && n.init
        && (n.init.type === 'ArrowFunctionExpression' || n.init.type === 'FunctionExpression')) {
      const fn = n.init;
      let addCall = null;
      (function inner(m) {
        if (!m || typeof m !== 'object' || addCall) return;
        if (m.type === 'CallExpression' && m.callee && m.callee.name === 'add' && m.arguments.length >= 3) addCall = m;
        for (const k in m) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = m[k]; if (v && typeof v === 'object') inner(v); }
      })(fn.body);
      if (!addCall) return;
      const params = fn.params.map(prm => ({
        name: prm.type === 'AssignmentPattern' ? prm.left.name : (prm.type === 'Identifier' ? prm.name : null),
        defaultNode: prm.type === 'AssignmentPattern' ? prm.right : null,
      }));
      // params that feed the verdict expression must resolve strictly at call
      // sites; the rest (conditions/descriptions) resolve with nonVerdict rules
      const verdictParams = new Set();
      (function ids(m) { if (!m || typeof m !== 'object') return;
        if (m.type === 'Identifier') verdictParams.add(m.name);
        for (const k in m) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = m[k]; if (v && typeof v === 'object') ids(v); } })(addCall.arguments[addCall.arguments.length - 1]);
      wrappers.set(n.id.name, { params, addCall, verdictParams });
    }
    for (const k in n) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = n[k]; if (v && typeof v === 'object') w(v); }
  })(fnNode);
  return wrappers;
}

function wrapperEnv(wrapper, callNode, scope, ctxBase, fnName) {
  const env = new Map();
  wrapper.params.forEach((p, i) => {
    if (!p.name) return;
    const strict = wrapper.verdictParams.has(p.name);
    const ctx = { ...ctxBase, env: null, nonVerdict: !strict };
    const arg = callNode.arguments[i];
    let values;
    if (arg != null) {
      values = resolveMulti(arg, scope, `${fnName}:wrapperArg(${p.name})@${arg.start}`, ctx);
    } else if (p.defaultNode != null) {
      values = resolveMulti(p.defaultNode, scope, `${fnName}:wrapperDefault(${p.name})`, ctx);
    } else {
      values = [''];
    }
    env.set(p.name, values);
  });
  return env;
}

// ── main extraction ──────────────────────────────────────────────────────────
function pushEntries(out, texts, fn, start, kind, dynLog) {
  const dyn = (dynLog && dynLog.length) ? [...dynLog] : [];
  for (const text of texts) {
    if (text.trim().length >= 8) {
      const identity = text.trim() + (dyn.length ? '\u0000' + dyn.join('\u0001') : '');
      out.push({ text, identity, dyn, fn, start, kind });
    }
  }
}

function extractFromCollector(fnNode, fnName, src, out) {
  const scope = collectScope(fnNode, src);
  const wrappers = findWrappers(fnNode, scope);
  let active = null;
  (function w(n) {
    if (!n || typeof n !== 'object') return;
    const tb = (n.type === 'CallExpression') ? tableBindings(n, scope) : null;
    const prev = active; if (tb) active = tb;
    const base = { bindings: active && active.bindings, tokens: active && active.tokens };

    if (n.type === 'CallExpression' && n.callee && n.callee.name === 'add' && n.arguments.length >= 3) {
      const last = n.arguments[n.arguments.length - 1];
      { const dynLog = [];
        pushEntries(out, resolveVerdict(last, scope, `${fnName}:add@${last.start}`, { ...base, dynLog }), fnName, last.start, 'add:' + last.type, dynLog); }
      if (n.arguments.length >= 4) {   // desc is safety-classified: audit it too
        const d = n.arguments[n.arguments.length - 2];
        const dynLog = [];
        pushEntries(out, resolveMulti(d, scope, `${fnName}:desc@${d.start}`, { ...base, nonVerdict: true, dynLog }), fnName, d.start, 'desc:' + d.type, dynLog);
      }
    }
    if (n.type === 'ArrayExpression' && n.elements.length >= 3 &&
        n.elements[0] && n.elements[0].type === 'ArrayExpression' &&
        n.elements[2] && (n.elements[2].type === 'Literal' || n.elements[2].type === 'BinaryExpression' || n.elements[2].type === 'TemplateLiteral')) {
      const dynLog = [];
      pushEntries(out, resolveVerdict(n.elements[2], scope, `${fnName}:row@${n.elements[2].start}`, { ...base, dynLog }), fnName, n.elements[2].start, 'row:' + n.elements[2].type, dynLog);
    }
    if (n.type === 'CallExpression' && n.callee && n.callee.type === 'Identifier' && wrappers.has(n.callee.name)) {
      const wr = wrappers.get(n.callee.name);
      const env = wrapperEnv(wr, n, scope, base, fnName);
      const wArgs = wr.addCall.arguments;
      { const dynLog = [];
        const vLast = wArgs[wArgs.length - 1];
        pushEntries(out, resolveVerdict(vLast, scope, `${fnName}:${n.callee.name}@${n.start}:verdict`, { ...base, env, dynLog }), fnName, n.start, 'wrapper:' + n.callee.name, dynLog); }
      if (wArgs.length >= 4) {
        const dNode = wArgs[wArgs.length - 2];
        const dynLog = [];
        pushEntries(out, resolveMulti(dNode, scope, `${fnName}:${n.callee.name}@${n.start}:desc`, { ...base, env, nonVerdict: true, dynLog }), fnName, n.start, 'wrapper-desc:' + n.callee.name, dynLog);
      }
    }
    for (const k in n) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = n[k]; if (v && typeof v === 'object') w(v); }
    active = prev;
  })(fnNode);
}

function extractVerdicts(htmlPath) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  const sha = crypto.createHash('sha256').update(html).digest('hex');
  const src = getInlineScriptWithCollectors(html);
  const ast = parse(src);
  const raw = [];
  const perCollector = {};
  for (const name of COLLECTORS) {
    const fn = findFunction(ast, name);
    if (!fn) throw new ExtractionError('collector not found in AST: ' + name);
    const before = raw.length;
    extractFromCollector(fn, name, src, raw);
    perCollector[name] = raw.length - before;
  }
  for (const name of COLLECTORS) {
    const floor = MIN_PER_COLLECTOR[name] || 1;
    if ((perCollector[name] || 0) < floor)
      throw new ExtractionError(`collector ${name} yielded ${perCollector[name] || 0} verdicts < ${floor}; appears stubbed, removed, or unparsed`);
  }
  const seen = new Set(); const entries = [];
  for (const r of raw) { if (seen.has(r.identity)) continue; seen.add(r.identity); entries.push(r); }
  if (entries.length < MIN_PLAUSIBLE_VERDICTS)
    throw new ExtractionError(`implausible verdict count ${entries.length} < ${MIN_PLAUSIBLE_VERDICTS}`);
  const texts = entries.map(e => e.text);
  for (const fx of REQUIRED_FIXTURES)
    if (!texts.some(t => t.includes(fx))) throw new ExtractionError(`required corpus fixture missing: ${JSON.stringify(fx)}`);
  return { source_file_sha256: sha, generator_version: '5.0.0-fingerprinted', collectors: COLLECTORS, entries };
}

// Real collector call shapes for the DOM sweep: direct add() calls AND
// wrapper-expanded runtime variants, every argument resolved, every branch of
// desc expanded, verdict axis and desc axis cartesian (capped).
function extractAddCalls(htmlPath) {
  const html = fs.readFileSync(htmlPath, 'utf8');
  const src = getInlineScriptWithCollectors(html);
  const ast = parse(src);
  const calls = [];
  function emit(fn, argLists) {
    let combos = [[]];
    for (const values of argLists) {
      const next = [];
      for (const c of combos) for (const v of values) { next.push([...c, v]); if (next.length > 64) { combos = next; return emitCapped(fn, argLists); } }
      combos = next;
    }
    for (const c of combos) calls.push({ fn, args: c });
  }
  function emitCapped(fn, argLists) {
    // cap blowups: first values for non-verdict axes, full expansion for the last two axes
    const fixed = argLists.slice(0, -2).map(v => [v[0]]);
    const tail = argLists.slice(-2);
    let combos = [[]];
    for (const values of [...fixed, ...tail]) {
      const next = [];
      for (const c of combos) for (const v of values) next.push([...c, v]);
      combos = next.slice(0, 64);
    }
    for (const c of combos) calls.push({ fn, args: c });
  }
  for (const name of COLLECTORS) {
    const fn = findFunction(ast, name);
    if (!fn) throw new ExtractionError('collector not found: ' + name);
    const scope = collectScope(fn, src);
    const wrappers = findWrappers(fn, scope);
    let active = null;
    (function w(n) {
      if (!n || typeof n !== 'object') return;
      const tb = (n.type === 'CallExpression') ? tableBindings(n, scope) : null;
      const prev = active; if (tb) active = tb;
      const base = { bindings: active && active.bindings, tokens: active && active.tokens };
      if (n.type === 'CallExpression' && n.callee && n.callee.name === 'add' && n.arguments.length >= 3) {
        const argLists = n.arguments.map((a, i) =>
          i === n.arguments.length - 1
            ? resolveVerdict(a, scope, `${name}:domarg@${a.start}`, { ...base })
            : resolveMulti(a, scope, `${name}:domarg@${a.start}`, { ...base, nonVerdict: true }));
        emit(name, argLists);
      }
      if (n.type === 'CallExpression' && n.callee && n.callee.type === 'Identifier' && wrappers.has(n.callee.name)) {
        const wr = wrappers.get(n.callee.name);
        const env = wrapperEnv(wr, n, scope, base, name);
        const argLists = wr.addCall.arguments.map((a, i) =>
          i === wr.addCall.arguments.length - 1
            ? resolveVerdict(a, scope, `${name}:${n.callee.name}dom@${n.start}`, { ...base, env })
            : resolveMulti(a, scope, `${name}:${n.callee.name}dom@${n.start}`, { ...base, env, nonVerdict: true }));
        emit(name, argLists);
      }
      for (const k in n) { if (k === 'type' || k === 'start' || k === 'end') continue; const v = n[k]; if (v && typeof v === 'object') w(v); }
      active = prev;
    })(fn);
  }
  return calls;
}

module.exports = { extractVerdicts, extractAddCalls, ExtractionError };

if (require.main === module) {
  const path = process.argv[2] || 'newphalit.html';
  const out = process.argv[3];
  try {
    const m = extractVerdicts(path);
    const kinds = {};
    for (const e of m.entries) { const k = e.kind.split(':')[0]; kinds[k] = (kinds[k] || 0) + 1; }
    if (out) fs.writeFileSync(out, JSON.stringify(m, null, 1));
    console.error(`extracted ${m.entries.length} entries (${JSON.stringify(kinds)}), sha ${m.source_file_sha256.slice(0, 12)}`);
  } catch (e) { console.error('EXTRACTION FAILED (fail-closed): ' + e.message); process.exit(2); }
}
