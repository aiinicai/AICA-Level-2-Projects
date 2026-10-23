"""Builds public/app.html (self-hosted edition) from the published TickTrail page.
Usage: python3 build_app.py <published TickTrail.html> <output app.html>
Every replacement must match exactly once, so a changed source fails loudly instead of half-patching."""
import sys

src, out = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()

def rep(a, b):
    global s
    n = s.count(a)
    assert n == 1, f"expected 1 match, found {n}: {a[:90]!r}"
    s = s.replace(a, b, 1)

# --- 1. sign-in happens on the server, so skip the in-page password gate
rep('''  S.me = me; if(me.name) S.names[me.id] = me.name;
  S.gate = "checking"; render();
  db.doc("auth/"+me.id).onSnapshot(''',
'''  S.me = me; if(me.name) S.names[me.id] = me.name;
  S.auth = me.auth || {}; unlock(true); return;
  db.doc("auth/"+me.id).onSnapshot(''')

# --- 2. log out ends the server session (after pending saves finish)
rep('''function logout(reason){
  if(!S.unlocked) return;''',
'''function logout(reason){
  if(!S.unlocked) return;
  S.unlocked = false; stopTimer();
  const go = () => { location.href = "/logout" + (reason ? "?r=" + encodeURIComponent(reason) : ""); };
  Promise.race([flushPending().catch(()=>{}), new Promise(r => setTimeout(r, 4000))]).then(go, go);
  return;''')

# --- 3. change password through the server
rep('''    const o = $("#cpOld").value, n1 = $("#cpNew").value, n2 = $("#cpNew2").value;
    const h0 = await hashPw(o, S.auth?.salt); if(h0.hash !== S.auth?.hash){ toast("Current password is wrong."); return; }''',
'''    const o = $("#cpOld").value, n1 = $("#cpNew").value, n2 = $("#cpNew2").value;
    if(!o){ toast("Enter your current password."); return; }
    if(n1.length < 8 || !/[A-Za-z]/.test(n1) || !/\\d/.test(n1)){ toast("Use at least 8 characters with letters and numbers."); return; }
    if(n1 !== n2){ toast("The new passwords do not match."); return; }
    try{ const r = await window.__TT_SELF.post("/api/password", {old:o, new:n1}); S.auth = {...S.auth, setAt: r.setAt}; $("#cpForm").reset(); toast("Password changed"); }
    catch(err){ toast(err.message || "Could not change the password."); }
    return;''')

# --- 4. password reset gives the admin a temporary password to pass on
rep('''write("auth/"+id, r=>r.delete()); toast("Password reset. They will set a new one at their next login.");''',
'''window.__TT_SELF.post("/api/admin/reset", {uid:id}).then(r => panel(`<h2>Temporary password</h2>
    <p>Give these to <b>${esc(who(id))}</b> in person or by phone, not by email. They will choose their own password when they log in.</p>
    <dl class="pinfo"><dt>User name</dt><dd class="mono">${esc(r.username)}</dd><dt>Temporary password</dt><dd class="mono">${esc(r.password)}</dd></dl>
    <p class="muted">This password is shown only once. They have also been logged out everywhere.</p>
    <div class="foot"><span></span><button class="btn primary" data-close="1">Done</button></div>`)).catch(e => toast(e.message || "Could not reset the password."));''')

# --- 5. deleting a user also removes their login
rep('''["members","rates","requests","auth"].forEach(c => write(`${c}/${id}`, r=>r.delete())); toast("User deleted. Also remove them from the Share menu.");''',
'''window.__TT_SELF.post("/api/admin/delete-user", {uid:id}).then(() => { ["members","rates","requests"].forEach(c => write(`${c}/${id}`, r=>r.delete())); toast("User deleted. Their name stays on work already done."); }).catch(e => toast(e.message || "Could not delete the user."));''')

# --- 6. Team & access: admins are set here (no Share menu on a private server)
rep('''    <td>${adm?`<span class="rolechip">Admin</span>`:`<select data-role="${id}"><option value="staff" ${m.role!=="reviewer"?"selected":""}>Staff</option><option value="reviewer" ${m.role==="reviewer"?"selected":""}>Reviewer</option></select>`}</td>''',
'''    <td>${(self || id===window.__TT_SELF.ownerId)?`<span class="rolechip">${id===window.__TT_SELF.ownerId?"Owner":"Admin"}</span>`:`<select data-role="${id}"><option value="staff" ${m.role!=="reviewer"&&m.role!=="admin"?"selected":""}>Staff</option><option value="reviewer" ${m.role==="reviewer"?"selected":""}>Reviewer</option><option value="admin" ${m.role==="admin"?"selected":""}>Admin</option></select>`}</td>''')
rep('''    <td>${adm||self?`<span class="muted" style="font-size:13px">${adm?"Change in Share menu":""}</span>`:''',
'''    <td>${(self || id===window.__TT_SELF.ownerId)?`<span class="muted" style="font-size:13px"></span>`:''')
rep('''<p>Everyone signs in with their own Claude account. New people appear under Requests; nobody sees clients or audit files until you approve them.</p>''',
'''<p>Everyone logs in with their own user name and password on this server. New people create a login and appear under Requests; nobody sees clients or audit files until you approve them.</p>''')
rep('''<b>Admins</b> (the owner, and anyone given Editor access in the Share menu) manage the team, library and thresholds. Disabling blocks a person at once. Deleting removes their access but keeps their name on work already done. To fully remove someone, also remove them in this page's Share menu.</div>''',
'''<b>Admins</b> (the owner, and anyone you set as Admin here) manage the team, library and thresholds. Disabling blocks a person at once. Deleting removes their login but keeps their name on work already done.</div>''')
rep('''(S.me.isOwner ? "Owner of the register" : "Editor access in the Share menu")''',
'''(S.me.isOwner ? "Owner of the register" : "Set as Admin by the owner")''')

# --- 7. wording that pointed at Claude
rep('''<p>Open this page in Claude while signed in. Your clients, audits and checklist library are stored there.</p>''',
'''<p>The TickTrail server could not be reached. Check that it is running, then reload this page.</p>''')
rep('''<p>Ask Claude to load the standard checklist into this register.</p>''',
'''<p>Load the standard checklist on the server with: node server.js --import seed</p>''')
rep('''<p>Reload the page. If this keeps happening, tell Claude the message above.</p>''',
'''<p>Reload the page. If this keeps happening, check that the TickTrail server is running and note the message above.</p>''')
rep('''Uploads are not available for your access level. Ask an admin to give you Contributor access.''',
'''Uploads are not available until an admin approves your access.''')

open(out, "w", encoding="utf-8").write(s)
print("built", out)
