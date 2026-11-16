#!/usr/bin/env python3
"""Scoped local archive guard. It checks accounting, never semantic completeness."""
import argparse, ast, hashlib, json, os, pathlib, re, shlex, sys, tempfile, time

BASE=pathlib.Path(os.environ.get('ARCHIVE_GUARD_STATE_DIR',str(pathlib.Path.home()/'.local/state/archive-reconstruction')))
PLUGIN_ROOT=pathlib.Path(os.environ.get('PYE_PLUGIN_ROOT',str(pathlib.Path(__file__).resolve().parents[2])))
RULES=os.environ.get('ARCHIVE_RECONSTRUCTION_RULES',str(pathlib.Path(__file__).resolve().with_name('archive-reconstruction-rules.md')))
ARCHIVE_ROOT=os.environ.get('PYE_ARCHIVE_ROOT','the authorized local archive or source roots for this task')
ROUTE='Archive reconstruction is active. Read '+RULES+'; acquire evidence directly from '+ARCHIVE_ROOT+'. Inventory all collections, expand aliases and related contexts, retain detailed source-linked material and account for every discovered source/owner turn. Resource limits require continuation. Do not launch model CLI workers for retrieval unless explicitly requested in this task. Register a reconciled coverage receipt with archive_guard.py --register --receipt PATH before completion. Quote checks do not prove completeness.'
BOUNDED_ROUTE='Bounded context recovery is active. Read '+RULES+'; use the smallest local source/context that actually settles this request, preserve attribution and uncertainty, and when it does not settle the request, expand within the authorized scope rather than guess. Do not infer archive-wide acquisition from a project name or path. No comprehensive coverage receipt is required for this bounded task. Model CLI workers still require an explicit current-task request.'
STOP_MAX_BYTES=8*1024*1024
STOP_MAX_SECONDS=2.0
RECOVER_FIRST=' RECOVER FIRST: before restating, paraphrasing or listing assumptions about this request, recover the missing context (current conversation, named folders and files, project notes, then the archive). Do not write a guessed rewrite or an Assumptions line in its place. Keep the user\'s own verbs and scope: move stays move, all stays all. If the user says they stated it before, find where. Ask only about what recovery could not settle.'
MOMENTUM_ROUTE=' Preserve momentum during this work: apply '+str(PLUGIN_ROOT/'skills/sustain-momentum/SKILL.md')+'. Continue independent authorized work during I/O waits or optional input. Offer one concrete asynchronous question only when its answer could improve the result; do not require a reply for unrelated progress. Recover teaching/examples from context. Reuse a compact task-scoped interaction profile: live purpose, demonstrated knowledge, source-supported helpful exchanges, friction, next action and contrary evidence. Do not rescan Discord synchronously on each prompt. Do not act on a predicted answer that recovery could check; mark any remaining prediction as unverified. Preserve required answers and approvals, and retain the next action across success or a pause. Source-supported interaction hypotheses are revisable; a hook cue does not prove sustained user benefit.'

class ValidationBudget:
    """Cooperative limits, not a wall-clock guarantee across blocked syscalls."""
    def __init__(self,max_bytes=STOP_MAX_BYTES,max_seconds=STOP_MAX_SECONDS):
        self.remaining=max_bytes;self.deadline=time.monotonic()+max_seconds
    def check(self,size=0):
        self.remaining-=size
        if self.remaining<0 or time.monotonic()>self.deadline:
            raise ValueError('Stop validation budget exceeded; accounting incomplete. For a completed packet run --finalize --receipt PATH explicitly for full task-bound validation; --check-receipt alone is read-only. Do not claim completion before successful validation')

def tick(budget):
    if budget is not None:budget.check()

def file_chunks(p,budget=None):
    tick(budget)
    # Reject an oversized regular artifact before reading its payload.
    if budget is not None and pathlib.Path(p).stat().st_size>budget.remaining:
        budget.check(budget.remaining+1)
    with open(p,'rb') as f:
        while True:
            tick(budget)
            size=min(65536,budget.remaining+1) if budget is not None else 65536
            b=f.read(size)
            if budget is not None:budget.check(len(b))
            if not b:break
            yield b

def read_text(p,budget=None):
    text=b''.join(file_chunks(p,budget)).decode('utf-8')
    tick(budget);return text

def digest_file(p,budget=None):
    h=hashlib.sha256()
    for b in file_chunks(p,budget):h.update(b)
    tick(budget);return h.hexdigest()

def recovery_scope(prompt):
    """Conservative lexical routing, not semantic intent/permission detection."""
    # Ignore fenced examples. Paths/product names alone never activate a scope.
    text=re.sub(r'```.*?```','',prompt.lower(),flags=re.S)
    # Drop filesystem paths so ".../kotor_mod_archives" or "~/x_chat_context" cannot match topic nouns.
    text=re.sub(r'\S*(?:boden_wizard_chat_context|ai-conversations)\S*',' archive ',text)
    text=re.sub(r'~/\S*|/[\w.-]+/[\w./-]*|(?<![\w/])\.{0,2}[\w.-]+/[\w./-]*','',text)
    scopes=[];negated=False
    # Original verbs pair with any topic noun. Added verbs are generic, so they need an archive noun.
    core=r'acquire|aggregat\w*|reconstruct|recover|retrieve|search|find|resume|continue'
    extra=r'consolidat\w*|gather|collect|merge|inventory|go through|look (?:at|through)|read|check|scan|review|dig through|comb through|mine|pull up|use (?:/|\$)?thought-reconstruction'
    actions=core+'|'+extra
    lead=r"(?:^\s*|\b(?:please|then|to|you|only|and|also|now|just|first)\s+)(?:(?:also|now|just|first|actually|please)\s+)?"
    strong=r"(?<!zip )(?<!tar )(?<!mod )(?<!rar )archives?\b(?! (?:are|were|files?)\b)|direct messages|\bdms\b|conversations?\b|\bchats\b|\bchat (?:logs?|history|exports?)|transcripts?\b|thought-reconstruction|(?<!git )(?<!shell )(?<!command )histor(?:y|ical)\b"
    weak=r"\bcontext\b(?![./_]\w| menu| window)|\bnotes\b|\bmessages?\b|\bdocumentation\b"
    # Sentence punctuation only: "context.py" and "~/a.b" stay in one clause.
    clauses=re.split(r'[.;!?]+(?=\s|$)|[\n,]+|\bbut\b|\band\s+(?=(?:please\s+)?(?:'+actions+r')\b)',text)
    for clause in clauses:
        negative=re.search(r"\b(?:do not|don't|must not|never|without|no)\b.{0,80}\b(?:acqui[rs]\w*|recover\w*|reconstruct\w*|search\w*|retriev\w*|archive-wide|comprehensive)\b",clause)
        if negative:
            negated=True;clause=clause[:negative.start()]
        has_strong=re.search(strong,clause)
        anchored=bool((re.search(lead+r"(?:"+core+r")\b",clause) and (has_strong or re.search(weak,clause)))
                or (re.search(lead+r"(?:"+extra+r")\b",clause) and has_strong))
        if not (anchored
                # With an archive noun the verb need not open the clause ("in the conversations find ...").
                or (has_strong and re.search(r"\b(?:"+actions+r")\b",clause))):continue
        bounded=bool(re.search(r'\b(?:bounded|single|specific|selected)\b|\bone (?:message|thread|conversation|chat|session|passage|file)\b|\bthis (?:message|thread|conversation|session|passage|file)\b|\b(?:throughout|within|in|during) (?:the|our) (?:current )?(?:conversation|session|chat|thread)\b',clause))
        broad=bool(re.search(r'\b(?:everything|entirety|any and all|thorough(?:ly)?|comprehensive(?:ly)?|exhaustive(?:ly)?|nothing (?:is )?missed)\b|archive-wide|\b(?:all|every|entire|whole)\b.{0,100}\b(?:archives?|history|conversations?|chats|transcripts|documentation|data|sources|collections|messages|notes|project)\b',clause))
        # Comprehensive needs an archive noun somewhere; "all documentation" alone is ordinary repo work.
        if broad and not bounded and anchored and (has_strong or re.search(strong,text)):scopes.append('comprehensive')
        elif not bounded and re.match(r'^\s*(?:please\s+)?(?:continue|resume)\b',clause):scopes.append('continuation')
        else:scopes.append('bounded')
    # A bounded first clause must not erase a later explicit comprehensive search.
    if 'comprehensive' in scopes:return 'comprehensive'
    if 'bounded' in scopes:return 'bounded'
    if scopes:return 'continuation'
    if negated:return 'excluded'
    # "I told you this before" means the answer exists somewhere: recover it, do not guess.
    if re.search(r"\b(?:i|we)(?:'ve| have)?\s+(?:already\s+|previously\s+)?(?:said|told you|mentioned|explained|specified|asked for|discussed|went over)\b.{0,80}\b(?:before|earlier|already|previously|last time|yesterday|another (?:session|chat|conversation))\b|\bas i (?:said|mentioned|explained)\b|\bi (?:already|previously) (?:said|told|mentioned|explained|specified)\b",text):return 'bounded'
    return None

def narrows_task(prompt):
    """Require a replacement/narrowing directive, not just a bounded substep."""
    text=re.sub(r'```.*?```','',prompt.lower(),flags=re.S)
    # Negating a scope change preserves the task; it is not a change directive.
    changes=re.sub(r"\b(?:do not|don't|don’t|must not|never)\s+(?:replace|narrow|limit|switch|change)\b",'',text)
    return bool(re.search(r'\b(?:replace|narrow|limit|switch|change)\b.{0,60}\b(?:task|scope|acquisition|bounded recovery)\b',changes)
        # "Instead, recover ..." replaces work. "Instead of asking ..." does not.
        or re.search(r'(?:^|[.;!?\n])\s*(?:please\s+)?instead\b(?!\s+of\b)|\binstead\s+of\s+(?:(?:this|the|current|comprehensive|archive-wide|original)\s+)*(?:task|scope|acquisition)\b',text)
        or (re.match(r'^\s*(?:please\s+)?(?:only\s+(?:recover|retrieve|search)|(?:recover|retrieve|search)\s+only)\b',text) and not re.search(r'\bfirst\b|\bthen\s+(?:continue|resume)\b',text))
        or re.search(r"\b(?:do not|don't|must not|never)\s+acquire\b",text))

def atomic(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,tmp=tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(obj,f,indent=2);f.write('\n')
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def state_path(sid,host):
    return BASE/(hashlib.sha256((host+':'+sid).encode()).hexdigest()+'.json')

def context(event,text):
    print(json.dumps({'hookSpecificOutput':{'hookEventName':event,'additionalContext':text}}))

def shell_launch(cmd,depth=0):
    if depth>3:return False
    # Remove heredoc bodies: their text is input to a command, not shell executables.
    kept=[];pending=[]
    for line in cmd.splitlines(keepends=True):
        if pending:
            if line.rstrip('\r\n').lstrip('\t')==pending[0]:pending.pop(0)
            continue
        kept.append(line)
        for match in re.finditer(r"<<-?\s*(?:'([^']+)'|\"([^\"]+)\"|([A-Za-z_][A-Za-z_0-9]*))",line):pending.append(next(x for x in match.groups() if x is not None))
    cmd=''.join(kept)
    try:
        lex=shlex.shlex(cmd,posix=False,punctuation_chars=';&|()\n');lex.whitespace_split=True;lex.whitespace=' \t\r';t=list(lex)
    except ValueError:return False
    def unquote(token):
        try:
            values=shlex.split(token);return values[0] if len(values)==1 else token
        except ValueError:return token
    boundary=True;i=0
    while i<len(t):
        token=t[i]
        if token and all(c in ';&|()\n' for c in token):boundary=True;i+=1;continue
        if not boundary:i+=1;continue
        if token in {'command','exec','env','nohup','timeout','setsid'} or re.match(r'^[A-Za-z_][A-Za-z_0-9]*=',token) or (token.replace('.','',1).isdigit()):i+=1;continue
        exe=pathlib.Path(unquote(token)).name
        tail=[]
        for part in t[i+1:]:
            if part and all(c in ';&|()\n' for c in part):break
            tail.append(unquote(part))
        help_only=any(x in {'--help','-h','--version'} for x in tail) or (tail and tail[0]=='help')
        if exe=='codex' and not help_only and ('exec' in tail or 'e' in tail):return True
        if exe=='claude' and not help_only and any(x in {'-p','--print'} or x.startswith('--print=') for x in tail):return True
        if exe in {'bash','sh','zsh','fish'}:
            for j,x in enumerate(tail[:-1]):
                if x.startswith('-') and 'c' in x and shell_launch(tail[j+1],depth+1):return True
        boundary=False;i+=1
    return False

def launch_input(obj):
    if isinstance(obj,str):
        try:return launch_input(json.loads(obj))
        except (ValueError,TypeError):obj={'code':obj}
    if not isinstance(obj,dict):return False
    if any(shell_launch(obj[k]) for k in ('cmd','command') if isinstance(obj.get(k),str)):return True
    # Code-mode exec_command literal arguments. Do not inspect arbitrary source strings.
    code=obj.get('code','')
    if isinstance(code,str):
        for m in re.finditer(r'''\bexec_command\s*\(\s*\{[^{}]{0,2048}?\b(?:cmd|command)\s*:\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')''',code):
            try:
                if shell_launch(ast.literal_eval(m.group(1))):return True
            except (ValueError,SyntaxError):pass
    return False

def checked_ref(ref,budget=None):
    if not isinstance(ref,dict) or not ref.get('path') or not ref.get('sha256'):raise ValueError('missing path/hash reference')
    p=pathlib.Path(ref['path'])
    if not p.is_file():raise ValueError('missing artifact: '+str(p))
    if digest_file(p,budget)!=ref['sha256']:raise ValueError('changed artifact: '+str(p))
    return p

def validate(receipt,task_id,budget=None):
    r=json.loads(read_text(receipt,budget));tick(budget);issues=[]
    if r.get('task_id')!=task_id:issues.append('receipt task identity differs')
    inv=json.loads(read_text(checked_ref(r['inventory'],budget),budget));tick(budget)
    if not inv.get('files') or not inv.get('unique_inodes') or inv['unique_inodes']>inv['files']:issues.append('invalid inventory counts')
    if inv.get('errors'):issues.append('inventory enumeration/access errors remain')
    checked_ref(r['search_plan'],budget)
    outputs={str(checked_ref(x,budget)) for x in r['outputs']}
    if not outputs:issues.append('no verified output artifacts')
    sources={};turns={};unresolved=0
    for line in read_text(checked_ref(r['sources'],budget),budget).splitlines():
        tick(budget)
        s=json.loads(line);sid=s['id']
        if sid in sources:issues.append('duplicate source ID '+sid)
        sources[sid]=s
        if not s.get('locator') or not s.get('reason'):issues.append('source lacks locator/reason '+sid)
        if s.get('status') not in {'included','excluded','duplicate','blocked','unreviewed'}:issues.append('invalid source disposition '+sid)
        if s.get('status') in {'blocked','unreviewed'}:unresolved+=1
        if s.get('status')=='included' and not s.get('reviewed_extent'):unresolved+=1
    for line in read_text(checked_ref(r['turns'],budget),budget).splitlines():
        tick(budget)
        t=json.loads(line);tid=t['id']
        if tid in turns:issues.append('duplicate turn ID '+tid)
        turns[tid]=t
        if t.get('source_id') not in sources or not t.get('locator') or not t.get('attribution'):issues.append('turn identity/attribution missing '+tid)
        status=t.get('status')
        if status not in {'retained','superseded','excluded','unreviewed','blocked'}:issues.append('invalid turn disposition '+tid)
        if status in {'unreviewed','blocked'}:unresolved+=1
        if status in {'retained','superseded'}:
            dest=t.get('destination','').split('#',1)[0]
            if dest not in outputs:issues.append('turn lacks verified output destination '+tid)
        if status=='superseded' and not t.get('superseded_by'):issues.append('missing superseding turn '+tid)
        if status=='excluded' and not t.get('reason'):issues.append('missing exclusion reason '+tid)
    for t in turns.values():
        tick(budget)
        if t.get('superseded_by') and t['superseded_by'] not in turns:issues.append('superseding ID absent '+t['id'])
    if r.get('source_count')!=len(sources) or r.get('turn_count')!=len(turns):issues.append('catalogue count mismatch')
    if not sources or not turns:issues.append('empty source/turn catalogue')
    surface_total=0
    for x in r.get('surfaces',[]):
        tick(budget)
        if not all(k in x for k in ('name','inventoried_count','screened_count','excluded_count','unresolved_count','reason')):
            issues.append('incomplete source-surface reconciliation row');continue
        vals=[x[k] for k in ('inventoried_count','screened_count','excluded_count','unresolved_count')]
        if any(not isinstance(v,int) or v<0 for v in vals) or vals[0]!=sum(vals[1:]):issues.append('surface counts do not reconcile: '+str(x.get('name')))
        surface_total+=vals[0];unresolved+=vals[3]
    if surface_total!=inv['unique_inodes']:issues.append('surface totals do not match inventory unique objects')
    if not r.get('surfaces'):issues.append('missing source-surface reconciliation')
    candidates={}
    for line in read_text(checked_ref(r['candidate_manifest'],budget),budget).splitlines():
        tick(budget)
        x=json.loads(line)
        if not x.get('id') or not x.get('path'):issues.append('candidate lacks identity/path');continue
        if x['id'] in candidates:issues.append('duplicate candidate ID '+x['id'])
        candidates[x['id']]=x
    covered={s.get('candidate_id') for s in sources.values() if s.get('candidate_id')}
    if set(candidates)!=covered:issues.append('candidate-to-source reconciliation differs')
    if not candidates or r.get('candidate_count')!=len(candidates):issues.append('candidate count mismatch or empty candidates')
    if r.get('status')=='complete' and unresolved:issues.append(str(unresolved)+' unresolved sources/turns/surfaces')
    if r.get('status') not in {'complete','incomplete'}:issues.append('missing completion state')
    if r.get('status')=='incomplete' and not r.get('blockers'):issues.append('incomplete receipt lacks explicit remaining work')
    tick(budget);return r,issues

def main():
    a=argparse.ArgumentParser();a.add_argument('--host',choices=['codex','claude'],default='codex')
    actions=a.add_mutually_exclusive_group();actions.add_argument('--register',action='store_true');actions.add_argument('--finalize',action='store_true');actions.add_argument('--check-receipt')
    a.add_argument('--session-id');a.add_argument('--receipt');a.add_argument('--allow-model-cli',action='store_true');args=a.parse_args()
    if args.receipt and not (args.register or args.finalize):a.error('--receipt requires --register or --finalize')
    if args.allow_model_cli and not args.register:a.error('--allow-model-cli requires --register')
    if args.session_id and not (args.register or args.finalize):a.error('--session-id requires --register or --finalize')
    if args.finalize and not args.receipt:a.error('--finalize requires --receipt')
    if args.check_receipt:
        r=json.loads(pathlib.Path(args.check_receipt).read_text());_,issues=validate(args.check_receipt,r.get('task_id'));print(json.dumps({'issues':issues,'status':r.get('status')}));return bool(issues)
    if args.finalize:
        sid=args.session_id or os.environ.get('CODEX_THREAD_ID')
        if not sid:raise ValueError('session ID required')
        p=state_path(sid,args.host);s=json.loads(p.read_text()) if p.exists() else {}
        if not s.get('active') or s.get('scope','comprehensive')!='comprehensive' or not s.get('task_id'):raise ValueError('finalization requires an active comprehensive task')
        receipt,issues=validate(args.receipt,s['task_id'])
        if issues or receipt.get('status')!='complete':raise ValueError('receipt accounting not complete: '+'; '.join(issues or ['receipt status is not complete']))
        # Full validation can take time. Never overwrite a task changed meanwhile.
        if not p.exists() or json.loads(p.read_text())!=s:raise ValueError('task state changed during validation; retry against the current task')
        now=time.time();s.update(active=False,allow_model_cli=False,receipt=args.receipt,last_stop_status='accounted',finalized_at=now,updated_at=now);atomic(p,s)
        print(json.dumps({'task_id':s['task_id'],'status':'accounted','state_file':str(p),'semantic_completeness':'not established'}));return 0
    if args.register:
        sid=args.session_id or os.environ.get('CODEX_THREAD_ID')
        if not sid:raise ValueError('session ID required')
        p=state_path(sid,args.host);s=json.loads(p.read_text()) if p.exists() else {}
        if not s.get('active'):s={'task_id':hashlib.sha256((sid+str(time.time_ns())).encode()).hexdigest()[:20]}
        s.update(active=True,scope=s.get('scope','comprehensive'),receipt=args.receipt,allow_model_cli=args.allow_model_cli,updated_at=time.time());atomic(p,s);print(json.dumps({'task_id':s['task_id'],'state_file':str(p)}));return 0
    raw=sys.stdin.buffer.read(1048577)
    if len(raw)>1048576:raise ValueError('hook input exceeds one MiB')
    event=json.loads(raw);sid=event.get('session_id');name=event.get('hook_event_name')
    if not sid:return 0
    p=state_path(sid,args.host);s=json.loads(p.read_text()) if p.exists() else {}
    if name=='UserPromptSubmit':
        prompt=event.get('prompt','');low=prompt.lower()
        if event.get('source') in {'system','scheduled','loop_wakeup','schedule_wakeup','poll_event'} or event.get('is_automated') is True:return 0
        if re.match(r'^\s*(?:/archive-reconstruction\s+off|(?:cancel|abandon|stop)\s+(?:this|the)\s+(?:archive|reconstruction|task)|new task:)',low):
            s={'active':False,'updated_at':time.time()};atomic(p,s);return 0
        scope=recovery_scope(prompt)
        if scope=='continuation':scope=None if s.get('active') else 'bounded'
        if scope=='excluded':
            s={'active':False,'updated_at':time.time()};atomic(p,s);return 0
        if scope=='bounded' and s.get('active') and s.get('scope','comprehensive')=='comprehensive' and not narrows_task(prompt):
            scope='comprehensive'
        if scope or s.get('active'):
            old_scope=s.get('scope','comprehensive')
            if not s.get('active') or (scope and scope!=old_scope):s={}
            if not s.get('task_id'):s['task_id']=hashlib.sha256((sid+str(time.time_ns())).encode()).hexdigest()[:20]
            scope=scope or old_scope
            s.update(active=True,scope=scope,updated_at=time.time());atomic(p,s)
            route=ROUTE if scope=='comprehensive' else BOUNDED_ROUTE
            context(name,route+RECOVER_FIRST+MOMENTUM_ROUTE+' Task identity: '+s['task_id'])
        return 0
    if not s.get('active'):return 0
    if name=='PreToolUse' and not s.get('allow_model_cli') and launch_input(event.get('tool_input',{})):
        print(json.dumps({'hookSpecificOutput':{'hookEventName':name,'permissionDecision':'deny','permissionDecisionReason':'This active archive reconstruction uses local conversations. A model CLI launch is not archive acquisition. Read the archive directly; model workers require an explicit current-task request.'}}));return 0
    if name=='Stop':
        if s.get('scope','comprehensive')=='bounded':
            s.update(active=False,allow_model_cli=False,last_stop_status='bounded_handoff',updated_at=time.time());atomic(p,s);return 0
        try:
            if not s.get('receipt'):raise ValueError('no registered coverage receipt')
            receipt,issues=validate(s['receipt'],s['task_id'],ValidationBudget())
        except (ValueError,KeyError,TypeError,OSError) as e:receipt={};issues=[str(e)]
        last=event.get('last_assistant_message','') or '';honest=bool(re.search(r'\bincomplete\b|\bunfinished\b|\bunreviewed\b|not complete',last,re.I))
        if not issues and receipt.get('status')=='complete':
            s.update(active=False,allow_model_cli=False,last_stop_status='accounted',updated_at=time.time());atomic(p,s);return 0
        if honest and receipt.get('status')=='incomplete' and not issues:s['last_stop_status']='incomplete';atomic(p,s);return 0
        fingerprint=hashlib.sha256(json.dumps(issues,sort_keys=True).encode()).hexdigest()
        if event.get('stop_hook_active') and s.get('last_failure')==fingerprint:
            s.update(last_stop_status='forced_incomplete',updated_at=time.time());atomic(p,s)
            print(json.dumps({'systemMessage':'Archive coverage is still incomplete. The guard stops repeating this event; this is not a completion pass. Report the remaining work explicitly.'}));return 0
        s.update(last_failure=fingerprint,last_stop_status='blocked_incomplete');atomic(p,s)
        print(json.dumps({'decision':'block','reason':'Archive coverage is incomplete: '+'; '.join(issues[:5] or ['receipt records unfinished work'])+'. Continue acquisition/synthesis or provide an explicitly incomplete handoff with the concrete remaining work. Do not claim exhaustive coverage.'}));return 0
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print('archive-guard: '+str(e),file=sys.stderr);sys.exit(1)
