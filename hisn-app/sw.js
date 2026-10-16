/* حصن السعودي service worker: the app shell is precached so the app opens offline;
   Google Fonts are cached on first use; price APIs always go to the network. */
const VERSION="1.0.0";
const SHELL="hisn-shell-"+VERSION, FONTS="hisn-fonts-v1";
const ASSETS=["./","index.html","css/base.css","css/app.css","js/version.js","js/money.js","js/app.js","js/pwa.js",
  "manifest.webmanifest","icons/icon.svg","icons/icon-192.png","icons/icon-512.png","icons/maskable-512.png","icons/apple-touch-icon.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(SHELL).then(c=>c.addAll(ASSETS)))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith("hisn-shell-")&&k!==SHELL).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener("message",e=>{if(e.data==="skip")self.skipWaiting()});
self.addEventListener("fetch",e=>{const r=e.request;if(r.method!=="GET")return;const u=new URL(r.url);
  if(u.origin===location.origin){
    if(r.mode==="navigate"){e.respondWith(caches.match("index.html").then(m=>m||fetch(r)));return}
    e.respondWith(caches.match(r,{ignoreSearch:true}).then(m=>m||fetch(r)));return}
  if(u.hostname==="fonts.googleapis.com"||u.hostname==="fonts.gstatic.com"){
    e.respondWith(caches.open(FONTS).then(async c=>{const m=await c.match(r);const net=fetch(r).then(res=>{if(res.ok||res.type==="opaque")c.put(r,res.clone());return res}).catch(()=>m);return m||net}));}
});
self.addEventListener("notificationclick",e=>{e.notification.close();e.waitUntil(self.clients.matchAll({type:"window"}).then(cs=>cs.length?cs[0].focus():self.clients.openWindow("./")))});
