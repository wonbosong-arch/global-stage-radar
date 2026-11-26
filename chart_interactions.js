export default function ({data}) {
  // v2 invokes the renderer on data updates; its returned cleanup is only
  // guaranteed on unmount. Retire the previous document-wide controller first.
  window.__radarChartInteractionsCleanup?.();
  // Public build identity for checking the existing hosted deployment.
  document.documentElement.dataset.radarRelease = data?.release || '';
  const charts = new Map();
  // Keep the date window through Streamlit widget replacements in this page.
  const comparisonRanges = window.__radarComparisonRanges ??= new Map();
  const number = v => Number.isFinite(Number(v)) && v !== null;
  function attach(gd) {
    if(charts.has(gd)) {charts.get(gd).refresh();return;}
    if (!gd._fullLayout || !gd.data?.some(t => t.type === 'candlestick')) return;
    function read() {
      const candle=gd._fullData.find(t=>t.type==='candlestick');
      return {candle,volume:gd._fullData.find(t=>t.type==='bar'),volumeMA:gd._fullData.find(t=>t.meta?.role==='volume_average'),dates:Array.from(candle.x,x=>new Date(x).getTime())};
    }
    const tip = document.createElement('div');
    tip.className = 'radar-cursor-info';
    Object.assign(tip.style, {position:'fixed', display:'none', pointerEvents:'none', zIndex:99999,
      background:'#fff', color:'#172033', border:'1px solid #94a3b8', borderRadius:'6px',
      padding:'8px', font:'12px sans-serif', whiteSpace:'pre-line', boxShadow:'0 2px 8px #0002'});
    document.body.append(tip);
    const line = document.createElement('div');
    line.className = 'radar-crosshair';
    Object.assign(line.style, {position:'absolute', pointerEvents:'none', display:'none', borderLeft:'1px dotted #7f8790', zIndex:10});
    const scale = document.createElement('div');
    const viewportCard = gd.closest('.st-key-markets_commodities_selected_chart_asset_card, .st-key-stocks_selected_chart_asset_card, .st-key-sectors_selected_chart_asset_card, .st-key-china_research_selected_chart_asset_card, .st-key-stage2_analysis [class*="candidate_quick_preview_chart_asset_card"]');
    const host=gd.closest('[class*="_asset_card"]')?.querySelector('.radar-axis-host');
    scale.className = 'radar-price-scale';
    if (!host) scale.setAttribute('role','radiogroup');
    scale.setAttribute('aria-label', '가격 축');
    let scaleValue='linear';
    if (host) {
      const button=document.createElement('button');
      button.type='button';
      button.textContent='로그';
      button.setAttribute('role','switch');
      button.onclick=()=>{
        scale.value=scaleValue==='log'?'linear':'log';
        scale.dispatchEvent(new Event('change',{bubbles:true}));
      };
      scale.append(button);
    } else for (const [value,label] of [['linear','선형'],['log','로그']]) {
      const button = document.createElement('button');
      button.type='button';button.textContent=label;button.dataset.value=value;
      button.setAttribute('role','radio');
      button.onclick=()=>{scale.value=value;scale.dispatchEvent(new Event('change',{bubbles:true}));};
      button.onkeydown=e=>{
        if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
        e.preventDefault();
        const next=['ArrowLeft','Home'].includes(e.key)?'linear':'log';
        const target=scale.querySelector(`[data-value="${next}"]`);target.click();target.focus();
      };
      scale.append(button);
    }
    Object.defineProperty(scale,'value',{get:()=>scaleValue,set:value=>{
      scaleValue=value;scale.dataset.value=value;
      for(const button of scale.children) {
        const selected=host ? value==='log' : button.dataset.value===value;
        button.setAttribute('aria-checked',String(selected));
        button.tabIndex=host||selected?0:-1;
      }
    }});
    scale.value='linear';
    const toolbar=document.createElement('div');toolbar.className='radar-chart-controls';
    Object.assign(toolbar.style,{display:'flex',justifyContent:'flex-start',alignItems:'center',flexWrap:'wrap',gap:'8px',padding:'4px 0 8px'});
    const symbol=document.createElement('strong');symbol.textContent=gd.layout.title?.text?.replace(/<[^>]*>/g,'')||'';
    if(host) toolbar.append(scale); else toolbar.append(symbol,scale);
    const style=document.createElement('style');
    style.textContent=`.radar-price-scale{display:flex;align-items:center;flex-wrap:nowrap;font:14px sans-serif;}
      .radar-price-scale button{box-sizing:border-box;border:1px solid #94a3b8;border-radius:0;background:var(--background-color,#fff);color:var(--text-color,#172033);padding:2px 8px;min-height:30px;line-height:1.6;cursor:pointer;font:inherit;}
      .radar-price-scale button+button{border-left:0;}
      .radar-price-scale button[aria-checked=true]{background:#0f766e;color:white;}
      .radar-price-scale button:focus-visible{outline:2px solid #0f766e;outline-offset:2px;}`;
    toolbar.append(style);
    const widget=[...(gd.closest('[class*=st-key-]')?.classList||[])].find(c=>c.startsWith('st-key-')) || gd.layout.title?.text;
    let storageKey, currentPeriod;
    function syncPeriod() {
      const period=gd._fullData.find(t=>t.type==='candlestick')?.name || '일봉';
      if(period===currentPeriod)return;
      currentPeriod=period;storageKey='radar-price-scale:'+widget+':'+period;
      scale.value=period==='주봉'?'log':'linear';
      try {const saved=sessionStorage.getItem(storageKey);if(['linear','log'].includes(saved))scale.value=saved;} catch {}
    }
    syncPeriod();
    gd.style.position='relative'; gd.append(line);if(host)host.append(toolbar);else gd.before(toolbar);
    let busy = false, lastFit = 0, applyingComparisonRange = false;
    const comparisonPeriod = () => gd.layout.meta?.comparison_period;
    function syncComparisonRange() {
      const period = comparisonPeriod();
      const axis = gd._fullLayout?.xaxis2;
      // Plotly changes its working range during a drag, before it emits the committed range.
      if (!period || !axis?.range || gd._dragging) return;
      if (!comparisonRanges.has(period)) comparisonRanges.set(period, [...axis.range]);
      const range = comparisonRanges.get(period);
      if (range.every((date, i) => axis.d2l(date) === axis.d2l(axis.range[i]))) return;
      if (busy || applyingComparisonRange) return;
      applyingComparisonRange = true;
      hide();
      Promise.resolve(window.Plotly.relayout(gd, {'xaxis2.range':range}))
        .finally(() => {
          applyingComparisonRange = false;
          if (gd.isConnected) fit();
        });
    }
    function fit() {
      syncPeriod();
      if (busy && Date.now()-lastFit<1000 || !gd._fullLayout) return;
      if (comparisonPeriod() && gd._dragging) return;
      const {candle,volume,dates}=read();
      const axis = gd._fullLayout.xaxis2;
      const limits = axis.range.map(x => new Date(x).getTime());
      const gaps=dates.slice(1).map((d,i)=>d-dates[i]).filter(d=>d>0).sort((a,b)=>a-b);
      const spacing=gaps.length?gaps[Math.floor(gaps.length/2)]:86400000;
      const last=dates[dates.length-1], right=Math.max(...limits), left=Math.min(...limits);
      const padding=!comparisonPeriod() && left<=last && right>=last && right<last+3*spacing
        ? {'xaxis.range':[new Date(left).toISOString(),new Date(last+4*spacing).toISOString()],
           'xaxis2.range':[new Date(left).toISOString(),new Date(last+4*spacing).toISOString()]} : {};
      const indices = dates.map((d,i) => d >= Math.min(...limits) && d <= Math.max(...limits) ? i : -1).filter(i => i >= 0);
      if (comparisonPeriod() && !indices.length) return;
      const log = scale.value === 'log';
      const values = indices.flatMap(i => [candle.low[i], candle.high[i]]).filter(v => number(v) && (!log || v > 0)).map(v => log ? Math.log10(v) : Number(v));
      if (!values.length) {if(log) {scale.value='linear';scale.title='표시 구간에 양수 가격이 없어 선형 축을 사용합니다.';fit();} return;}
      let low=Math.min(...values), high=Math.max(...values);
      const pad=(high-low || Math.abs(high)*.05 || 1)*.08;
      const range=[low-pad,high+pad];
      let priceTicks={};
      if (host) {
        if (log) {
          // Numeric dtick is measured in log10 units, so labels are equally spaced.
          const targetTicks=Math.max(3,Math.min(8,Math.round(gd._fullLayout.yaxis._length/45)));
          const step=(range[1]-range[0])/targetTicks;
          const magnitude=10**Math.floor(Math.log10(step));
          const logStep=[1,2,2.5,5,10].map(multiplier=>multiplier*magnitude).find(interval=>interval>=step);
          priceTicks={'yaxis.tickmode':'linear', 'yaxis.tick0':0, 'yaxis.dtick':logStep, 'yaxis.tickformat':'.4~g'};
        } else {
          priceTicks={'yaxis.tickmode':'auto', 'yaxis.dtick':null, 'yaxis.tickformat':null};
        }
      }
      const volumeMA=gd._fullData.find(t=>t.meta?.role==='volume_average');
      const vols=indices.flatMap(i => [volume?.y[i],volumeMA?.y[i]]).filter(v => number(v) && v >= 0);
      busy=true;lastFit=Date.now();
      Promise.resolve(window.Plotly.relayout(gd, {...padding,...priceTicks,'hovermode':false, 'yaxis.type':scale.value,
        'yaxis.autorange':false, 'yaxis.range':range, 'yaxis.fixedrange':true,
        'yaxis2.autorange':false, 'yaxis2.range':[0, Math.max(1,...vols)*1.08], 'yaxis2.fixedrange':true}))
        .finally(() => {busy=false;});
    }
    function hide() {tip.style.display='none'; line.style.display='none';}
    function move(e) {
      const {candle,volume,volumeMA,dates}=read();
      const box=gd.getBoundingClientRect(), f=gd._fullLayout, ax=f.xaxis2;
      const x=e.clientX-box.left, y=e.clientY-box.top;
      const top=f.yaxis._offset, bottom=f.yaxis2._offset+f.yaxis2._length;
      if (x<ax._offset || x>ax._offset+ax._length || y<top || y>bottom) return hide();
      const target=new Date(ax.p2d(x-ax._offset)).getTime();
      let lo=0, hi=dates.length-1;
      while (lo<hi) {const m=(lo+hi)>>1; if(dates[m]<target) lo=m+1; else hi=m;}
      const i=lo>0 && Math.abs(dates[lo-1]-target)<Math.abs(dates[lo]-target)?lo-1:lo;
      const fmt=v=>number(v)?Number(v).toLocaleString(undefined,{maximumFractionDigits:2}):'—';
      const change=i && candle.close[i-1] > 0 ? (candle.close[i]/candle.close[i-1]-1)*100 : null;
      tip.textContent=`${new Date(dates[i]).toISOString().slice(0,10)}\n시가: ${fmt(candle.open[i])} · 고가: ${fmt(candle.high[i])}\n저가: ${fmt(candle.low[i])} · 종가: ${fmt(candle.close[i])}\n전일/전주 대비: ${fmt(change)}%\n거래량: ${fmt(volume?.y[i])}${volumeMA?'\n'+volumeMA.name+': '+fmt(volumeMA.y[i]):''}`;
      tip.dataset.index=String(i); tip.style.display='block';
      const r=tip.getBoundingClientRect(), gap=12;
      const px=e.clientX+r.width+gap<innerWidth?e.clientX+gap:e.clientX-r.width-gap;
      const above=y<top+f.yaxis._length/2;
      let py=above?e.clientY-r.height-gap:e.clientY+gap;
      if(py<4) py=e.clientY+gap;
      if(py+r.height>innerHeight-4) py=e.clientY-r.height-gap;
      tip.style.left=Math.max(4,px)+'px'; tip.style.top=Math.max(4,py)+'px';
      Object.assign(line.style,{display:'block',left:(ax._offset+ax.d2p(candle.x[i]))+'px',top:top+'px',height:(bottom-top)+'px'});
    }
    scale.onchange=()=>{try{sessionStorage.setItem(storageKey,scale.value);}catch{} hide(); fit(); };
    gd.addEventListener('mousemove', move); gd.addEventListener('mouseleave', hide);
    const relayout=event=>{
      const changesTime = Object.keys(event).some(key => key.startsWith('xaxis'));
      if (changesTime && comparisonPeriod()) {
        if (applyingComparisonRange) return;
        comparisonRanges.set(comparisonPeriod(), [...gd._fullLayout.xaxis2.range]);
        for (const [peer, dispose] of charts) {
          if (peer !== gd) dispose.syncComparisonRange();
        }
      }
      if (changesTime || 'autosize' in event) {hide();fit();}
    };
    gd.on('plotly_relayout',relayout);
    let previous=gd._fullData;
    const afterplot=()=>{if(previous!==gd._fullData) {previous=gd._fullData;if(!busy) fit();}};
    gd.on('plotly_afterplot',afterplot);
    document.addEventListener('scroll',hide,true);
    syncComparisonRange();
    if (!applyingComparisonRange) fit();
    const dispose=()=>{document.removeEventListener('scroll',hide,true);gd.removeListener?.('plotly_afterplot',afterplot);tip.remove();line.remove();toolbar.remove();gd.removeEventListener('mousemove',move);gd.removeEventListener('mouseleave',hide);gd.removeListener?.('plotly_relayout',relayout);};
    let signature=JSON.stringify([gd._fullLayout?.xaxis2.range,scale.value]);
    dispose.syncComparisonRange = syncComparisonRange;
    dispose.refresh = () => {
      syncPeriod();
      if (viewportCard) {
        const height=Math.max(260, Math.floor(viewportCard.getBoundingClientRect().bottom-gd.getBoundingClientRect().top-10));
        if (gd.layout.height!==height && !busy) {
          viewportCard.style.setProperty('--stocks-plot-height',height+'px');
          window.Plotly.relayout(gd,{height});
        }
      }
      const nextHost = gd.closest('[class*="_asset_card"]')?.querySelector('.radar-axis-host');
      if (nextHost && toolbar.parentElement !== nextHost) nextHost.append(toolbar);
      else if (!toolbar.isConnected && gd.isConnected) gd.before(toolbar);
      symbol.textContent = gd.layout.title?.text?.replace(/<[^>]*>/g,'') || '';
      if (busy && Date.now()-lastFit > 1000) busy = false;
      syncComparisonRange();
      const next = JSON.stringify([gd._fullLayout?.xaxis2.range, scale.value]);
      if (!busy && !applyingComparisonRange && (signature !== next
          || gd._fullLayout?.yaxis.type !== scale.value
          || (!comparisonPeriod() && gd._fullLayout?.yaxis.autorange !== false))) {
        signature = next;
        hide();
        fit();
      }
    };
    charts.set(gd,dispose);
  }
  const scan=()=>{
    const split=document.querySelector('.st-key-markets_commodities_analysis_split, .st-key-stocks_analysis_split, .st-key-sectors_analysis_split, .st-key-china_research_analysis_split, .st-key-stage2_analysis [class*="candidate_quick_analysis_split"]');
    const main=split?.closest('[data-testid=stMain]');
    if (main) {
      // Use the pane's document offset so scrolling to disclosures does not resize it.
      const height=innerWidth<=900 ? 390 : Math.max(390, Math.floor(main.getBoundingClientRect().bottom
        -split.getBoundingClientRect().top-main.scrollTop-8));
      split.style.setProperty('--stocks-pane-height',height+'px');
    }
    for(const [gd,dispose] of charts) if(!gd.isConnected) {dispose();charts.delete(gd);}
    document.querySelectorAll('.js-plotly-plot').forEach(attach);
  };
  const timer=setInterval(scan,250); scan();
  let stopped=false;
  const cleanup=()=>{
    if(stopped)return;stopped=true;
    clearInterval(timer);for(const dispose of charts.values())dispose();charts.clear();
    if(window.__radarChartInteractionsCleanup===cleanup)delete window.__radarChartInteractionsCleanup;
  };
  window.__radarChartInteractionsCleanup=cleanup;
  return cleanup;
}
