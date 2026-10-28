"""Chronotype timetable, exam-hall stamina protocol and Pomodoro timer."""
from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

TIMETABLES: dict[str, list[tuple[str, str]]] = {
    "Early Morning (5 AM - 9 AM)": [
        ("5:00 - 5:15", "Wake, water, light movement"),
        ("5:15 - 6:45", "Hardest numericals: Capital Budgeting, Cost of Capital (fresh working memory)"),
        ("6:45 - 7:00", "Break and breakfast"),
        ("7:00 - 8:30", "Paper 6B case-study reading and framework answers"),
        ("8:30 - 9:00", "Formula cue-card recall, no looking first"),
        ("Evening (short)", "30 min error-log review; sleep by 10 PM"),
    ],
    "Late Night (10 PM - 2 AM)": [
        ("10:00 - 10:15", "Settle, water, dim the room"),
        ("10:15 - 11:45", "Numericals: Working Capital, Leverages, Dividend"),
        ("11:45 - 12:00", "Break, stretch, no phone"),
        ("12:00 - 1:15", "Theory and Paper 6B recall; write answers from memory"),
        ("1:15 - 2:00", "Light revision of formula matrix; wind down"),
        ("Next day", "Protect a fixed wake time; do not skip morning daylight"),
    ],
}

EXAM_HALL_PROTOCOL: list[tuple[str, str]] = [
    ("Exam window", "The paper runs 2:00 PM - 5:00 PM, which overlaps the natural post-lunch dip. Practise at this hour in the last 3 weeks."),
    ("Lunch", "Choose a lower glycemic index meal (dal, vegetables, curd, some whole grains). Avoid heavy fried food and large sweet portions."),
    ("Timing", "Finish lunch about 90 minutes before entering the hall; keep portions moderate."),
    ("Hydration", "Drink water steadily in the morning, 300-500 ml before entering, and sip in the hall. Avoid a large intake just before the paper."),
    ("Caffeine", "If you use tea or coffee, keep it consistent with your practice routine; do not try anything new on exam day."),
    ("Fatigue reset", "Stand for 20 seconds at the hour mark, relax shoulders, take 5 slow breaths, then continue."),
    ("Paper strategy", "Start with the question you are most confident in to build momentum; keep a time budget per mark."),
]

_POMODORO_HTML = """
<div style="font-family:Arial,sans-serif;text-align:center;padding:12px;border:1px solid #0284C7;border-radius:12px;background:#F8FAFC;color:#0F172A">
  <div id="phase" style="font-weight:700;color:#0284C7">Focus</div>
  <div id="time" style="font-size:44px;font-weight:700">__FOCUS__:00</div>
  <button onclick="startT()" style="padding:6px 14px;border-radius:8px;border:1px solid #0284C7;background:#0284C7;color:#fff">Start</button>
  <button onclick="resetT()" style="padding:6px 14px;border-radius:8px;border:1px solid #0284C7;background:#fff;color:#0284C7">Reset</button>
</div>
<script>
const F=__FOCUS__*60, R=__REST__*60; let phase='Focus', left=F, h=null;
const t=document.getElementById('time'), p=document.getElementById('phase');
function fmt(s){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');}
function draw(){t.textContent=fmt(left);p.textContent=phase;}
function startT(){ if(h) return; h=setInterval(()=>{ left--; if(left<0){ phase=(phase==='Focus')?'Rest':'Focus'; left=(phase==='Focus')?F:R; } draw(); },1000);}
function resetT(){ clearInterval(h); h=null; phase='Focus'; left=F; draw(); }
draw();
</script>
"""


def render_scheduler() -> None:
    st.subheader("Cognitive Stamina and Chronotype Timetable")
    choice = st.radio("Your chronotype", list(TIMETABLES), horizontal=True)
    st.table({"Time": [a for a, _ in TIMETABLES[choice]], "Activity": [b for _, b in TIMETABLES[choice]]})

    st.markdown("#### Exam Hall Stamina Protocol (2:00 PM - 5:00 PM)")
    for head, body in EXAM_HALL_PROTOCOL:
        st.markdown(f"**{head}.** {body}")
    st.caption("General wellness guidance, not medical advice.")

    st.markdown("#### Pomodoro timer")
    cycle = st.radio("Cycle", ["25 / 5", "50 / 10"], horizontal=True)
    focus, rest = (25, 5) if cycle == "25 / 5" else (50, 10)
    components.html(_POMODORO_HTML.replace("__FOCUS__", str(focus)).replace("__REST__", str(rest)), height=190)
