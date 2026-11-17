export function today(){const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export function nextDay(day){const d=new Date(day+'T12:00:00');d.setDate(d.getDate()+1);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
export const minutes=t=>{const [h,m]=t.split(':').map(Number);return h*60+m;};
export const clock=m=>`${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}`;
export function cleanTask(t){
 const title=String(t.title||'').trim();if(!title)throw Error('Every task needs a name.');
 const dateValue=v=>{if(!v)return '';if(!/^\d{4}-\d{2}-\d{2}$/.test(v)||!Number.isFinite(Date.parse(v+'T12:00:00'))||new Date(v+'T12:00:00').getDate()!==Number(v.slice(8)))throw Error('Enter a valid date.');return v;};
 const duration=Math.round(Number(t.minutes??30));if(!Number.isFinite(duration)||duration<5||duration>480)throw Error('Choose a duration from 5 to 480 minutes.');
 const fixed=t.fixed||'';if(fixed&&!/^([01]\d|2[0-3]):[0-5]\d$/.test(fixed))throw Error('Enter a valid appointment time.');
 const appointmentDate=dateValue(t.appointmentDate);if(!!fixed!==!!appointmentDate)throw Error('An appointment needs both a date and a fixed start time.');
 return {id:typeof t.id==='string'?t.id:crypto.randomUUID(),title:title.slice(0,500),category:t.category==='professional'?'professional':'personal',minutes:duration,energy:['low','medium','high'].includes(t.energy)?t.energy:'medium',location:['anywhere','office','home','outside'].includes(t.location)?t.location:'anywhere',activity:['desk','call','errand','quick'].includes(t.activity)?t.activity:'desk',due:dateValue(t.due),appointmentDate,fixed,must:t.must===true,delayed:t.delayed===true,quick:t.quick===true,waiting:t.waiting===true,skipDate:dateValue(t.skipDate),done:t.done===true,deferUntil:dateValue(t.deferUntil)};
}
export function makePlan(tasks,p){
 const start=minutes(p.start),end=minutes(p.end);if(!Number.isFinite(start)||!Number.isFinite(end)||end<=start)throw Error('Choose an end time later than your start time.');
 const selected=[],deferred=[],warnings=[],occupied=[],breaks=[];
 const priority=t=>t.must||t.delayed||t.due&&t.due<=p.date;
 const defer=(t,reason)=>{deferred.push({task:t,reason});if(priority(t))warnings.push(`${t.title}: ${reason}`);};
 const pending=tasks.filter(t=>!t.done);
 const eligible=pending.filter(t=>{if(t.skipDate===p.date){defer(t,'You chose to skip this day.');return false;}if(t.waiting){defer(t,'Waiting on someone.');return false;}if(t.deferUntil&&t.deferUntil>p.date){defer(t,`Postponed until ${t.deferUntil}.`);return false;}return true;});
 function reserve(t,s,reason){selected.push({task:t,start:s,end:s+t.minutes,reason});occupied.push({start:s,end:s+t.minutes});}
 const appointments=eligible.filter(t=>t.fixed&&t.appointmentDate===p.date).sort((a,b)=>a.fixed.localeCompare(b.fixed));
 for(const t of appointments){const s=minutes(t.fixed),e=s+t.minutes;if(s<start||e>end){defer(t,'Appointment is outside your planning window.');warnings.push(`Appointment outside window: ${t.title}`);}else if(occupied.some(o=>s<o.end&&e>o.start)){defer(t,'Overlaps another appointment.');warnings.push(`Appointment conflict: ${t.title}`);}else{reserve(t,s,'Fixed appointment.');if(t.location!=='anywhere'&&!p.locations.includes(t.location))warnings.push(`${t.title}: appointment location is outside your selected locations.`);}}
 const score=t=>(t.must?100000:0)+(t.delayed?10000:0)+(t.due&&t.due<=p.date?5000:t.due?Math.max(0,500-(Date.parse(t.due)-Date.parse(p.date))/86400000*20):0)+(t.quick&&t.minutes<=20?(p.mood==='light'?400:200):0)+(p.mood==='light'&&t.energy==='low'||p.mood==='focus'&&t.energy==='high'?200:0)+(60-Math.min(t.minutes,60));
 for(const t of eligible.filter(t=>t.fixed&&t.appointmentDate!==p.date))defer(t,`Appointment belongs to ${t.appointmentDate}.`);
 for(const t of eligible.filter(t=>!t.fixed).sort((a,b)=>score(b)-score(a))){
 let reason='';if(p.focus!=='both'&&t.category!==p.focus)reason='Outside your chosen personal/professional focus.';else if(t.location!=='anywhere'&&!p.locations.includes(t.location))reason=`Requires ${t.location}.`;else if(!p.activities.includes(t.activity))reason='Activity type is not selected.';else if(p.mood==='light'&&t.energy==='high'&&!priority(t))reason='Saved for a higher-energy day.';
 if(reason){defer(t,reason);continue;}
 let cursor=start,fit=null;for(const o of [...occupied.slice().sort((a,b)=>a.start-b.start),{start:end,end}]){if(cursor+t.minutes<=o.start){fit=cursor;break;}cursor=Math.max(cursor,o.end);}
 if(fit===null){defer(t,'Not enough uninterrupted time.');continue;}
 reserve(t,fit,t.must?'Must do today.':t.delayed?'Already delayed.':t.due&&t.due<=p.date?'Due or overdue.':t.quick&&t.minutes<=20?'Quick win.':'Fits your day.');
 const bs=fit+t.minutes,be=bs+Number(p.breakMinutes);if(be>bs&&be<=end&&!occupied.some(o=>bs<o.end&&be>o.start)){occupied.push({start:bs,end:be});breaks.push({start:bs,end:be});}
 }
 return {date:p.date,start,end,selected:selected.sort((a,b)=>a.start-b.start),rank:selected.slice().sort((a,b)=>score(b.task)-score(a.task)),deferred,warnings:[...new Set(warnings)],breaks};
}
