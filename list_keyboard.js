export default function() {
  const listKey=e=>{
    const panel=e.target.closest('[class*="_compact_list"]');
    return panel && [...panel.classList].find(c=>c.startsWith('st-key-'));
  };
  const focus=e=>{const key=listKey(e);if(key || e.type==='click') window.__radarActiveList=key;};
  const keyboard=e=>{
    if(!['ArrowDown','ArrowUp'].includes(e.key) || ['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName) || e.target.isContentEditable) return;
    const panel=document.querySelector('.'+window.__radarActiveList);
    if(!panel) return;
    const buttons=[...panel.querySelectorAll('button[kind]')].filter(b=>b.offsetParent && !b.disabled);
    if(!buttons.length) return;
    const current=buttons.findIndex(b=>b.getAttribute('kind')==='primary');
    const next=Math.max(0,Math.min(buttons.length-1,current+(e.key==='ArrowDown'?1:-1)));
    const button=buttons[next];
    e.preventDefault();
    const p=panel.getBoundingClientRect(),b=button.getBoundingClientRect();
    if(b.bottom>p.bottom) panel.scrollTop+=b.bottom-p.bottom+6;
    if(b.top<p.top) panel.scrollTop-=p.top-b.top+6;
    button.click();
  };
  document.addEventListener('focusin',focus); document.addEventListener('click',focus);
  document.addEventListener('keydown',keyboard);
  return ()=>{document.removeEventListener('focusin',focus);document.removeEventListener('click',focus);document.removeEventListener('keydown',keyboard);};
}
