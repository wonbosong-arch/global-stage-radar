export default function() {
  let pending=null;
  const heights=new Map();
  const main=()=>document.querySelector('[data-testid=stMain]');
  function capture(e) {
    const widget=e.target.closest('[class*=st-key-]');
    const key=widget && [...widget.classList].find(c=>/st-key-.*_grid_(next|prev)$/.test(c));
    if(!key || e.target.closest('button')?.disabled)return;
    const canvasKey=key.replace(/_(next|prev)$/,'_canvas');
    const canvas=document.querySelector('.'+canvasKey);
    if(!canvas)return;
    const first=canvas.querySelector('[data-testid=stPlotlyChart]')?.closest('[data-testid=stElementContainer]');
    pending={key:canvasKey,scroll:main().scrollTop,first:first?.className,until:Date.now()+2500};
    main().style.overflowAnchor='none';
    heights.set(canvasKey,Math.max(canvas.getBoundingClientRect().height,heights.get(canvasKey)||0));
    canvas.style.minHeight=heights.get(canvasKey)+'px';
  }
  function settle() {
    for(const [key,height] of heights) {
      const canvas=document.querySelector('.'+key);
      if(canvas)canvas.style.minHeight=height+'px';
    }
    if(!pending)return;
    const canvas=document.querySelector('.'+pending.key);
    const first=canvas?.querySelector('[data-testid=stPlotlyChart]')?.closest('[data-testid=stElementContainer]');
    if(first && first.className!==pending.first && canvas.querySelector('.radar-price-scale')) {
      main().scrollTop=pending.scroll;
      // Keep the restoration until all figures have been initialized.
      if(Date.now()>pending.until && [...canvas.querySelectorAll('[data-testid=stPlotlyChart]')].every(e=>e.querySelector('.radar-price-scale')))pending=null;
    }
  }
  function resize(){pending=null;for(const key of heights.keys()){const c=document.querySelector('.'+key);if(c)c.style.minHeight='';}heights.clear();}
  document.addEventListener('click',capture,true);window.addEventListener('resize',resize);
  const timer=setInterval(settle,100);
  return ()=>{clearInterval(timer);document.removeEventListener('click',capture,true);window.removeEventListener('resize',resize);};
}
