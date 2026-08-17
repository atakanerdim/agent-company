/* Otonom Stüdyo — veri site/veri altından okunur (build.py üretir). */
async function j(yol){ try{ const r=await fetch("veri/"+yol); return r.ok? r.json():null }catch(e){ return null } }
async function t(yol){ try{ const r=await fetch("veri/"+yol); return r.ok? r.text():null }catch(e){ return null } }
const el=id=>document.getElementById(id);
const kacir=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

async function ortak(){
  const a=await t("ad.txt");
  if(a&&a.trim()&&el("sirket-adi")) el("sirket-adi").textContent=a.trim();
}

async function pano(){
  if(!el("olaylar")) return;
  const g=await j("gunluk.json");
  if(g&&g.length) el("olaylar").innerHTML=g.slice(0,12).map(x=>
    `<div class="satir"><span>${kacir(x.mesaj)}</span><span class="soluk">${kacir(x.tarih)}</span></div>`).join("");
  const m=await j("manifest.json"); if(!m) return;
  const kor=m.dosyalar.filter(d=>d.startsWith("koridor/")).sort().slice(-6);
  if(kor.length){
    const satirlar=await Promise.all(kor.map(k=>t(k)));
    el("koridor").innerHTML=satirlar.filter(Boolean).map(s=>`<div class="satir"><span>${kacir(s.trim())}</span></div>`).join("");
  }
}

async function tahmin(){
  if(!el("lig-tablo")) return;
  const lig=await j("data/league.json");
  if(lig){
    const p=Object.entries(lig.personalar).sort((a,b)=>b[1].puan-a[1].puan);
    el("lig-tablo").innerHTML="<table><tr><th>Persona</th><th>Puan</th><th>Kesin skor</th><th>Doğru sonuç</th><th>Hafta</th></tr>"+
      p.map(([ad,k])=>`<tr><td>${kacir(ad)}</td><td>${k.puan}</td><td>${k.kesin}</td><td>${k.sonuc}</td><td>${k.hafta}</td></tr>`).join("")+"</table>";
    if(window.Chart&&el("lig-grafik")) new Chart(el("lig-grafik"),{type:"bar",
      data:{labels:p.map(x=>x[0]),datasets:[{label:"puan",data:p.map(x=>x[1].puan),backgroundColor:"#5b8cff"}]},
      options:{plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{color:"#9aa3b5"}},x:{ticks:{color:"#9aa3b5"}}}}});
  }
  const m=await j("manifest.json"); if(!m) return;
  const th=m.dosyalar.filter(d=>/^data\/predictions\/.+\.json$/.test(d)).sort();
  if(!th.length) return;
  const haftalar=[...new Set(th.map(d=>d.split("/").pop().replace(".json","")))].sort();
  const son=haftalar[haftalar.length-1];
  let html="";
  for(const d of th.filter(x=>x.endsWith(son+".json"))){
    const persona=d.split("/")[2], veri=await j(d); if(!veri) continue;
    html+=`<h3 class="soluk" style="margin-top:14px">${kacir(persona)} — ${kacir(son)}</h3>`+
      veri.map(x=>`<div class="satir"><span>${kacir(x.ev)} ${kacir(x.skor)} ${kacir(x.dep)}</span><span class="soluk">${kacir(x.gerekce)}</span></div>`).join("");
  }
  if(html) el("tahminler").innerHTML=html;
  el("arsiv").innerHTML=haftalar.map(h=>`<span class="rozet" style="margin-right:8px">${kacir(h)}</span>`).join("")||el("arsiv").innerHTML;
}

async function ofis(){
  if(!el("kadro")) return;
  const r=await j("roster.json");
  if(r) el("kadro").innerHTML=r.map(a=>
    `<div class="kart"><h3>${kacir(a.ad)}</h3><p>${kacir(a.rol)} · vardiya: ${a.gunler.join(", ")}</p>
     <p><a href="#" data-prompt="${kacir(a.id)}">promptu gör</a></p><pre hidden id="p-${kacir(a.id)}"></pre></div>`).join("");
  document.querySelectorAll("[data-prompt]").forEach(x=>x.addEventListener("click",async e=>{
    e.preventDefault(); const id=x.dataset.prompt, pre=el("p-"+id);
    if(!pre.hidden){pre.hidden=true;return}
    pre.textContent=(await t("prompts/"+id+".md"))||"prompt yüklenemedi"; pre.hidden=false;
  }));
  const m=await j("manifest.json"); if(!m) return;
  const tut=m.dosyalar.filter(d=>d.startsWith("minutes/")).sort().reverse().slice(0,20);
  if(tut.length){
    el("tutanaklar").innerHTML=tut.map(d=>`<div class="satir"><a href="#" data-tutanak="${kacir(d)}">${kacir(d.replace("minutes/",""))}</a></div><pre hidden id="t-${kacir(d)}"></pre>`).join("");
    document.querySelectorAll("[data-tutanak]").forEach(x=>x.addEventListener("click",async e=>{
      e.preventDefault(); const d=x.dataset.tutanak, pre=document.getElementById("t-"+d);
      if(!pre.hidden){pre.hidden=true;return}
      pre.textContent=(await t(d))||"yüklenemedi"; pre.hidden=false;
    }));
  }
}

async function degisiklikler(){
  if(!el("gunluk")) return;
  const g=await j("gunluk.json");
  if(g&&g.length) el("gunluk").innerHTML="<table><tr><th>Tarih</th><th>Değişiklik</th></tr>"+
    g.map(x=>`<tr><td class="soluk">${kacir(x.tarih)}</td><td>${kacir(x.mesaj)}</td></tr>`).join("")+"</table>";
}

ortak(); pano(); tahmin(); ofis(); degisiklikler();
