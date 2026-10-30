export default function({data, setStateValue}) {
  const key='global-stage-radar:favorites:v2';
  try {
    if(!data.loaded) {
      let saved=[];
      try {saved=JSON.parse(sessionStorage.getItem(key)||'[]');} catch {}
      setStateValue('restored',Array.isArray(saved)?saved:[]);
    } else {
      sessionStorage.setItem(key,JSON.stringify(data.assets));
      document.documentElement.dataset.radarFavoritesSaved=JSON.stringify(data.assets.map(a=>a.id));
    }
  } catch {
    setStateValue('storage_error',true);
    if(!data.loaded)setStateValue('restored',[]);
  }
}
