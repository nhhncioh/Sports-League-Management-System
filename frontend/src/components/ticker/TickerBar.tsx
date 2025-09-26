/* src/components/ticker/TickerBar.tsx */
"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchTicker, TickerItem, TickerTheme } from "@/src/lib/tickerApi";

function useReducedMotion(){ 
  const [pref, setPref] = useState<boolean>(false);
  useEffect(()=>{ 
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setPref(mq.matches); 
    const fn = (e:MediaQueryListEvent)=>setPref(e.matches);
    mq.addEventListener?.("change", fn);
    return ()=>mq.removeEventListener?.("change", fn);
  },[]);
  return pref;
}

export default function TickerBar({ leagueId }:{ leagueId:string }) {
  const [enabled,setEnabled] = useState(false);
  const [theme,setTheme] = useState<TickerTheme>({bg:"#0b0d12",fg:"#fff",accent:"#ffc107",height:40,speed:55,showLogos:true,showStatus:true});
  const [items,setItems] = useState<TickerItem[]>([]);
  const [paused,setPaused] = useState(false);
  const reduced = useReducedMotion();
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(()=>{ 
    (async()=>{
      const data = await fetchTicker(leagueId);
      setEnabled(data.enabled);
      if (data.theme) setTheme({...theme, ...data.theme});
      setItems(data.items || []);
    })();
    const id = setInterval(async ()=>{
      const data = await fetchTicker(leagueId);
      if (data.enabled) setItems(data.items || []);
    }, 20_000);
    return ()=>clearInterval(id);
  }, [leagueId]);

  const row = useMemo(()=>items.length?items:[{
    id:0,status:"",home_name:"Ticker is empty",away_name:"Add items in Admin → Homepage → Score Ticker"
  } as TickerItem], [items]);

  if(!enabled) return null;

  const h = `${theme.height}px`;
  const animDur = `${Math.max(12, Math.round( (row.length*300)/Math.max(10, theme.speed) ))}s`;

  return (
    <div role="region" aria-label="Score ticker" style={{background:theme.bg,color:theme.fg,height:h}}
         className="w-full overflow-hidden border-b" >
      <div className="max-w-screen-2xl mx-auto flex items-center h-full gap-2 px-3">
        <strong style={{color:theme.accent}} className="shrink-0">SCORES</strong>
        <button aria-pressed={paused} onClick={()=>setPaused(p=>!p)} className="text-xs underline ml-1"> {paused? "Play" : "Pause"} </button>
        <div className="relative flex-1 h-full overflow-hidden">
          <div
            ref={trackRef}
            className="ticker-track"
            data-paused={(paused || reduced) ? "1" : "0"}
            style={{ 
              height:h,
              '--ticker-height': h,
              '--ticker-duration': animDur
            } as React.CSSProperties}
          >
            {[...row, ...row].map((g, i)=>(
              <a
                key={i+"-"+g.id}
                href={g.link_url || "#"}
                className="ticker-chip"
                style={{'--accent':theme.accent} as React.CSSProperties}
                aria-label={`${g.away_name ?? ''} ${g.away_score ?? ''} at ${g.home_name ?? ''} ${g.home_score ?? ''} ${g.status??''}`}
              >
                {theme.showLogos && g.away_logo ? <img src={g.away_logo} alt="" /> : null}
                <span className="team">{g.away_name}</span>
                {typeof g.away_score === "number" ? <span className="score">{g.away_score}</span> : null}
                <span className="at">@</span>
                {theme.showLogos && g.home_logo ? <img src={g.home_logo} alt="" /> : null}
                <span className="team">{g.home_name}</span>
                {typeof g.home_score === "number" ? <span className="score">{g.home_score}</span> : null}
                {theme.showStatus && g.status ? <span className="status">{g.status}</span> : null}
              </a>
            ))}
          </div>
        </div>
      </div>
      <style jsx>{`
        .ticker-track {
          display:flex;
          align-items:center;
          gap: 12px;
          height: var(--ticker-height);
          will-change: transform;
          animation: scroll var(--ticker-duration) linear infinite;
        }
        .ticker-track[data-paused="1"] { animation-play-state: paused; }
        @keyframes scroll {
          from { transform: translateX(0); }
          to   { transform: translateX(-50%); }
        }
        .ticker-chip{
          display:inline-flex; align-items:center; gap:8px;
          padding: 0 10px; height: calc(var(--ticker-height) - 8px);
          border-radius: 999px; border:1px solid #ffffff22;
          text-decoration:none; color:inherit; font-size:14px; white-space:nowrap;
          outline-offset: 2px;
        }
        .ticker-chip:hover{ background:#ffffff0f; }
        .ticker-chip img{ width:18px; height:18px; object-fit:contain }
        .ticker-chip .team{ font-weight:600 }
        .ticker-chip .score{ font-variant-numeric: tabular-nums; padding-left:2px }
        .ticker-chip .status{ margin-left:8px; font-size:12px; color: var(--accent) }
        @media (prefers-reduced-motion: reduce){ .ticker-track{ animation: none; } }
      `}</style>
    </div>
  );
}
