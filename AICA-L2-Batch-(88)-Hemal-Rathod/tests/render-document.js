var __mode = window.__PRINT_MODE || 'detailed';
var __caseId = window.__CASE_ID || 'case-06';
var __c = TAS.samples.byId(__caseId);
TAS.state.replace(__c.input);
var __r = TAS.state.evaluate();
var __wp = TAS.workingpaper.generateWorkingPaper(__r);
document.getElementById('print-root').innerHTML = TAS.workingpaper.renderDocument(__wp, __mode);
document.documentElement.setAttribute('data-print-mode', __mode);
JSON.stringify({ status: __r.status, mode: __mode, htmlLength: document.getElementById('print-root').innerHTML.length });
