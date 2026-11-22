const url = process.env.SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
const webhook = process.env.DISCORD_WEBHOOK_URL;
if (!url || !key || !webhook) throw new Error('Missing SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or DISCORD_WEBHOOK_URL secret.');
const headers = { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' };
const get = async (path) => { const r=await fetch(`${url}/rest/v1/${path}`,{headers}); if(!r.ok) throw new Error(`Supabase GET failed (${r.status}): ${await r.text()}`); return r.json(); };
const post = async (path, body, prefer='return=representation') => { const r=await fetch(`${url}/rest/v1/${path}`,{method:'POST',headers:{...headers,Prefer:prefer},body:JSON.stringify(body)}); if(!r.ok) throw new Error(`Supabase POST failed (${r.status}): ${await r.text()}`); return r.json(); };
// WAT is UTC+1. GitHub cron is 19:00 UTC Sunday = 20:00 WAT Sunday.
const now = new Date();
const wat = new Date(now.getTime()+60*60*1000);
const day = (wat.getUTCDay()+6)%7; // Monday=0
const monday = new Date(Date.UTC(wat.getUTCFullYear(),wat.getUTCMonth(),wat.getUTCDate()-day));
const sunday = new Date(monday); sunday.setUTCDate(sunday.getUTCDate()+6);
const fmt = d => d.toISOString().slice(0,10);
const weekStart=fmt(monday), weekEnd=fmt(sunday);
const existing=await get(`payroll_runs?week_start=eq.${weekStart}&select=id`);
if(existing.length){console.log(`Payroll for ${weekStart} already exists; skipping duplicate.`);process.exit(0);}
const [agents,sales]=await Promise.all([
  get('agents?active=eq.true&select=id,name&order=name.asc'),
  get(`sales?status=eq.sold&sold_at=gte.${weekStart}&sold_at=lte.${weekEnd}&select=id,agent_id,property_ref,amount,sold_at`)
]);
const rows=agents.map(a=>{const own=sales.filter(s=>s.agent_id===a.id);const total=own.reduce((n,s)=>n+Number(s.amount),0);return {agent_id:a.id,agent:a.name,properties_sold:own.length,sales_total:total,commission_total:Number((total*0.15).toFixed(2))};}).filter(a=>a.properties_sold>0);
const totalSales=sales.reduce((n,s)=>n+Number(s.amount),0);const totalCommission=Number((totalSales*0.15).toFixed(2));
const fmtMoney=n=>new Intl.NumberFormat('en-NG',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(n);
const lines=rows.length?rows.map(a=>`**${a.agent}** — ${a.properties_sold} sold · Sales ${fmtMoney(a.sales_total)} · Commission **${fmtMoney(a.commission_total)}**`).join('\n'):'No confirmed property sales this week.';
const content=`👑 **PRIME CITY REAL ESTATE**\n📊 **WEEKLY AGENT PAYROLL**\nWeek: ${weekStart} to ${weekEnd} (WAT)\n\n${lines}\n\n**BUSINESS TOTALS**\nProperties sold: **${sales.length}**\nTotal sales: **${fmtMoney(totalSales)}**\nCommission rate: **15%**\n💰 **TOTAL AGENT PAYOUT: ${fmtMoney(totalCommission)}**`;
const discord=await fetch(webhook,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({content})});
if(!discord.ok)throw new Error(`Discord webhook failed (${discord.status}): ${await discord.text()}`);
await post('payroll_runs',{week_start:weekStart,week_end:weekEnd,properties_sold:sales.length,sales_total:totalSales,commission_rate:0.15,commission_total:totalCommission,breakdown:rows});
if(rows.length) await post('payroll_agent_rows', rows.map(a=>({week_start:weekStart,week_end:weekEnd,agent_id:a.agent_id,properties_sold:a.properties_sold,sales_total:a.sales_total,commission_rate:0.15,commission_total:a.commission_total}))); 
console.log(`Posted and archived payroll for ${weekStart}–${weekEnd}.`);
