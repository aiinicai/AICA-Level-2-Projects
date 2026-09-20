"""Sequential source requests on a background Python thread; no GUI imports."""
from . import db, scoring
from .scrapers import REGISTRY, SOURCE_URLS, GMP_DIAGNOSTIC_SOURCES, GMP_REDIRECTS
from .research import enrich_record

def run_refresh(emit, cancel):
    ok=failed=0
    for key,(module,name,official,_) in REGISTRY.items():
        if cancel.is_set(): break
        emit('log', f'Fetching {name}…')
        try:
            records,message=module.fetch()
            count=0
            skipped=0
            for rec in records:
                if cancel.is_set(): break
                try:
                    # Only filter brand-new companies: if this source has no
                    # open/close date for a name we don't already track, it's
                    # most likely an IPO that has already closed/listed and
                    # dropped off the source's live table, not a fresh
                    # listing — don't add it to the IPO list. An IPO we
                    # already track can still receive GMP/other updates from
                    # a dateless row (e.g. a GMP-only table).
                    if not db.find_by_name(rec.get('name','')) and not rec.get('open_date') and not rec.get('close_date'):
                        skipped+=1
                        continue
                    db.merge_incoming(rec,key,name,SOURCE_URLS[key],'Live source import',official)
                    count+=1
                except Exception as e: emit('log',f'{name}: skipped a row: {e}')
            if skipped: emit('log',f'{name}: skipped {skipped} row(s) with no open/close date (likely closed IPOs no longer listed by the source)')
            if key in GMP_DIAGNOSTIC_SOURCES:
                # Record this source's per-company GMP quote (or explicit
                # "no quote published") for the GMP tab's diagnostics table —
                # separate from the merge above, which only ever updates the
                # single, official/priority-ordered gmp_amount.
                db.sync_gmp_quotes(key,name,SOURCE_URLS[key],records,redirect_note=GMP_REDIRECTS.get(key))
            db.log_refresh(name,True,message,count)
            emit('log',f'{name}: {message}; saved {count}')
            ok+=1
            emit('data',None)
        except Exception as e:
            db.log_refresh(name,False,str(e))
            emit('log',f'{name}: unavailable — {e}')
            failed+=1
            if key in GMP_DIAGNOSTIC_SOURCES:
                db.sync_gmp_quotes_failed(key,name,SOURCE_URLS[key],str(e))
    remapped=db.consolidate_duplicates()
    if remapped: emit('log',f'Merged {len(remapped)} duplicate BSE/NSE record(s).')
    all_records=db.all_ipos()
    purged=db.purge_malformed_records(all_records)
    if purged: emit('log',f'Removed {purged} malformed record(s) created by a since-fixed parsing bug.')
    if purged: all_records=db.all_ipos()
    scoped=[r for r in all_records if db.in_refresh_scope(r)]
    # Open/upcoming IPOs are analysed first, closed/recently-listed ones
    # after — so a long closed-IPO backlog can never delay or crowd out
    # research on the IPOs actually being looked at right now.
    current=sorted(scoped,key=lambda r: 0 if db.is_active(r) else 1)
    for i,record in enumerate(current,1):
        if cancel.is_set(): break
        emit('log',f'Analysing {i}/{len(current)} open, closed & recently-listed IPOs: {record["name"]}…')
        try: emit('log',enrich_record(record))
        except Exception as e: emit('log',f'{record["name"]}: statements unavailable — {e}; existing data retained with its original date')
        result=scoring.analyse(db.get(record['id']))
        emit('log',f'Coverage {result["coverage"]:.0f}%; {result["auto"]}')
        emit('data',None)
    emit('done',f'{ok} sources responded; {failed} unavailable. '+('Stopped after current request.' if cancel.is_set() else 'Automatic analysis completed.'))
