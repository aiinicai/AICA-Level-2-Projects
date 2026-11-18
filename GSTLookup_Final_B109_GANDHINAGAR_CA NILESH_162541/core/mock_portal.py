"""Explicitly synthetic local portal; never returns real taxpayer data."""
import io, secrets, time
from flask import Flask, request, session, jsonify, send_file
from PIL import Image, ImageDraw
from config import PATHS
from core.validators import checksum

def demo_gstin(state='27',entity='1'):
    s=state+'AAACT1234K'+entity+'Z';return s+checksum(s)

def create_mock():
    app=Flask(__name__);app.secret_key=secrets.token_hex(32);app.config['SCENARIO']='ok';app.config['HITS']=0
    @app.get(PATHS['page'])
    def page(): return '<h1>LOCAL DEMO GST portal</h1>'
    @app.get(PATHS['captcha'])
    def captcha():
        answer=str(secrets.randbelow(900000)+100000);session['captcha']=answer
        im=Image.new('RGB',(240,70),'white');ImageDraw.Draw(im).text((15,20),answer,fill='black',font_size=28)
        out=io.BytesIO();im.save(out,'PNG');out.seek(0);return send_file(out,mimetype='image/png')
    def lookup():
        app.config['HITS']+=1;scenario=app.config['SCENARIO']
        if scenario=='timeout': time.sleep(.15)
        if scenario=='500': return jsonify(error='demo server error'),500
        if scenario=='429' and app.config['HITS']<3: return jsonify(error='demo throttle'),429
        data=request.get_json()
        if data.get('captcha')!=session.pop('captcha',None): return jsonify(errorCode='SWEB_9000')
        if scenario=='notfound': return jsonify(errorCode='SWEB_9032')
        if 'panNO' in data: return jsonify(gstinResList=[{'gstin':demo_gstin(s)} for s in ('27','07','29')])
        return jsonify(gstin=data['gstin'],lgnm='DEMO ONLY - Sample Legal Company Limited',tradeNam='DEMO ONLY - Sample Company',rgdt='01/07/2017',ctb='Private Limited Company',sts='Active',dty='Regular',admOfc=['Centre: Demo'],othrOfc=['State: Demo'],pradr={'adr':'Synthetic address, India'},adadr=[],bzsdtls={'gds':[{'hsncd':'1001','gdes':'DEMO Wheat'}],'sac':[{'saccd':'9983','sdes':'DEMO Services'}]})
    app.add_url_rule(PATHS['GSTIN'],'gstin',lookup,methods=['POST']);app.add_url_rule(PATHS['PAN'],'pan',lookup,methods=['POST'])
    @app.get(PATHS['goods'])
    def goods():
        return jsonify(bzgddtls=[{'hsncd':'1001','gdes':'DEMO Wheat'}],bzsdtls=[{'saccd':'9983','sdes':'DEMO Services'}])
    @app.get(PATHS['years'])
    def years():
        return jsonify(status=1,data=[{'year':f'{y}-{str(y+1)[-2:]}','value':str(y)+str(y+1)} for y in range(2017,2027)])
    @app.post(PATHS['returns'])
    def returns():
        if app.config.get('RETURN_ERROR'): return jsonify(errorCode='SWEB_8000')
        if app.config.get('RETURN_CAPTCHA') and (not request.json.get('captcha') or request.json.get('captcha')!=session.pop('captcha',None)): return jsonify(errorCode='SWEB_9000')
        fy=request.json['fy']
        if len(str(fy))!=8: return jsonify(errorCode='SWEB_9034')
        return jsonify(filingStatus=[[dict(rtntype=t,taxp=period,status='Filed',dof=d,fy=fy[:4]+'-'+fy[4:]) for t,period,d in [('GSTR3B','April','20/05/2025'),('GSTR1','April','11/05/2025'),('GSTR9','Annual','31/12/2025'),('GSTR9C','Annual','31/12/2025')]]])
    return app
