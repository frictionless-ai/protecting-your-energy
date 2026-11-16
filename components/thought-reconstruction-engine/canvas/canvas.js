/* Private static library. Source text is never interpreted as HTML. */
(function () {
  'use strict';
  const data = window.TR_DATA || {objects: [], metadata: {}, manifest: {}};
  const objects = data.objects || [], metadata = data.metadata || {}, manifest = data.manifest || {};
  const dims = ['coherence','evidence','originality','usefulness','feasibility','significance','maturity','research_confidence'];
  const controls = {};
  ['sort','type','status','search','review','project','implementation'].forEach(id => controls[id] = document.getElementById(id));
  const cards = document.getElementById('cards'), more = document.getElementById('more');
  let limit = 30;
  function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
  function meta(o) { return metadata[o.id] || {review:'candidate',project:'Unassigned',implementation:{status:'unknown',summary:'Not checked',evidence:[]},acceptance:[],open_questions:[],related:[]}; }
  function mean(o) { return Math.round(dims.reduce((s,d) => s + (o.scores[d] || 0),0) / dims.length); }
  function date(o) { return meta(o).last_seen || o.evidence.map(e => e.date || '').sort().pop() || ''; }
  const speakers = {owner:'Owner',assistant:'AI assistant',peer:'Other person',unknown:'Unknown speaker'};
  function hosted(m) { return m.method === 'hosted-semantic' || m.method === 'hosted-merge'; }
  function base(path) { return String(path || '').split('/').pop(); }
  // Context turns sit beside his quotes and are never counted as evidence.
  function turns(parent,items) {
    const block = el('div','context-block');
    items.forEach(t => { const turn = el('div','context-turn context-'+t.speaker); turn.append(el('span','badge badge-info',speakers[t.speaker] || t.speaker),el('span','evidence-source',' '+(t.date || 'Undated')),el('p','context-text',t.text)); block.append(turn); });
    parent.append(block);
  }
  function list(parent,title,items) { if (!items || !items.length) return; parent.append(el('h3','',title)); const ul = el('ul'); items.forEach(text => ul.append(el('li','',text))); parent.append(ul); }
  function renderCard(o) {
    const m = meta(o), card = el('article','card'); card.id = o.id;
    const head = el('div','card-head');
    head.append(el('span','badge badge-'+(m.review === 'reviewed' ? 'evidence':'caution'),m.review === 'reviewed' ? 'Reviewed':'Candidate'),el('span','badge badge-info',o.type));
    if (m.method === 'hosted-semantic') head.append(el('span','badge badge-caution','AI reconstruction · unreviewed'));
    if (m.method === 'hosted-merge') head.append(el('span','badge badge-caution','AI merge across batches · unreviewed'));
    const replaced = m.reconstruction_source === 'flagged-reading';
    if (replaced) head.append(el('span','badge badge-caution','Reconstruction from a reading with context'));
    card.append(head,el('p','evidence-source',m.project+(date(o) ? ' · '+date(o):'')),el('h2','card-title',o.title),el('p','card-reconstruction',o.reconstruction));
    // A reading of a flagged piece sits beside the reconstruction; it is an interpretation, never evidence.
    Object.entries(m.readings || {}).filter(([k]) => !(replaced && m.evidence_keys.includes(k))).sort(([a],[b]) => a.localeCompare(b)).forEach(([, r]) => {
      card.append(el('p','context-note','Reading with context · AI interpretation, not evidence'),el('p','card-reconstruction',r.reading),el('p','evidence-source','Anchored to his words: “'+r.anchor+'”'));
    });
    const details = el('details','thought-detail');
    details.append(el('summary','','Explore evidence & next steps · '+o.evidence.length+' fragment'+(o.evidence.length === 1 ? '':'s')));
    const body = el('div','detail');
    body.append(el('h3','','Next action'),el('p','',m.next_action || 'Review this candidate.'));
    list(body,'Acceptance',m.acceptance);
    body.append(el('h3','','Implementation evidence'),el('p','research-status',m.implementation.status+' — '+m.implementation.summary));
    if (m.implementation.scope) body.append(el('p','evidence-source','Scope: '+m.implementation.scope+' · HEAD '+m.implementation.head),el('p','',m.implementation.limit));
    (m.implementation.evidence || []).forEach(e => body.append(el('p','evidence-source',e.path+(e.line ? ':'+e.line:'')+' · checked '+(e.checked_at || '')),el('pre','research-quote',e.quote)));
    list(body,'Open questions',m.open_questions);
    list(body,'Critique',(o.critique || []).map(c => c.date+' — '+c.finding));
    list(body,'Evolution',(o.evolution || []).map(e => e.date+' · '+e.kind+' — '+e.note));
    const att = m.attachments || {context:[],exchanges:[],replies:[],related:[]};
    const where = {}; att.context.concat(att.replies).forEach(c => where[c.source+'\u0000'+c.ref] = c);
    body.append(el('h3','','Original evidence'));
    o.evidence.forEach(e => {
      const c = where[e.source+'\u0000'+(e.ref || '')], source = el('p','evidence-source',(e.date || 'Undated')+' · '+((c && c.label) || base(e.source)));
      source.title = e.source+' · '+(e.ref || '');
      body.append(el('blockquote','evidence-quote',e.quote),source);
      if (c && c.turns.length) { body.append(el('p','context-note','Context · not counted as evidence')); turns(body,c.turns); }
    });
    if (att.replies.length) {
      body.append(el('h3','','His short replies'));
      att.replies.forEach(r => { body.append(el('span','badge badge-evidence','Owner reply'),el('blockquote','evidence-quote',r.quote),el('p','evidence-source',(r.date || 'Undated')+' · '+(r.label || base(r.source)))); if (r.turns.length) { body.append(el('p','context-note','Context · not counted as evidence')); turns(body,r.turns); } });
    }
    if (att.exchanges.length) {
      const quotes = {}; o.evidence.forEach(e => quotes[e.source+'\u0000'+(e.ref || '')] = e.quote); att.replies.forEach(r => quotes[r.source+'\u0000'+r.ref] = r.quote);
      body.append(el('h3','','AI proposals he answered'));
      att.exchanges.forEach(x => { const pair = el('div','exchange'); pair.append(el('span','badge badge-caution','Endorsement: '+x.endorsement+(x.endorsement_source ? ' · AI reading, not a review' : ''))); turns(pair,[x.proposal]); pair.append(el('span','badge badge-evidence','Owner reply'),el('blockquote','evidence-quote',quotes[x.reply.source+'\u0000'+x.reply.ref] || '')); if (x.anchor) pair.append(el('p','evidence-source','Anchored to his words: “'+x.anchor.quote+'”'+(x.change ? ' · change: “'+x.change+'”' : ''))); body.append(pair); });
    }
    if (o.outlet) body.append(el('h3','','Suggested destination'),el('p','',o.outlet.suggested+' — '+o.outlet.note));
    const scores = el('details'); scores.append(el('summary','','Eight dimensions · '+(m.score_method || 'historical estimates')),el('p','','Estimates describe the artifact. They are not verified measures of truth, novelty or your worth. Zero research confidence means no independent research.'));
    const table = el('table'); dims.forEach(d => { const tr = el('tr'); const value = d === 'originality' && m.review === 'reviewed' && o.scores[d] === 0 ? 'Unassessed' : String(o.scores[d]); tr.append(el('th','',d.replaceAll('_',' ')),el('td','',value)); table.append(tr); }); scores.append(table); body.append(scores);
    // Links are {id, reason} or plain reviewed ids; neither claims the same idea.
    const related = (att.related || m.related || []).map(r => typeof r === 'string' ? {id:r,reason:'Reviewed link'} : r).map(r => ({r, other:objects.find(x => x.id === r.id)})).filter(x => x.other);
    if (related.length) { body.append(el('h3','','Related thoughts · possible connections')); related.forEach(({r,other}) => { const a = el('a','related-link',other.title); a.href = '#'+other.id; body.append(a,el('p','evidence-source',r.reason || '')); }); }
    if (m.review === 'reviewed' || hosted(m)) {
      const download = el('a','toggle','Save private task brief');
      download.href = '../tasks/'+o.id+'.md'; download.download = o.id+'.md';
      body.append(download,el('p','evidence-source','The saved brief contains private source quotations.'));
    }
    details.append(body); card.append(details);
    details.addEventListener('toggle',() => card.classList.toggle('is-expanded',details.open));
    return card;
  }
  function render() {
    const q = controls.search.value.trim().toLocaleLowerCase();
    let shown = objects.filter(o => {
      const m = meta(o);
      if (controls.review.value === 'semantic' ? !hosted(m) : controls.review.value !== 'all' && m.review !== controls.review.value) return false;
      if (controls.review.value === 'candidate' && m.covered_by) return false;
      if (controls.project.value !== 'all' && m.project !== controls.project.value) return false;
      if (controls.type.value !== 'all' && o.type !== controls.type.value) return false;
      if (controls.status.value !== 'all' && o.status !== controls.status.value) return false;
      if (controls.implementation.value !== 'all' && m.implementation.status !== controls.implementation.value) return false;
      return !q || [o.title,o.reconstruction,m.project,m.next_action,...o.evidence.map(e => e.quote)].join(' ').toLocaleLowerCase().includes(q);
    });
    const sort = controls.sort.value;
    shown.sort((a,b) => sort === 'recent' ? date(b).localeCompare(date(a)) || a.id.localeCompare(b.id) : sort === 'recurrence' ? b.evidence.length-a.evidence.length : sort === 'composite' ? mean(b)-mean(a) : b.scores[sort]-a.scores[sort]);
    cards.replaceChildren(); shown.slice(0,limit).forEach(o => cards.append(renderCard(o)));
    if (!shown.length) cards.append(el('p','empty',objects.length ? 'No thoughts match these filters. Try Everything or clear the search.':'No library loaded. Build the library to create data.js; sample content is never substituted.'));
    document.getElementById('count').textContent = Math.min(limit,shown.length)+' shown · '+shown.length+' matches · '+objects.length+' total'; more.hidden = shown.length <= limit;
  }
  [...new Set(objects.map(o => meta(o).project))].sort().forEach(p => { const option = el('option','',p); option.value = p; controls.project.append(option); });
  if (!objects.some(o => meta(o).review === 'reviewed')) controls.review.value = 'candidate';
  Object.values(controls).forEach(c => c.addEventListener(c.id === 'search' ? 'input':'change',() => { limit = 30; render(); }));
  more.addEventListener('click',() => { limit += 30; render(); });
  document.getElementById('meta').textContent = (manifest.reviewed || 0)+' reviewed · '+(manifest.fragments || 0)+' preserved fragments · built '+(data.generated || 'not yet');
  const coverage = document.getElementById('coverage-body'); coverage.append(el('p','',manifest.coverage || 'Coverage unavailable for this legacy build.'));
  list(coverage,'Processing',[manifest.inference || 'Inference mode not recorded',...(manifest.limitations || [])]);
  list(coverage,'Sources',(manifest.sources || []).map(s => s.path+' — '+s.accepted+' accepted; '+Object.entries(s.excluded || {}).map(([k,v]) => k+': '+v).join(', ')));
  function navigateHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const found = objects.find(o => o.id === id); if (!found) { render(); return; }
    cards.replaceChildren(renderCard(found)); more.hidden = true;
    document.getElementById('count').textContent = 'Focused thought · '+found.title;
    const card = document.getElementById(id); card.querySelector('details').open = true; card.querySelector('summary').focus(); card.scrollIntoView({block:'start'});
  }
  window.addEventListener('hashchange',navigateHash);
  document.addEventListener('keydown',e => { if (e.key === '/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)) { e.preventDefault(); controls.search.focus(); } if (e.key === 'Escape') document.querySelectorAll('.thought-detail[open]').forEach(d => d.open = false); });
  render(); if (location.hash) navigateHash();
})();
