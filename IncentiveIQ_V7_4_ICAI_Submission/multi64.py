from answer68 import rank
from answer65 import answer as extract
from engine import official
from urllib.parse import urlencode
TYPES=['Industrial Policy','Package Scheme of Incentives','Government Resolution','Amendment','Implementation Guidelines','Official FAQ']
def research_link(state,kind,topic):
 return 'https://www.google.com/search?'+urlencode({'q':f'{state} {kind} {topic} (site:gov.in OR site:nic.in)'})
def collect(docs,q):
 # Rank each document independently so a long policy cannot crowd out a short notification.
 groups=[rank({src:body},q,k=5) for src,body in docs.items()]
 groups=[g for g in groups if g]
 allhits=sorted([h for g in groups for h in g],key=lambda h:h[0],reverse=True)
 primary=sorted([g[0] for g in groups],key=lambda h:h[0],reverse=True)
 shown=primary[:8]
 for h in allhits:
  if h not in shown and len(shown)<12: shown.append(h)
 return shown,allhits

def combined(docs,q,state):
 shown,allhits=collect(docs,q)
 # Existing conservative extractor checks all retrieved candidates, not just displayed excerpts.
 result=extract(allhits,q,state) if allhits else None
 return result,shown
