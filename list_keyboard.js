export default function() {
  const memory=window.__radarTableScroll ||= new Map();
  const panels=()=>[...document.querySelectorAll('[class*="_compact_list"].stVerticalBlock')];
  const key=panel=>[...panel.classList].find(c=>c.startsWith('st-key-'));
  const rows=panel=>[...panel.querySelectorAll('[class*="_table_row_"].stHorizontalBlock')];
  const picks=panel=>rows(panel).map(row=>row.querySelector('button[kind]')).filter(b=>b?.offsetParent&&!b.disabled);
  let pending=null,restoring=false;
  const capture=e=>{
    const panel=e.target.closest('[class*="_compact_list"].stVerticalBlock');
    if(panel){
      window.__radarActiveList=key(panel);
      const pos={top:panel.scrollTop,left:panel.scrollLeft};memory.set(key(panel),pos);
      pending={key:key(panel),...pos,outer:document.querySelector('[data-testid=stMain]')?.scrollTop,until:Date.now()+4000};
    } else if(e.type==='click') {window.__radarActiveList=null;pending=null;}
  };
  const selectRow=e=>{
    if(e.target.closest('button,a,input,select,textarea,[role=button]'))return;
    const row=e.target.closest('[class*="_table_row_"].stHorizontalBlock');
    row?.querySelector('button[kind]')?.click();
  };
  const keyboard=e=>{
    if(!['ArrowDown','ArrowUp'].includes(e.key)||['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)||e.target.isContentEditable)return;
    const panel=document.querySelector('.'+window.__radarActiveList);
    if(!panel)return;
    const buttons=picks(panel);if(!buttons.length)return;
    const current=buttons.findIndex(b=>b.getAttribute('kind')==='primary');
    const next=Math.max(0,Math.min(buttons.length-1,current+(e.key==='ArrowDown'?1:-1)));
    const button=buttons[next];e.preventDefault();
    const p=panel.getBoundingClientRect(),b=button.getBoundingClientRect();
    if(b.bottom>p.bottom)panel.scrollTop+=b.bottom-p.bottom+6;
    if(b.top<p.top+34)panel.scrollTop-=p.top+34-b.top+6;
    button.click();
  };
  const scroll=e=>{
    if(restoring)return;
    const panel=e.target;
    if(panel.matches?.('[class*="_compact_list"].stVerticalBlock'))memory.set(key(panel),{top:panel.scrollTop,left:panel.scrollLeft});
  };
  const restore=()=>{
    restoring=true;
    for(const panel of panels()){
      if(!panel.dataset.radarTableReady){
        const pos=memory.get(key(panel));if(pos){panel.scrollTop=pos.top;panel.scrollLeft=pos.left;}
        panel.dataset.radarTableReady='true';
      }
    }
    if(pending){
      const panel=document.querySelector('.'+pending.key);
      if(panel){panel.scrollTop=pending.top;panel.scrollLeft=pending.left;}
      const main=document.querySelector('[data-testid=stMain]');if(main)main.scrollTop=pending.outer;
      if(Date.now()>pending.until)pending=null;
    }
    restoring=false;
  };
  const cancel=()=>{pending=null;};
  document.addEventListener('click',capture,true);document.addEventListener('focusin',capture);
  document.addEventListener('click',selectRow);document.addEventListener('keydown',keyboard);
  document.addEventListener('scroll',scroll,true);document.addEventListener('wheel',cancel,{passive:true});
  document.addEventListener('touchstart',cancel,{passive:true});
  const timer=setInterval(restore,100);
  return ()=>{
    clearInterval(timer);document.removeEventListener('click',capture,true);document.removeEventListener('focusin',capture);
    document.removeEventListener('click',selectRow);document.removeEventListener('keydown',keyboard);
    document.removeEventListener('scroll',scroll,true);document.removeEventListener('wheel',cancel);
    document.removeEventListener('touchstart',cancel);
  };
}
