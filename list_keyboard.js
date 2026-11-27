const nameCell = '[class*="st-key-asset_name_"]';
const nameTarget = nameCell + ' button, .radar-table-name';

function clippedName(anchor) {
  const fullLabel = anchor.matches('button')
    ? anchor.closest(nameCell).querySelector('.radar-table-full-label')
    : null;
  if (fullLabel) return fullLabel.textContent;
  const label = anchor.querySelector('p') || anchor;
  return label.scrollWidth > label.clientWidth ? label.textContent : '';
}

function placeTooltip(tooltip, anchor, panel, panels) {
  const gap = 8;
  const cell = anchor.getBoundingClientRect();
  const table = panel.getBoundingClientRect();
  const {width, height} = tooltip.getBoundingClientRect();
  const viewportWidth = document.documentElement.clientWidth;
  const viewportHeight = document.documentElement.clientHeight;
  const x = Math.max(gap, Math.min(cell.left, viewportWidth - width - gap));
  const y = Math.max(gap, Math.min(cell.top, viewportHeight - height - gap));
  const header = document.querySelector('.st-key-analysis_header');
  const occupied = [...panels, header].filter(Boolean).map(node => node.getBoundingClientRect());
  const positions = [
    [table.right + gap, y], [x, table.bottom + gap],
    [x, table.top - height - gap], [table.left - width - gap, y],
  ];
  const position = positions.find(([left, top]) => {
    const right = left + width;
    const bottom = top + height;
    return left >= gap && top >= gap && right <= viewportWidth - gap && bottom <= viewportHeight - gap
      && !occupied.some(box => left < box.right && right > box.left
        && top < box.bottom && bottom > box.top);
  });
  if (!position) return false;
  const [left, top] = position;
  Object.assign(tooltip.style, {left: left + 'px', top: top + 'px', visibility: 'visible'});
  return true;
}

export default function() {
  window.__radarTableInteractionsCleanup?.();
  const memory=window.__radarTableScroll ||= new Map();
  const panels=()=>[...document.querySelectorAll('[class*="_compact_list"].stVerticalBlock')];
  const key=panel=>[...panel.classList].find(c=>c.startsWith('st-key-'));
  const rows=panel=>[...panel.querySelectorAll('[class*="_table_row_"].stHorizontalBlock')];
  const ticker=row=>row.querySelector('button[kind]:not([class*="_table_star_"] button)');
  const picks=panel=>rows(panel).map(ticker).filter(b=>b?.offsetParent&&!b.disabled);
  const signature=panel=>[...panel.querySelectorAll('button[kind]')].map(b=>b.textContent+':'+b.getAttribute('kind')).join('|');
  const state=window.__radarTableState ||= {pending:null};
  const tooltip = document.createElement('div');
  tooltip.className = 'radar-table-tooltip';
  tooltip.setAttribute('role', 'tooltip');
  let anchor = null;
  let tooltipPanel = null;
  const hideTooltip = () => {
    tooltip.remove();
    anchor = null;
    tooltipPanel = null;
  };
  const hoverName = event => {
    if (event.pointerType !== 'mouse') return;
    const target = event.target.closest(nameTarget);
    if (target === anchor) return;
    hideTooltip();
    const panel = target?.closest('[class*="_compact_list"].stVerticalBlock');
    if (!panel || target.closest('[data-stale="true"]')) return;
    const name = clippedName(target);
    if (!name) return;
    tooltip.textContent = name;
    tooltip.style.visibility = 'hidden';
    document.body.append(tooltip);
    if (placeTooltip(tooltip, target, panel, panels())) {
      anchor = target;
      tooltipPanel = panel;
    } else {
      hideTooltip();
    }
  };
  const leaveName = event => {
    if (anchor?.contains(event.target) && !anchor.contains(event.relatedTarget)) hideTooltip();
  };
  let restoring=false;
  const capture=e=>{
    if(e.type==='click')hideTooltip();
    const panel=e.target.closest('[class*="_compact_list"].stVerticalBlock');
    if(panel){
      window.__radarActiveList=key(panel);
      const pos={top:panel.scrollTop,left:panel.scrollLeft};memory.set(key(panel),pos);
      state.pending={key:key(panel),signature:signature(panel),...pos,outer:document.querySelector('[data-testid=stMain]')?.scrollTop,until:Date.now()+4000};
    } else if(e.type==='click') {window.__radarActiveList=null;state.pending=null;}
  };
  const selectRow=e=>{
    if(e.target.closest('button,a,input,select,textarea,[role=button]'))return;
    const row=e.target.closest('[class*="_table_row_"].stHorizontalBlock');
    if(row)ticker(row)?.click();
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
    hideTooltip();
    if(restoring)return;
    const panel=e.target;
    if(panel.matches?.('[class*="_compact_list"].stVerticalBlock')){
      memory.set(key(panel),{top:panel.scrollTop,left:panel.scrollLeft});
      if(state.pending?.key===key(panel)){state.pending.top=panel.scrollTop;state.pending.left=panel.scrollLeft;}
    }
  };
  const restore=()=>{
    restoring=true;
    for(const panel of panels()){
      if(!panel.dataset.radarTableReady){
        const pos=memory.get(key(panel));if(pos){panel.scrollTop=pos.top;panel.scrollLeft=pos.left;}
        panel.dataset.radarTableReady='true';
      }
    }
    const pending=state.pending;
    if(pending){
      const panel=document.querySelector('.'+pending.key);
      // Restore once when the server's new selection/sort/star arrives. Holding
      // scroll on a timer would fight a user's subsequent scrollbar movement.
      if(panel && signature(panel)!==pending.signature){
        panel.scrollTop=pending.top;panel.scrollLeft=pending.left;
        const main=document.querySelector('[data-testid=stMain]');if(main)main.scrollTop=pending.outer;
        state.pending=null;
      } else if(Date.now()>pending.until)state.pending=null;
    }
    restoring=false;
  };
  const cancel=()=>{state.pending=null;hideTooltip();};
  const tooltipResetEvents = ['input', 'change', 'keydown'];
  for (const event of tooltipResetEvents) document.addEventListener(event, hideTooltip, true);
  // Scrolling can generate pointerover on a row that slides under a still cursor.
  document.addEventListener('pointermove', hoverName);
  document.addEventListener('pointerout', leaveName);
  window.addEventListener('resize', hideTooltip);
  window.addEventListener('blur', hideTooltip);
  document.addEventListener('click',capture,true);document.addEventListener('focusin',capture);
  document.addEventListener('click',selectRow);document.addEventListener('keydown',keyboard);
  document.addEventListener('scroll',scroll,true);document.addEventListener('wheel',cancel,{passive:true});
  document.addEventListener('touchstart',cancel,{passive:true});
  const observer=new MutationObserver(records=>{
    if (anchor && (!anchor.isConnected || anchor.closest('[data-stale="true"]')
        || records.some(record => tooltipPanel.contains(record.target)))) hideTooltip();
    if(state.pending)restore();
  });
  observer.observe(document.body,{childList:true,subtree:true,characterData:true,
    attributes:true,attributeFilter:['data-stale']});
  restore();
  const timer=setInterval(restore,100);
  let stopped=false;
  const cleanup=()=>{
    if(stopped)return;stopped=true;
    hideTooltip();
    for (const event of tooltipResetEvents) document.removeEventListener(event, hideTooltip, true);
    document.removeEventListener('pointermove', hoverName);
    document.removeEventListener('pointerout', leaveName);
    window.removeEventListener('resize', hideTooltip);
    window.removeEventListener('blur', hideTooltip);
    observer.disconnect();clearInterval(timer);document.removeEventListener('click',capture,true);document.removeEventListener('focusin',capture);
    document.removeEventListener('click',selectRow);document.removeEventListener('keydown',keyboard);
    document.removeEventListener('scroll',scroll,true);document.removeEventListener('wheel',cancel);
    document.removeEventListener('touchstart',cancel);
    if(window.__radarTableInteractionsCleanup===cleanup)delete window.__radarTableInteractionsCleanup;
  };
  window.__radarTableInteractionsCleanup=cleanup;
  return cleanup;
}
