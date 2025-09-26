/* src/lib/tickerApi.ts */
export type TickerTheme = {
  bg:string; fg:string; accent:string; height:number; speed:number; showLogos:boolean; showStatus:boolean;
};
export type TickerItem = {
  id:number; status:"SCHEDULED"|"LIVE"|"FINAL"|string; start_time?:string;
  home_name:string; away_name:string; home_logo?:string; away_logo?:string;
  home_score?:number; away_score?:number; venue?:string; link_url?:string;
};
export async function fetchTicker(leagueId:string): Promise<{enabled:boolean; theme?:TickerTheme; items:TickerItem[]}> {
  const r = await fetch(`/api/ticker/${leagueId}`, { cache: "no-store" });
  if (!r.ok) return { enabled:false, items:[] };
  return r.json();
}
