export default function({data, setStateValue}) {
  const key='global-stage-radar:preferences:v1';
  try {
    if(data.read) setStateValue('restored',sessionStorage.getItem(key)||'');
    if(data.write) sessionStorage.setItem(key,data.raw);
  } catch {
    // URL preferences and the current session still work when storage is blocked.
    if(data.read) setStateValue('restored','');
  }
}
