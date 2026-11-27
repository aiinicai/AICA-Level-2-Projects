import math

def project(cap,op,inc,years,rate,delay=0,duration=None):
    duration=years if duration is None else duration
    base=[-cap]+[op]*years
    benefit=[0]+[inc if delay<i<=delay+duration else 0 for i in range(1,years+1)]
    total=[a+b for a,b in zip(base,benefit)]
    def npv(cf,r): return sum(v/(1+r/100)**i for i,v in enumerate(cf))
    def pay(cf):
        bal=cf[0]
        for i,v in enumerate(cf[1:],1):
            if bal<0<=bal+v and v>0:return i-1-bal/v
            bal+=v
        return None
    def irr(cf):
        if any(v<0 for v in cf[1:]) or not any(v>0 for v in cf[1:]):return None
        lo,hi=-99.999,100.
        while npv(cf,hi)>0 and hi<1e8:hi*=2
        if npv(cf,lo)<0 or npv(cf,hi)>0:return None
        for _ in range(100):
            mid=(lo+hi)/2
            if npv(cf,mid)>0:lo=mid
            else:hi=mid
        return (lo+hi)/2
    discounted=[v/(1+rate/100)**i for i,v in enumerate(total)]
    return dict(base=base,benefit=benefit,total=total,discounted=discounted,npv_base=npv(base,rate),npv=npv(total,rate),irr=irr(total),roi=sum(total)/cap*100,payback=pay(total),discounted_payback=pay(discounted))
