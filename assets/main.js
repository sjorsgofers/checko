/* Karateschool Yin Yang — interactie & animaties */
(function(){
  const header=document.querySelector('.site-header');
  const onScroll=()=>header.classList.toggle('scrolled',window.scrollY>40);
  onScroll();addEventListener('scroll',onScroll,{passive:true});

  // Mobiel menu
  const burger=document.querySelector('.burger');
  const menu=document.querySelector('.mobile-menu');
  if(burger&&menu){
    burger.addEventListener('click',()=>{
      const open=document.body.classList.toggle('menu-open');
      menu.classList.toggle('open',open);
      burger.setAttribute('aria-expanded',open);
      if(open)header.classList.add('scrolled');
    });
    menu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
      document.body.classList.remove('menu-open');menu.classList.remove('open');
    }));
  }

  // Scroll-reveal
  const io=new IntersectionObserver(entries=>{
    entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});
  },{threshold:.12,rootMargin:'0px 0px -40px 0px'});
  document.querySelectorAll('.reveal,.timeline').forEach(el=>io.observe(el));

  // Tellers
  const counters=document.querySelectorAll('[data-count]');
  const cio=new IntersectionObserver(entries=>{
    entries.forEach(e=>{
      if(!e.isIntersecting)return;cio.unobserve(e.target);
      const el=e.target,end=parseInt(el.dataset.count,10),dur=1400,start=performance.now();
      const step=now=>{const p=Math.min(1,(now-start)/dur),v=Math.round(end*(1-Math.pow(1-p,3)));el.textContent=v;if(p<1)requestAnimationFrame(step);};
      requestAnimationFrame(step);
    });
  },{threshold:.5});
  counters.forEach(c=>cio.observe(c));

  // Aftellen naar het ONK — zondag 1 november 2026, 08:00
  const cd=document.getElementById('countdown');
  if(cd){
    const target=new Date(2026,10,1,8,0,0).getTime();
    const tick=()=>{
      let d=Math.max(0,target-Date.now());
      const days=Math.floor(d/864e5);d-=days*864e5;
      const hrs=Math.floor(d/36e5);d-=hrs*36e5;
      const min=Math.floor(d/6e4);d-=min*6e4;
      const sec=Math.floor(d/1e3);
      cd.querySelector('[data-d]').textContent=days;
      cd.querySelector('[data-h]').textContent=String(hrs).padStart(2,'0');
      cd.querySelector('[data-m]').textContent=String(min).padStart(2,'0');
      cd.querySelector('[data-s]').textContent=String(sec).padStart(2,'0');
    };
    tick();setInterval(tick,1000);
  }

  // Formulieren: bouwen een e-mail op naar kyokusyinyang@gmail.com
  document.querySelectorAll('form[data-mail]').forEach(form=>{
    form.addEventListener('submit',ev=>{
      ev.preventDefault();
      const subject=form.dataset.mail;
      const lines=[];
      form.querySelectorAll('input,select,textarea').forEach(f=>{
        if(!f.name)return;
        if(f.type==='checkbox'){lines.push(f.name+': '+(f.checked?'ja':'nee'));return;}
        if(f.type==='radio'){if(f.checked)lines.push(f.name+': '+f.value);return;}
        lines.push(f.name+': '+f.value);
      });
      location.href='mailto:kyokusyinyang@gmail.com?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(lines.join('\n'));
    });
  });

  // Actieve navigatie
  const here=location.pathname.split('/').pop()||'index.html';
  document.querySelectorAll('.nav a,.mobile-menu a').forEach(a=>{
    if(a.getAttribute('href')===here)a.setAttribute('aria-current','page');
  });
})();
