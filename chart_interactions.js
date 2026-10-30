export default function ({data}) {
  // Public build identity for checking the existing hosted deployment.
  document.documentElement.dataset.radarRelease = data?.release || '';
  const charts = new Map();
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
    const scale = document.createElement('select');
    scale.className = 'radar-price-scale'; scale.setAttribute('aria-label', '가격 축 Linear / Log');
    for (const [value,label] of [['linear','선형'],['log','로그']]) {
      const o = document.createElement('option'); o.value=value; o.textContent=label; scale.append(o);
    }
    const toolbar=document.createElement('div');toolbar.className='radar-chart-controls';
    Object.assign(toolbar.style,{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:'8px',padding:'4px 0 8px'});
    const symbol=document.createElement('strong');symbol.textContent=gd.layout.title?.text?.replace(/<[^>]*>/g,'')||'';
    const label=document.createElement('label');label.textContent='가격 축 ';label.append(scale);
    const host=gd.closest('[class*="_asset_card"]')?.querySelector('.radar-axis-host');
    if(host) toolbar.append(label); else toolbar.append(symbol,label);
    Object.assign(scale.style,{color:'#172033',background:'#fff',border:'1px solid #94a3b8',borderRadius:'4px',padding:'4px'});
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
    let busy = false, lastFit = 0;
    function fit() {
      syncPeriod();
      if (busy && Date.now()-lastFit<1000 || !gd._fullLayout) return;
      const {candle,volume,dates}=read();
      const axis = gd._fullLayout.xaxis2;
      const limits = axis.range.map(x => new Date(x).getTime());
      const gaps=dates.slice(1).map((d,i)=>d-dates[i]).filter(d=>d>0).sort((a,b)=>a-b);
      const spacing=gaps.length?gaps[Math.floor(gaps.length/2)]:86400000;
      const last=dates[dates.length-1], right=Math.max(...limits), left=Math.min(...limits);
      const padding=left<=last && right>=last && right<last+3*spacing
        ? {'xaxis.range':[new Date(left).toISOString(),new Date(last+4*spacing).toISOString()],
           'xaxis2.range':[new Date(left).toISOString(),new Date(last+4*spacing).toISOString()]} : {};
      const indices = dates.map((d,i) => d >= Math.min(...limits) && d <= Math.max(...limits) ? i : -1).filter(i => i >= 0);
      const log = scale.value === 'log';
      const values = indices.flatMap(i => [candle.low[i], candle.high[i]]).filter(v => number(v) && (!log || v > 0)).map(v => log ? Math.log10(v) : Number(v));
      if (!values.length) {if(log) {scale.value='linear';scale.title='표시 구간에 양수 가격이 없어 선형 축을 사용합니다.';fit();} return;}
      let low=Math.min(...values), high=Math.max(...values);
      const pad=(high-low || Math.abs(high)*.05 || 1)*.08;
      const volumeMA=gd._fullData.find(t=>t.meta?.role==='volume_average');
      const vols=indices.flatMap(i => [volume?.y[i],volumeMA?.y[i]]).filter(v => number(v) && v >= 0);
      busy=true;lastFit=Date.now();
      Promise.resolve(window.Plotly.relayout(gd, {...padding,'hovermode':false, 'yaxis.type':scale.value,
        'yaxis.autorange':false, 'yaxis.range':[low-pad,high+pad], 'yaxis.fixedrange':true,
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
    const relayout=event=>{if(Object.keys(event).some(k=>k.startsWith('xaxis') || k==='autosize')) {hide();fit();}};
    gd.on('plotly_relayout',relayout);
    let previous=gd._fullData;
    const afterplot=()=>{if(previous!==gd._fullData) {previous=gd._fullData;if(!busy) fit();}};
    gd.on('plotly_afterplot',afterplot);
    document.addEventListener('scroll',hide,true);
    fit();
    const dispose=()=>{document.removeEventListener('scroll',hide,true);gd.removeListener?.('plotly_afterplot',afterplot);tip.remove();line.remove();toolbar.remove();gd.removeEventListener('mousemove',move);gd.removeEventListener('mouseleave',hide);gd.removeListener?.('plotly_relayout',relayout);};
    let signature=JSON.stringify([gd._fullLayout?.xaxis2.range,scale.value]);
    dispose.refresh=()=>{syncPeriod();if(!toolbar.isConnected && gd.isConnected){const nextHost=gd.closest('[class*="_asset_card"]')?.querySelector('.radar-axis-host');if(nextHost)nextHost.append(toolbar);else gd.before(toolbar);}symbol.textContent=gd.layout.title?.text?.replace(/<[^>]*>/g,'')||'';if(busy && Date.now()-lastFit>1000)busy=false;const next=JSON.stringify([gd._fullLayout?.xaxis2.range,scale.value]);if(!busy && (signature!==next || gd._fullLayout?.yaxis.type!==scale.value || gd._fullLayout?.yaxis.autorange!==false)) {signature=next;hide();fit();}};
    charts.set(gd,dispose);
  }
  const scan=()=>{
    for(const [gd,dispose] of charts) if(!gd.isConnected) {dispose();charts.delete(gd);}
    document.querySelectorAll('.js-plotly-plot').forEach(attach);
  };
  const timer=setInterval(scan,250); scan();
  return ()=>{clearInterval(timer);for(const dispose of charts.values()) dispose();};
}
