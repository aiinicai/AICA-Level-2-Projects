"""Optional, user-triggered Responses API drafting. No secret is persisted."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def request_draft(prompt,key,model,opener=None):
    if not key.strip() or not model.strip(): raise ValueError('Enter an API key and a model available to your API account.')
    body=dict(model=model.strip(),store=False,input=prompt,max_output_tokens=1800)
    req=Request('https://api.openai.com/v1/responses',data=json.dumps(body).encode(),
                headers={'Authorization':'Bearer '+key.strip(),'Content-Type':'application/json'},method='POST')
    try:
        with (opener or urlopen)(req,timeout=55) as response:
            data=json.load(response)
    except HTTPError as exc:
        raise ValueError(f'OpenAI API returned HTTP {exc.code}. Check account access, model, credits, or rate limits. No draft was saved.') from None
    except (URLError,TimeoutError):
        raise ValueError('AI request could not complete. Check connection; no draft was saved.') from None
    if data.get('status')!='completed':
        raise ValueError('The AI response was incomplete or unsuccessful. No draft was saved.')
    texts=[c['text'] for item in data.get('output',[]) if item.get('type')=='message'
           for c in item.get('content',[]) if c.get('type')=='output_text']
    if not texts: raise ValueError('No draft text returned. The model may have refused the request.')
    return dict(text='\n'.join(texts),response_id=data.get('id',''),model=data.get('model',model),usage=data.get('usage',{}))
