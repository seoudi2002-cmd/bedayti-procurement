/* service worker registration + "update ready" prompt */
(()=>{
if(!("serviceWorker" in navigator)||location.protocol==="file:")return;
const ask=w=>{const t=document.createElement("div");t.className="toast";t.style.pointerEvents="auto";
  t.innerHTML='نسخة جديدة من التطبيق جاهزة <button class="btn sm gold" type="button" style="margin-inline-start:8px">حدّث</button>';
  t.querySelector("button").onclick=()=>{w.postMessage("skip");t.remove()};document.body.append(t)};
navigator.serviceWorker.register("sw.js").then(reg=>{
  if(reg.waiting&&navigator.serviceWorker.controller)ask(reg.waiting);
  reg.addEventListener("updatefound",()=>{const w=reg.installing;w&&w.addEventListener("statechange",()=>{if(w.state==="installed"&&navigator.serviceWorker.controller)ask(w)})});
  setInterval(()=>reg.update().catch(()=>{}),6*36e5);
}).catch(()=>{});
/* reload only when an already-running copy is replaced by an update the user accepted; the very first install must never reload the page under them */
const hadController=!!navigator.serviceWorker.controller;let reloaded=false;
navigator.serviceWorker.addEventListener("controllerchange",()=>{if(!hadController||reloaded)return;reloaded=true;location.reload()});
})();
