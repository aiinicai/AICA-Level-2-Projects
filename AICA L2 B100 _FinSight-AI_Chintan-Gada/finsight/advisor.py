"""Grounded AI draft generation; no raw uploaded financial documents sent to provider."""
import json, os

def fallback(facts):
    y=facts['periods'][-1]; p=facts['periods'][-2]; m=facts['metrics']; a=m[y]; b=m[p]
    lines=[f'FINANCIAL REVIEW — {y} (DETERMINISTIC DRAFT)',f'Revenue: {b["Revenue"]:.2f} to {a["Revenue"]:.2f}. EBITDA: {b["EBITDA"]:.2f} to {a["EBITDA"]:.2f}. PAT: {b["PAT"]:.2f} to {a["PAT"]:.2f}.',f'Operating cash flow: {b["Operating cash flow"]:.2f} to {a["Operating cash flow"]:.2f}. Current ratio: {a["Current ratio"]:.2f}x.']
    if facts['risk_flags']:
        lines.append('AREAS FOR MANAGEMENT REVIEW')
        for f in facts['risk_flags']: lines.append(f'- {f["code"]}: {f["evidence"]}. Action: {f["recommendation"]}')
    else: lines.append('No configured risk rules were triggered. This does not establish absence of risk.')
    lines.append('Prepared from uploaded figures. Verify source statements and conclusions before external use.')
    return '\n'.join(lines)

def generate(facts, use_ai=False, model='gpt-4.1-mini'):
    if not use_ai: return fallback(facts),'Deterministic offline draft'
    if not os.getenv('OPENAI_API_KEY'): raise ValueError('OPENAI_API_KEY not configured. Turn off AI or configure the environment variable.')
    from openai import OpenAI
    prompt='''You are a CFO analysis assistant. Use ONLY the supplied verified JSON figures. Do not invent values, industry norms, events, causal explanations or regulations. Distinguish observations from hypotheses. Cite period and numeric evidence for each observation. Give a concise executive summary, financial strengths, concerns, questions to management, and practical actions. State that a CA must review the draft. Do not treat this as audit assurance. All amounts are in the units selected by the user.''' 
    response=OpenAI(timeout=45).responses.create(model=model,instructions=prompt,input=json.dumps(facts,allow_nan=False),max_output_tokens=1100)
    return response.output_text,'OpenAI generated — human approval required'
