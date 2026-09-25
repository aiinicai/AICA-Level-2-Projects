(function(){
  const root=document.documentElement;
  const saved=localStorage.getItem('ibc-theme');
  if(saved==='dark'||saved==='light'){root.dataset.theme=saved;}
  const toggle=document.querySelector('[data-theme-toggle]');
  if(toggle){toggle.addEventListener('click',function(){const next=root.dataset.theme==='dark'?'light':'dark';root.dataset.theme=next;localStorage.setItem('ibc-theme',next);});}
})();
