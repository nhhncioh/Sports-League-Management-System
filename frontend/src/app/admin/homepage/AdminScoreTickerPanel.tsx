/* src/app/admin/homepage/AdminScoreTickerPanel.tsx */
"use client";
import { useEffect, useState } from "react";
import { TickerTheme } from "@/src/lib/tickerApi";

function ColorRow({label,value,onChange}:{label:string;value:string;onChange:(v:string)=>void}){
  return (
    <label className="flex items-center gap-2">
      <span className="w-36">{label}</span>
      <input type="color" value={value} onChange={(e)=>onChange(e.target.value)} />
      <input className="border rounded px-2 py-1 text-sm w-32" value={value} onChange={(e)=>onChange(e.target.value)} />
    </label>
  );
}
function RangeRow({label,min,max,value,onChange}:{label:string;min:number;max:number;value:number;onChange:(n:number)=>void}){
  return (
    <label className="flex items-center gap-2">
      <span className="w-36">{label}</span>
      <input type="range" min={min} max={max} value={value} onChange={(e)=>onChange(Number(e.target.value))} className="flex-1"/>
      <input className="border rounded px-2 py-1 text-sm w-20 text-right" value={value} onChange={(e)=>onChange(Number(e.target.value)||0)} />
    </label>
  );
}

export default function AdminScoreTickerPanel({ leagueId }:{leagueId:string}){
  const [enabled, setEnabled] = useState(false);
  const [theme, setTheme] = useState<TickerTheme>({bg:"#0b0d12",fg:"#ffffff",accent:"#ffc107",height:40,speed:55,showLogos:true,showStatus:true});
  const [saving, setSaving] = useState(false);

  useEffect(()=>{ (async()=>{
      const r = await fetch(`/api/ticker/${leagueId}`).then(r=>r.json());
      if (r?.theme) setTheme((t)=>({ ...t, ...r.theme }));
      setEnabled(!!r?.enabled);
  })(); }, [leagueId]);

  const save = async ()=>{
    setSaving(true);
    await fetch(`/api/ticker/admin/${leagueId}/settings`, {
      method:"PUT", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ enabled, theme })
    });
    setSaving(false);
  };

  return (
    <div className="grid gap-4">
      <div className="flex items-center gap-2">
        <input id="enable" type="checkbox" checked={enabled} onChange={(e)=>setEnabled(e.target.checked)} />
        <label htmlFor="enable" className="font-medium">Enable score ticker on homepage</label>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="grid gap-3 p-3 rounded border">
          <h3 className="font-semibold">Appearance</h3>
          <ColorRow label="Background" value={theme.bg} onChange={v=>setTheme({...theme,bg:v})}/>
          <ColorRow label="Text" value={theme.fg} onChange={v=>setTheme({...theme,fg:v})}/>
          <ColorRow label="Accent" value={theme.accent} onChange={v=>setTheme({...theme,accent:v})}/>
          <RangeRow label="Height (px)" min={28} max={72} value={theme.height} onChange={v=>setTheme({...theme,height:v})}/>
          <RangeRow label="Scroll speed (px/s)" min={20} max={140} value={theme.speed} onChange={v=>setTheme({...theme,speed:v})}/>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={theme.showLogos} onChange={(e)=>setTheme({...theme,showLogos:e.target.checked})}/>
            <span>Show team logos</span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={theme.showStatus} onChange={(e)=>setTheme({...theme,showStatus:e.target.checked})}/>
            <span>Show game status</span>
          </label>
          <button onClick={save} className="px-3 py-2 rounded bg-black text-white disabled:opacity-60" disabled={saving}>
            {saving? "Saving..." : "Save settings"}
          </button>
        </div>

        <div className="grid gap-3 p-3 rounded border">
          <h3 className="font-semibold">How to populate</h3>
          <ol className="list-decimal ml-5 space-y-1 text-sm">
            <li>Use the “Add Ticker Item” action in Scores to push marquee games.</li>
            <li>Or set <code>source.mode</code> to <code>external</code> with a JSON feed (admin API supports it).</li>
            <li>Ticker auto-refreshes every 20s on homepage.</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
