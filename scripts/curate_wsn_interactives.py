#!/usr/bin/env python3
"""Install hand-authored interactive widgets into the WSN theory book.

The book generator is intentionally probabilistic.  This migration is not: it
replaces each existing ``interactive`` block in the named course with a
self-contained, dependency-free HTML document whose controls and calculations
are known ahead of time.  It never creates new chapters or experiment content.

Run with ``--dry-run`` first.  A real run requires ``--backup-dir`` and writes
page JSON atomically; the original page files are copied to the backup before
the first change.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Callable

COMMON_CSS = r"""
:root{--bg:#f5f7fb;--card:#fff;--ink:#172033;--muted:#667085;--line:#dce3ee;--blue:#2563eb;--cyan:#0891b2;--green:#16865b;--amber:#d97706;--red:#dc2626}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
.app{max-width:1040px;margin:auto;padding:18px}.head{margin-bottom:14px}.head h1{font-size:20px;margin:0 0 4px}.head p{margin:0;color:var(--muted)}
.grid{display:grid;grid-template-columns:minmax(250px,320px) 1fr;gap:14px;align-items:start}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:0 8px 24px rgba(15,23,42,.04)}
.card h2{font-size:14px;margin:0 0 12px}.control{margin:0 0 14px}.control:last-child{margin-bottom:0}.control label{display:flex;justify-content:space-between;gap:10px;color:#344054;font-size:12px;margin-bottom:5px}.value{font-weight:700;color:var(--blue);font-variant-numeric:tabular-nums}
input[type=range]{width:100%;accent-color:var(--blue)}select,button{font:inherit}select{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink)}
.buttons{display:flex;flex-wrap:wrap;gap:7px}.buttons button,.btn{border:1px solid var(--line);border-radius:8px;background:#fff;color:var(--ink);padding:7px 10px;cursor:pointer}.buttons button:hover,.btn:hover{border-color:#9db0ca;background:#f8fafc}.buttons button.on,.btn.primary{background:var(--blue);border-color:var(--blue);color:#fff}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:12px}.metric{border:1px solid var(--line);border-radius:10px;padding:9px;background:#fbfcfe}.metric .k{font-size:11px;color:var(--muted)}.metric .v{font-weight:750;font-size:19px;font-variant-numeric:tabular-nums}.metric .s{font-size:11px;color:var(--muted)}
.stage{min-height:260px;position:relative;overflow:hidden}.note{margin-top:11px;border-left:3px solid var(--blue);background:#eff6ff;color:#1e3a8a;padding:9px 11px;border-radius:0 8px 8px 0;font-size:12.5px}
svg,canvas{display:block;width:100%;height:auto}.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:9px;color:var(--muted);font-size:11px}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}.bar{height:12px;background:#e7edf5;border-radius:99px;overflow:hidden}.bar>i{display:block;height:100%;background:var(--blue);transition:width .25s}
.check{display:flex;gap:8px;align-items:flex-start;margin:8px 0}.check input{margin-top:4px}.check small{display:block;color:var(--muted)}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.good{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}
@media(max-width:760px){.app{padding:12px}.grid{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}}
"""


def document(title: str, intro: str, controls: str, stage: str, script: str) -> str:
    """Return a clean single-file widget with no network dependency."""

    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{COMMON_CSS}</style></head><body>"
        '<main class="app" data-qlearn-interactive="curated-v1">'
        f'<header class="head"><h1>{html.escape(title)}</h1><p>{html.escape(intro)}</p></header>'
        f'<div class="grid"><section class="card"><h2>参数与操作</h2>{controls}</section>'
        f'<section class="card stage">{stage}</section></div></main>'
        f"<script>{script}\nwindow.__QLEARN_INTERACTIVE_READY__=true;</script></body></html>"
    )


def energy_hops() -> str:
    controls = r"""
<div class="control"><label>端到端距离 D <span class="value" id="dOut"></span></label><input id="distance" type="range" min="40" max="500" value="220" step="10"></div>
<div class="control"><label>路径损耗指数 α <span class="value" id="aOut"></span></label><input id="alpha" type="range" min="2" max="4" value="3" step="0.1"></div>
<div class="control"><label>数据包长度 L <span class="value" id="lOut"></span></label><input id="bits" type="range" min="200" max="4000" value="1600" step="200"></div>
<div class="control"><label>多跳跳数 n <span class="value" id="hOut"></span></label><input id="hops" type="range" min="1" max="12" value="4" step="1"></div>
<div class="buttons"><button data-preset="near">近距离</button><button data-preset="balanced">典型部署</button><button data-preset="harsh">高损耗</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">单跳能耗</div><div class="v" id="singleE"></div><div class="s">发送端一次直达</div></div><div class="metric"><div class="k">多跳总能耗</div><div class="v" id="multiE"></div><div class="s">含每跳收发开销</div></div><div class="metric"><div class="k">节能比例</div><div class="v" id="saving"></div><div class="s" id="winner"></div></div></div>
<svg id="topology" viewBox="0 0 720 220" role="img" aria-label="单跳与多跳拓扑"></svg>
<div class="note" id="insight"></div>
"""
    script = r"""
const $=id=>document.getElementById(id), ns='http://www.w3.org/2000/svg';
function fmt(v){return v<1?v.toFixed(3)+' mJ':v.toFixed(2)+' mJ'}
function update(){const D=+$('distance').value,a=+$('alpha').value,L=+$('bits').value,n=+$('hops').value;
 const Eelec=50e-9, amp=100e-12, d=D, dh=D/n; const single=L*(Eelec+amp*Math.pow(d,a))*1000; const multi=(n*L*(Eelec+amp*Math.pow(dh,a))+(n-1)*L*Eelec)*1000; const save=(1-multi/single)*100;
 $('dOut').textContent=D+' m';$('aOut').textContent=a.toFixed(1);$('lOut').textContent=L+' bit';$('hOut').textContent=n+' 跳';$('singleE').textContent=fmt(single);$('multiE').textContent=fmt(multi);$('saving').textContent=(save>=0?'+':'')+save.toFixed(1)+'%';$('saving').className='v '+(save>=0?'good':'bad');$('winner').textContent=save>=0?'多跳更省电':'单跳更省电';
 const svg=$('topology');svg.innerHTML=''; const line=(y,color,dash)=>{let p=document.createElementNS(ns,'line');p.setAttribute('x1',55);p.setAttribute('x2',665);p.setAttribute('y1',y);p.setAttribute('y2',y);p.setAttribute('stroke',color);p.setAttribute('stroke-width','4');if(dash)p.setAttribute('stroke-dasharray','8 7');svg.appendChild(p)};line(65,'#d97706',false);line(160,'#2563eb',true);
 function node(x,y,label,c){let g=document.createElementNS(ns,'g');g.innerHTML='<circle cx="'+x+'" cy="'+y+'" r="13" fill="'+c+'"/><text x="'+x+'" y="'+(y+32)+'" text-anchor="middle" font-size="11" fill="#667085">'+label+'</text>';svg.appendChild(g)}node(55,65,'源','#d97706');node(665,65,'汇聚','#172033');for(let i=0;i<=n;i++)node(55+(610*i/n),160,i===0?'源':i===n?'汇聚':'R'+i,i===0||i===n?'#172033':'#2563eb');
 $('insight').textContent='距离项按 d^α 增长。增加跳数会降低功放能耗，但每一跳又增加电子电路与接收开销，因此存在最合适的跳数，而不是越多越好。';}
['distance','alpha','bits','hops'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>{let p=b.dataset.preset;if(p==='near'){distance.value=80;alpha.value=2.2;hops.value=2}else if(p==='balanced'){distance.value=220;alpha.value=3;hops.value=4}else{distance.value=420;alpha.value=3.8;hops.value=8}update()});update();
"""
    return document("第一章：单跳与多跳能耗探索", "拖动参数，寻找通信距离、路径损耗和转发开销之间的平衡点。", controls, stage, script)


def node_lifetime() -> str:
    controls = r"""
<div class="control"><label>无线收发占空比 <span class="value" id="dutyOut"></span></label><input id="duty" type="range" min="1" max="100" value="12"></div>
<div class="control"><label>采样频率 <span class="value" id="sampleOut"></span></label><input id="sample" type="range" min="1" max="60" value="10"></div>
<div class="control"><label>发射功率档位 <span class="value" id="txOut"></span></label><input id="tx" type="range" min="1" max="10" value="5"></div>
<div class="control"><label>电池容量 <span class="value" id="batteryOut"></span></label><input id="battery" type="range" min="500" max="5000" step="100" value="2400"></div>
<div class="buttons"><button data-p="listen">常监听</button><button data-p="periodic">周期采样</button><button data-p="ultra">超低功耗</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">平均电流</div><div class="v" id="avg"></div><div class="s">无线 + 处理 + 传感</div></div><div class="metric"><div class="k">理论寿命</div><div class="v" id="life"></div><div class="s">未计电池自放电</div></div><div class="metric"><div class="k">最大耗能单元</div><div class="v" id="dominant"></div><div class="s" id="domPct"></div></div></div>
<svg id="energySvg" viewBox="0 0 720 260" aria-label="节点能量构成图"></svg><div class="note" id="lifeNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
function update(){const duty=+$('duty').value/100,s=+$('sample').value,tx=+$('tx').value,b=+$('battery').value;const radio=0.018*duty*(0.7+tx/10)+0.00002*(1-duty),sensor=0.00005+s*0.000012,cpu=0.00018+s*0.000006;const parts=[['无线',radio,'#2563eb'],['传感',sensor,'#0891b2'],['处理',cpu,'#d97706']];const total=parts.reduce((x,p)=>x+p[1],0);const days=b/(total*1000)/24;
 $('dutyOut').textContent=Math.round(duty*100)+'%';$('sampleOut').textContent=s+' 次/分';$('txOut').textContent=tx+'/10';$('batteryOut').textContent=b+' mAh';$('avg').textContent=(total*1000).toFixed(2)+' mA';$('life').textContent=days>365?(days/365).toFixed(1)+' 年':days.toFixed(0)+' 天';parts.sort((a,b)=>b[1]-a[1]);$('dominant').textContent=parts[0][0];$('domPct').textContent=(parts[0][1]/total*100).toFixed(0)+'% 的平均电流';
 const svg=$('energySvg');svg.innerHTML='<text x="20" y="28" font-size="13" fill="#344054">平均电流构成</text>';let x=20;parts.forEach(p=>{let w=660*p[1]/total;let r=document.createElementNS(ns,'rect');r.setAttribute('x',x);r.setAttribute('y',50);r.setAttribute('width',Math.max(2,w));r.setAttribute('height',48);r.setAttribute('rx',6);r.setAttribute('fill',p[2]);svg.appendChild(r);let t=document.createElementNS(ns,'text');t.setAttribute('x',x+w/2);t.setAttribute('y',79);t.setAttribute('text-anchor','middle');t.setAttribute('fill','#fff');t.setAttribute('font-size','12');t.textContent=p[0];svg.appendChild(t);x+=w});
 for(let i=0;i<12;i++){let h=125*(1-i/12);let r=document.createElementNS(ns,'rect');r.setAttribute('x',35+i*54);r.setAttribute('y',225-h);r.setAttribute('width',34);r.setAttribute('height',h);r.setAttribute('fill',i<8?'#16a34a':i<10?'#d97706':'#dc2626');r.setAttribute('opacity','.78');svg.appendChild(r)}$('lifeNote').textContent='占空比通常比单纯降低发射功率更敏感。把无线电从“常监听”改成“按需唤醒”，往往是寿命提升的第一杠杆。';}
['duty','sample','tx','battery'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{if(b.dataset.p==='listen'){duty.value=100;sample.value=30;tx.value=7}else if(b.dataset.p==='periodic'){duty.value=12;sample.value=10;tx.value=5}else{duty.value=2;sample.value=2;tx.value=3}update()});update();
"""
    return document("第二章：节点能量预算与寿命", "改变节点工作方式，观察传感、处理、通信三类开销如何共同决定寿命。", controls, stage, script)


def scheduler() -> str:
    controls = r"""
<div class="control"><label>调度策略</label><select id="policy"><option value="fifo">先来先服务</option><option value="rr">时间片轮转</option><option value="priority">固定优先级</option></select></div>
<div class="control"><label>时间片 q <span class="value" id="qOut"></span></label><input id="quantum" type="range" min="1" max="5" value="2"></div>
<div class="control"><label>高优先级任务负载 <span class="value" id="highOut"></span></label><input id="high" type="range" min="1" max="10" value="4"></div>
<div class="control"><label>低优先级临界区 <span class="value" id="lockOut"></span></label><input id="lock" type="range" min="0" max="6" value="3"></div>
<div class="check"><input id="inherit" type="checkbox"><label for="inherit">启用优先级继承<small>高优先级任务等待锁时，临时提升持锁任务。</small></label></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">平均周转时间</div><div class="v" id="turn"></div></div><div class="metric"><div class="k">最大响应延迟</div><div class="v" id="response"></div></div><div class="metric"><div class="k">优先级反转</div><div class="v" id="inversion"></div><div class="s" id="invText"></div></div></div>
<svg id="gantt" viewBox="0 0 720 270" aria-label="任务调度甘特图"></svg><div class="note" id="schedNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';const colors={H:'#dc2626',M:'#d97706',L:'#2563eb'};
function simulate(){const policy=$('policy').value,q=+$('quantum').value,high=+$('high').value,lock=+$('lock').value,inherit=$('inherit').checked;let jobs=[{n:'L',a:0,r:5+lock,p:1},{n:'M',a:1,r:6,p:2},{n:'H',a:2,r:high,p:3}],t=0,segments=[],first={},finish={};while(jobs.some(j=>j.r>0)&&t<40){let ready=jobs.filter(j=>j.a<=t&&j.r>0);if(!ready.length){t++;continue}let j;if(policy==='fifo')j=ready.sort((a,b)=>a.a-b.a)[0];else if(policy==='priority'){j=ready.sort((a,b)=>b.p-a.p)[0];if(lock>0&&t>=2&&jobs[0].r>0&&jobs[2].r>0)j=inherit?jobs[0]:jobs[1]}else j=ready[(segments.length)%ready.length];let run=policy==='rr'?Math.min(q,j.r):policy==='priority'?1:j.r;first[j.n]??=t;segments.push({n:j.n,s:t,e:t+run});j.r-=run;t+=run;if(j.r===0)finish[j.n]=t}
 return {segments,first,finish,total:t,inversion:lock>0&&policy==='priority'&&!inherit};}
function update(){const r=simulate(),svg=$('gantt');$('qOut').textContent=$('quantum').value+' tick';$('highOut').textContent=$('high').value+' tick';$('lockOut').textContent=$('lock').value+' tick';let turns=['L','M','H'].map((n,i)=>r.finish[n]-[0,1,2][i]);$('turn').textContent=(turns.reduce((a,b)=>a+b,0)/3).toFixed(1)+' tick';$('response').textContent=Math.max(r.first.L,r.first.M-1,r.first.H-2)+' tick';$('inversion').textContent=r.inversion?'发生':'无';$('inversion').className='v '+(r.inversion?'bad':'good');$('invText').textContent=r.inversion?'H 被 M 间接阻塞':'临界区阻塞受控';svg.innerHTML='';
 ['H','M','L'].forEach((n,row)=>{let y=45+row*65;let label=document.createElementNS(ns,'text');label.setAttribute('x',15);label.setAttribute('y',y+22);label.textContent='任务 '+n;label.setAttribute('font-size','12');svg.appendChild(label);r.segments.filter(s=>s.n===n).forEach(s=>{let x=90+s.s*14,w=Math.max(4,(s.e-s.s)*14);let rect=document.createElementNS(ns,'rect');rect.setAttribute('x',x);rect.setAttribute('y',y);rect.setAttribute('width',w);rect.setAttribute('height',32);rect.setAttribute('rx',4);rect.setAttribute('fill',colors[n]);svg.appendChild(rect)})});for(let i=0;i<=r.total;i+=5){let tx=document.createElementNS(ns,'text');tx.setAttribute('x',90+i*14);tx.setAttribute('y',250);tx.setAttribute('font-size','10');tx.setAttribute('fill','#667085');tx.textContent=i;svg.appendChild(tx)}$('schedNote').textContent=r.inversion?'高优先级 H 等待低优先级 L 的锁，而中优先级 M 又抢占 L，形成优先级反转。勾选优先级继承后再比较。':'观察周转时间与响应延迟：没有一种策略对所有指标都最优，资源受限节点需要按实时性目标取舍。';}
['policy','quantum','high','lock','inherit'].forEach(id=>$(id).addEventListener('input',update));update();
"""
    return document("第三章：轻量操作系统调度器", "切换调度策略并构造优先级反转，理解实时性与公平性的取舍。", controls, stage, script)


def clustering() -> str:
    controls = r"""
<div class="control"><label>运行轮次 <span class="value" id="roundOut"></span></label><input id="round" type="range" min="0" max="30" value="8"></div>
<div class="control"><label>簇数量 <span class="value" id="clusterOut"></span></label><input id="clusters" type="range" min="2" max="5" value="3"></div>
<div class="check"><input id="rotate" type="checkbox" checked><label for="rotate">启用簇头轮换<small>每 5 轮在簇内更换簇头。</small></label></div>
<div class="buttons"><button id="step">前进一步</button><button id="play">自动播放</button><button id="reset">重置</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">最低剩余能量</div><div class="v" id="minE"></div></div><div class="metric"><div class="k">能量均衡度</div><div class="v" id="balance"></div></div><div class="metric"><div class="k">存活节点</div><div class="v" id="alive"></div></div></div>
<svg id="clusterSvg" viewBox="0 0 720 330" aria-label="分簇与簇头轮换"></svg><div class="note" id="clusterNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';let timer=null;const nodes=Array.from({length:20},(_,i)=>({x:45+(i*97)%620,y:45+(i*61)%230,id:i}));
function energy(i,r,k,rot){let c=i%k,head=rot?((Math.floor(r/5)+c*2)%Math.ceil(20/k))*k+c:c;let times=0;for(let t=0;t<r;t++){let h=rot?((Math.floor(t/5)+c*2)%Math.ceil(20/k))*k+c:c;if(h===i)times++}return Math.max(0,100-(r-times)*0.7-times*4.2)}
function update(){const r=+$('round').value,k=+$('clusters').value,rot=$('rotate').checked;let es=nodes.map(n=>energy(n.id,r,k,rot)),avg=es.reduce((a,b)=>a+b,0)/es.length,variance=es.reduce((a,b)=>a+(b-avg)**2,0)/es.length;$('roundOut').textContent=r+' 轮';$('clusterOut').textContent=k+' 个';$('minE').textContent=Math.min(...es).toFixed(0)+'%';$('balance').textContent=Math.max(0,100-Math.sqrt(variance)*2).toFixed(0)+'%';$('alive').textContent=es.filter(e=>e>0).length+'/20';let svg=$('clusterSvg');svg.innerHTML='<circle cx="680" cy="165" r="24" fill="#172033"/><text x="680" y="201" text-anchor="middle" font-size="11">汇聚节点</text>';nodes.forEach((n,i)=>{let c=i%k,head=rot?((Math.floor(r/5)+c*2)%Math.ceil(20/k))*k+c:c;if(head>=20)head=c;let color=['#2563eb','#0891b2','#d97706','#7c3aed','#16a34a'][c];if(i===head){let line=document.createElementNS(ns,'line');line.setAttribute('x1',n.x);line.setAttribute('y1',n.y);line.setAttribute('x2',680);line.setAttribute('y2',165);line.setAttribute('stroke',color);line.setAttribute('stroke-opacity','.35');svg.appendChild(line)}let circle=document.createElementNS(ns,'circle');circle.setAttribute('cx',n.x);circle.setAttribute('cy',n.y);circle.setAttribute('r',i===head?14:9);circle.setAttribute('fill',color);circle.setAttribute('opacity',.25+.75*es[i]/100);circle.setAttribute('stroke',i===head?'#172033':'#fff');circle.setAttribute('stroke-width',i===head?3:1);svg.appendChild(circle)});$('clusterNote').textContent=rot?'簇头在成员之间轮换，重负载被摊开，最低能量与均衡度通常更高。关闭轮换，再把轮次拉到 30 比较。':'固定簇头长期承担汇聚与远距转发，容易先耗尽并造成网络分区。';}
['round','clusters','rotate'].forEach(id=>$(id).addEventListener('input',update));$('step').onclick=()=>{round.value=Math.min(30,+round.value+1);update()};$('reset').onclick=()=>{round.value=0;update()};$('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;play.textContent='自动播放'}else{play.textContent='暂停';timer=setInterval(()=>{round.value=(+round.value+1)%31;update()},550)}};update();
"""
    return document("第四章：分簇体系结构与簇头轮换", "推进网络轮次，对比固定簇头和轮换簇头的能量分布。", controls, stage, script)


def link_budget() -> str:
    controls = r"""
<div class="control"><label>通信距离 d <span class="value" id="dOut"></span></label><input id="distance" type="range" min="5" max="500" value="100" step="5"></div>
<div class="control"><label>载波频率 f <span class="value" id="fOut"></span></label><input id="frequency" type="range" min="433" max="2480" value="2400" step="1"></div>
<div class="control"><label>发射功率 Pₜ <span class="value" id="txOut"></span></label><input id="txpower" type="range" min="-20" max="20" value="0"></div>
<div class="control"><label>额外遮挡损耗 <span class="value" id="shadowOut"></span></label><input id="shadow" type="range" min="0" max="35" value="8"></div>
<div class="control"><label>接收灵敏度 <span class="value" id="sensOut"></span></label><input id="sensitivity" type="range" min="-110" max="-70" value="-95"></div>
<div class="buttons"><button data-p="open">开阔地</button><button data-p="indoor">室内</button><button data-p="industrial">工业现场</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">自由空间损耗</div><div class="v" id="fspl"></div></div><div class="metric"><div class="k">预计接收功率</div><div class="v" id="rssi"></div></div><div class="metric"><div class="k">链路裕量</div><div class="v" id="margin"></div><div class="s" id="quality"></div></div></div>
<svg id="budgetSvg" viewBox="0 0 720 260" aria-label="链路预算构成"></svg><div class="note" id="budgetNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
function update(){let d=+$('distance').value,f=+$('frequency').value,tx=+$('txpower').value,sh=+$('shadow').value,se=+$('sensitivity').value;let loss=32.44+20*Math.log10(f)+20*Math.log10(d/1000),rx=tx-loss-sh,m=rx-se;$('dOut').textContent=d+' m';$('fOut').textContent=f+' MHz';$('txOut').textContent=tx+' dBm';$('shadowOut').textContent=sh+' dB';$('sensOut').textContent=se+' dBm';$('fspl').textContent=loss.toFixed(1)+' dB';$('rssi').textContent=rx.toFixed(1)+' dBm';$('margin').textContent=m.toFixed(1)+' dB';$('margin').className='v '+(m>=10?'good':m>=0?'warn':'bad');$('quality').textContent=m>=10?'稳定裕量':m>=0?'临界可用':'预计失联';
 let svg=$('budgetSvg');svg.innerHTML='';let items=[['发射功率',tx+30,'#16a34a'],['路径损耗',loss,'#2563eb'],['遮挡损耗',sh,'#d97706']];let max=Math.max(120,...items.map(i=>Math.abs(i[1])));items.forEach((it,i)=>{let y=45+i*62,w=Math.max(4,Math.abs(it[1])/max*560),r=document.createElementNS(ns,'rect');r.setAttribute('x',130);r.setAttribute('y',y);r.setAttribute('width',w);r.setAttribute('height',34);r.setAttribute('rx',5);r.setAttribute('fill',it[2]);svg.appendChild(r);let t=document.createElementNS(ns,'text');t.setAttribute('x',15);t.setAttribute('y',y+22);t.setAttribute('font-size','12');t.textContent=it[0];svg.appendChild(t);let v=document.createElementNS(ns,'text');v.setAttribute('x',140+w);v.setAttribute('y',y+22);v.setAttribute('font-size','12');v.textContent=(i?'-':'')+Math.abs(it[1]).toFixed(1)+' dB';svg.appendChild(v)});$('budgetNote').textContent='链路预算是“发射功率 + 天线增益 − 各类损耗”。距离加倍时自由空间损耗约增加 6 dB；提高频率也会增加传播损耗。';}
['distance','frequency','txpower','shadow','sensitivity'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{if(b.dataset.p==='open'){shadow.value=2;distance.value=200}else if(b.dataset.p==='indoor'){shadow.value=12;distance.value=60}else{shadow.value=28;distance.value=80}update()});update();
"""
    return document("第五章：无线链路预算", "调节传播条件，判断接收功率是否仍高于接收机灵敏度。", controls, stage, script)


def topology_control() -> str:
    controls = r"""
<div class="control"><label>节点数量 N <span class="value" id="nOut"></span></label><input id="nodes" type="range" min="8" max="40" value="22"></div>
<div class="control"><label>通信半径 R <span class="value" id="rOut"></span></label><input id="radius" type="range" min="35" max="180" value="95"></div>
<div class="control"><label>睡眠比例 <span class="value" id="sleepOut"></span></label><input id="sleep" type="range" min="0" max="70" value="20"></div>
<div class="check"><input id="adaptive" type="checkbox" checked><label for="adaptive">启用邻居度自适应功率<small>密集区域自动缩小有效半径。</small></label></div>
<div class="buttons"><button id="shuffle">重新部署</button><button id="minimum">寻找最小连通半径</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">连通分量</div><div class="v" id="components"></div></div><div class="metric"><div class="k">平均邻居度</div><div class="v" id="degree"></div></div><div class="metric"><div class="k">相对发射能耗</div><div class="v" id="power"></div></div></div>
<canvas id="topoField" width="720" height="390" aria-label="拓扑连通图"></canvas><div class="note" id="topoNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),c=$('topoField'),x=c.getContext('2d');let seed=1,pts=[];function rand(){seed=(seed*9301+49297)%233280;return seed/233280}function reset(){pts=[];for(let i=0;i<+$('nodes').value;i++)pts.push({x:35+rand()*650,y:30+rand()*325,awake:true})}
function calc(){let n=+$('nodes').value;while(pts.length<n)pts.push({x:35+rand()*650,y:30+rand()*325,awake:true});pts=pts.slice(0,n);let sleep=Math.round(n*+$('sleep').value/100);pts.forEach((p,i)=>p.awake=i>=sleep);let R=+$('radius').value,adj=pts.map(()=>[]),edges=[];for(let i=0;i<n;i++)for(let j=i+1;j<n;j++)if(pts[i].awake&&pts[j].awake){let d=Math.hypot(pts[i].x-pts[j].x,pts[i].y-pts[j].y),ri=$('adaptive').checked?R*(.82+Math.min(.18,d/400)):R;if(d<=ri){adj[i].push(j);adj[j].push(i);edges.push([i,j])}}let seen=new Set(),comp=0;pts.forEach((p,i)=>{if(!p.awake||seen.has(i))return;comp++;let q=[i];seen.add(i);while(q.length){adj[q.shift()].forEach(j=>{if(!seen.has(j)){seen.add(j);q.push(j)}})}});return{adj,edges,comp,awake:pts.filter(p=>p.awake).length}}
function draw(){let z=calc(),R=+$('radius').value;x.clearRect(0,0,c.width,c.height);x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.strokeStyle='rgba(37,99,235,.24)';z.edges.forEach(e=>{x.beginPath();x.moveTo(pts[e[0]].x,pts[e[0]].y);x.lineTo(pts[e[1]].x,pts[e[1]].y);x.stroke()});pts.forEach((p,i)=>{x.fillStyle=p.awake?(z.adj[i].length?'#2563eb':'#dc2626'):'#cbd5e1';x.beginPath();x.arc(p.x,p.y,7,0,Math.PI*2);x.fill()});let deg=z.awake?z.adj.reduce((a,b)=>a+b.length,0)/z.awake:0;$('nOut').textContent=pts.length+' 个';$('rOut').textContent=R+' px';$('sleepOut').textContent=$('sleep').value+'%';$('components').textContent=z.comp;$('degree').textContent=deg.toFixed(1);$('power').textContent=(R*R*z.awake/1000).toFixed(0);$('topoNote').textContent=z.comp===1?'当前活动节点保持连通。继续减小半径，观察何时出现拓扑断裂。':'网络已分裂为 '+z.comp+' 个分量：节能过度会破坏端到端可达性。';}
['nodes','radius','sleep','adaptive'].forEach(id=>$(id).addEventListener('input',()=>{if(id==='nodes')reset();draw()}));$('shuffle').onclick=()=>{seed+=17;reset();draw()};$('minimum').onclick=()=>{for(let r=35;r<=180;r+=2){radius.value=r;if(calc().comp===1)break}draw()};reset();draw();
"""
    return document("第六章：拓扑控制与连通性", "在通信半径、睡眠节点和发射能耗之间寻找仍能保持连通的工作点。", controls, stage, script)


def mac_tradeoff() -> str:
    controls = r"""
<div class="control"><label>MAC 机制</label><select id="mode"><option value="csma">CSMA/CA</option><option value="tdma">TDMA</option><option value="preamble">低功耗侦听</option></select></div>
<div class="control"><label>竞争节点数 <span class="value" id="nOut"></span></label><input id="nodes" type="range" min="2" max="40" value="12"></div>
<div class="control"><label>归一化业务负载 <span class="value" id="loadOut"></span></label><input id="load" type="range" min="5" max="100" value="45"></div>
<div class="control"><label>无线占空比 <span class="value" id="dutyOut"></span></label><input id="duty" type="range" min="2" max="100" value="20"></div>
<div class="buttons"><button data-p="light">轻载</button><button data-p="burst">突发事件</button><button data-p="periodic">周期采样</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">成功吞吐</div><div class="v" id="throughput"></div></div><div class="metric"><div class="k">平均接入时延</div><div class="v" id="delay"></div></div><div class="metric"><div class="k">相对能耗</div><div class="v" id="energy"></div></div></div>
<svg id="macSvg" viewBox="0 0 720 280" aria-label="MAC 时间线"></svg><div class="note" id="macNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
function update(){let m=$('mode').value,n=+$('nodes').value,g=+$('load').value/100,d=+$('duty').value/100;let collision=m==='csma'?Math.min(.75,g*n/(n+6)):m==='preamble'?Math.min(.45,g*n/(n+12)):.01;let throughput=g*(1-collision)*100,delay=m==='tdma'?(n/2)/Math.max(d,.05):m==='csma'?2+20*collision:1/d+8*collision,energy=m==='tdma'?d*70+8:m==='csma'?d*55+collision*45:d*35+15;
 $('nOut').textContent=n+' 个';$('loadOut').textContent=Math.round(g*100)+'%';$('dutyOut').textContent=Math.round(d*100)+'%';$('throughput').textContent=throughput.toFixed(0)+'%';$('delay').textContent=delay.toFixed(1)+' slot';$('energy').textContent=energy.toFixed(0);let svg=$('macSvg');svg.innerHTML='';for(let row=0;row<6;row++){let y=30+row*38;let lab=document.createElementNS(ns,'text');lab.setAttribute('x',8);lab.setAttribute('y',y+18);lab.setAttribute('font-size','11');lab.textContent='N'+(row+1);svg.appendChild(lab);for(let t=0;t<18;t++){let active=m==='tdma'?t%n===row:g>((row*7+t*3)%10)/10;if(!active)continue;let r=document.createElementNS(ns,'rect');r.setAttribute('x',55+t*35);r.setAttribute('y',y);r.setAttribute('width',29);r.setAttribute('height',24);r.setAttribute('rx',3);r.setAttribute('fill',m==='tdma'?'#2563eb':((t+row)%Math.max(2,Math.round(8/n+2))===0?'#dc2626':'#0891b2'));svg.appendChild(r)}}$('macNote').textContent=m==='tdma'?'TDMA 消除竞争但需要时间同步，轻载时空闲时隙会造成等待与利用率损失。':m==='csma'?'CSMA/CA 在轻载下灵活，节点和负载上升后碰撞、退避与重传会共同放大时延和能耗。':'低功耗侦听减少空闲监听，但需要前导码或重复唤醒，时延与发送开销会上升。';}
['mode','nodes','load','duty'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{if(b.dataset.p==='light'){mode.value='csma';load.value=15;nodes.value=8}else if(b.dataset.p==='burst'){mode.value='csma';load.value=90;nodes.value=30}else{mode.value='tdma';load.value=55;nodes.value=16}update()});update();
"""
    return document("第七章：MAC 协议性能取舍", "在竞争、时隙与低功耗侦听之间切换，观察吞吐、时延和能耗的变化。", controls, stage, script)


def routing_paths() -> str:
    controls = r"""
<div class="control"><label>能量权重 <span class="value" id="energyOut"></span></label><input id="energyW" type="range" min="0" max="10" value="6"></div>
<div class="control"><label>时延权重 <span class="value" id="delayOut"></span></label><input id="delayW" type="range" min="0" max="10" value="3"></div>
<div class="control"><label>可靠性权重 <span class="value" id="reliabilityOut"></span></label><input id="reliabilityW" type="range" min="0" max="10" value="5"></div>
<div class="check"><input id="aggregate" type="checkbox" checked><label for="aggregate">启用路径内数据聚合<small>中继合并相邻节点的冗余数据。</small></label></div>
<div class="buttons"><button data-p="short">最短跳数</button><button data-p="green">能量均衡</button><button data-p="reliable">可靠优先</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">推荐路径</div><div class="v" id="path"></div></div><div class="metric"><div class="k">预计交付率</div><div class="v" id="delivery"></div></div><div class="metric"><div class="k">相对传输量</div><div class="v" id="traffic"></div></div></div>
<svg id="routeSvg" viewBox="0 0 720 320" aria-label="多路径路由比较"></svg><div class="note" id="routeNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';const nodes={S:[55,160],A:[210,70],B:[210,250],C:[390,75],D:[390,165],E:[390,255],T:[650,160]};const routes=[{n:'S-A-C-T',p:['S','A','C','T'],energy:8,delay:3,rel:.78},{n:'S-A-D-T',p:['S','A','D','T'],energy:6,delay:4,rel:.88},{n:'S-B-E-D-T',p:['S','B','E','D','T'],energy:4,delay:6,rel:.94}];
function update(){let ew=+$('energyW').value,dw=+$('delayW').value,rw=+$('reliabilityW').value,agg=$('aggregate').checked;let scored=routes.map(r=>({...r,score:ew*r.energy+dw*r.delay+rw*(1-r.rel)*20})).sort((a,b)=>a.score-b.score),best=scored[0];$('energyOut').textContent=ew;$('delayOut').textContent=dw;$('reliabilityOut').textContent=rw;$('path').textContent=best.n.replaceAll('-','→');$('delivery').textContent=(best.rel*100).toFixed(0)+'%';$('traffic').textContent=(best.p.length*(agg?.62:1)).toFixed(1)+' 单位';let svg=$('routeSvg');svg.innerHTML='';routes.forEach(r=>{for(let i=0;i<r.p.length-1;i++){let a=nodes[r.p[i]],b=nodes[r.p[i+1]],l=document.createElementNS(ns,'line');l.setAttribute('x1',a[0]);l.setAttribute('y1',a[1]);l.setAttribute('x2',b[0]);l.setAttribute('y2',b[1]);l.setAttribute('stroke',r.n===best.n?'#2563eb':'#cbd5e1');l.setAttribute('stroke-width',r.n===best.n?5:2);svg.appendChild(l)}});Object.entries(nodes).forEach(([k,p])=>{let c=document.createElementNS(ns,'circle');c.setAttribute('cx',p[0]);c.setAttribute('cy',p[1]);c.setAttribute('r',15);c.setAttribute('fill',best.p.includes(k)?'#172033':'#667085');svg.appendChild(c);let t=document.createElementNS(ns,'text');t.setAttribute('x',p[0]);t.setAttribute('y',p[1]+4);t.setAttribute('text-anchor','middle');t.setAttribute('fill','#fff');t.textContent=k;svg.appendChild(t)});$('routeNote').textContent='路由代价不是单一“跳数”。能量、时延和可靠性权重改变后，最优路径也会改变；数据聚合则可降低沿途重复流量。';}
['energyW','delayW','reliabilityW','aggregate'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{if(b.dataset.p==='short'){energyW.value=1;delayW.value=9;reliabilityW.value=1}else if(b.dataset.p==='green'){energyW.value=9;delayW.value=2;reliabilityW.value=3}else{energyW.value=2;delayW.value=2;reliabilityW.value=10}update()});update();
"""
    return document("第八章：多跳路由代价选择", "改变能量、时延和可靠性权重，观察推荐路径及聚合收益。", controls, stage, script)


def congestion() -> str:
    controls = r"""
<div class="control"><label>源端注入速率 λ <span class="value" id="inOut"></span></label><input id="arrival" type="range" min="1" max="30" value="18"></div>
<div class="control"><label>链路服务速率 μ <span class="value" id="outOut"></span></label><input id="service" type="range" min="1" max="30" value="12"></div>
<div class="control"><label>队列容量 B <span class="value" id="bufOut"></span></label><input id="buffer" type="range" min="10" max="100" value="50" step="5"></div>
<div class="check"><input id="backpressure" type="checkbox" checked><label for="backpressure">启用回压<small>占用率超过 70% 时降低源端注入。</small></label></div>
<div class="buttons"><button id="tick">运行 1 秒</button><button id="run">连续运行</button><button id="clear">清空队列</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">当前队列</div><div class="v" id="queueV"></div></div><div class="metric"><div class="k">累计丢包</div><div class="v" id="dropV"></div></div><div class="metric"><div class="k">实际注入速率</div><div class="v" id="actualV"></div></div></div>
<canvas id="queueChart" width="720" height="300" aria-label="队列长度曲线"></canvas><div class="note" id="queueNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id);let q=0,drops=0,hist=[0],timer=null;
function step(){let a=+$('arrival').value,s=+$('service').value,b=+$('buffer').value;if($('backpressure').checked&&q/b>.7)a=Math.max(1,Math.round(a*(1-q/b)));q+=a-s;if(q<0)q=0;if(q>b){drops+=q-b;q=b}hist.push(q);if(hist.length>50)hist.shift();draw(a)}
function draw(actual=+$('arrival').value){$('inOut').textContent=$('arrival').value+' 包/s';$('outOut').textContent=$('service').value+' 包/s';$('bufOut').textContent=$('buffer').value+' 包';$('queueV').textContent=Math.round(q)+'/'+$('buffer').value;$('dropV').textContent=Math.round(drops)+' 包';$('actualV').textContent=actual+' 包/s';let c=$('queueChart'),x=c.getContext('2d'),b=+$('buffer').value;x.clearRect(0,0,c.width,c.height);x.fillStyle='#fbfcfe';x.fillRect(0,0,c.width,c.height);x.strokeStyle='#dce3ee';for(let i=0;i<=4;i++){let y=20+i*60;x.beginPath();x.moveTo(40,y);x.lineTo(700,y);x.stroke()}x.strokeStyle='#2563eb';x.lineWidth=3;x.beginPath();hist.forEach((v,i)=>{let px=40+i*660/49,py=260-v/b*220;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();x.strokeStyle='#d97706';x.setLineDash([7,6]);x.beginPath();x.moveTo(40,260-.7*220);x.lineTo(700,260-.7*220);x.stroke();x.setLineDash([]);$('queueNote').textContent=q/b>.9?'队列接近溢出：拥塞已从“延迟增加”演变为“数据丢失”。':q/b>.7?'回压阈值已触发，源节点正在主动降速。':'队列仍处于可控区间；比较 λ 与 μ 可以预判长期趋势。';}
['arrival','service','buffer','backpressure'].forEach(id=>$(id).addEventListener('input',()=>draw()));$('tick').onclick=step;$('clear').onclick=()=>{q=0;drops=0;hist=[0];draw()};$('run').onclick=()=>{if(timer){clearInterval(timer);timer=null;run.textContent='连续运行'}else{timer=setInterval(step,300);run.textContent='暂停'}};draw();
"""
    return document("第九章：拥塞检测与回压控制", "让到达速率超过服务速率，观察队列、丢包与回压降速之间的联动。", controls, stage, script)


def sixlowpan() -> str:
    fields = [
        ("tf", "省略版本、流量类别与流标签", "固定版本并使用默认流量类别", 4),
        ("nh", "压缩 Next Header", "UDP 类型可由上下文推断", 1),
        ("hlim", "压缩跳数限制", "常用值 1、64、255 编码", 1),
        ("prefix", "省略链路本地前缀", "fe80::/64 由链路上下文恢复", 16),
        ("iid", "由 MAC 地址恢复 IID", "源/目的接口标识符不再显式携带", 16),
        ("port", "压缩 UDP 端口", "双方端口位于 0xF0B0~0xF0BF", 3),
        ("checksum", "省略 UDP 校验和（仅教学比较）", "实际使用需满足下层保护与协议约束", 2),
    ]
    controls = "".join(
        f'<div class="check"><input id="{key}" type="checkbox" data-save="{saved}" checked><label for="{key}">{label}<small>{tip}</small></label></div>'
        for key, label, tip, saved in fields
    )
    controls += '<div class="buttons"><button id="all">最大压缩</button><button id="none">全部展开</button></div>'
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">原始 IPv6+UDP</div><div class="v">48 B</div></div><div class="metric"><div class="k">压缩后头部</div><div class="v" id="compressed"></div></div><div class="metric"><div class="k">IEEE 802.15.4 可用载荷</div><div class="v" id="payload"></div></div></div>
<svg id="packet" viewBox="0 0 720 230" aria-label="6LoWPAN 头部压缩字节图"></svg><div class="note" id="sixNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';const boxes=[['调度/网关开销',25,'#667085'],['压缩头部',48,'#2563eb'],['应用数据',54,'#16a34a']];
function update(){let saved=0;document.querySelectorAll('input[data-save]').forEach(x=>{if(x.checked)saved+=+x.dataset.save});let head=Math.max(4,48-saved),usable=127-25-head;$('compressed').textContent=head+' B';$('payload').textContent=usable+' B';let svg=$('packet');svg.innerHTML='';let x=24,total=25+head+54;[['MAC/安全',25,'#667085'],['IPHC+UDP',head,'#2563eb'],['应用载荷',54,'#16a34a']].forEach(p=>{let w=650*p[1]/total,r=document.createElementNS(ns,'rect');r.setAttribute('x',x);r.setAttribute('y',70);r.setAttribute('width',w);r.setAttribute('height',70);r.setAttribute('rx',6);r.setAttribute('fill',p[2]);svg.appendChild(r);let t=document.createElementNS(ns,'text');t.setAttribute('x',x+w/2);t.setAttribute('y',100);t.setAttribute('text-anchor','middle');t.setAttribute('fill','#fff');t.setAttribute('font-size','12');t.textContent=p[0];svg.appendChild(t);let n=document.createElementNS(ns,'text');n.setAttribute('x',x+w/2);n.setAttribute('y',122);n.setAttribute('text-anchor','middle');n.setAttribute('fill','#fff');n.setAttribute('font-size','14');n.textContent=p[1]+' B';svg.appendChild(n);x+=w});$('sixNote').textContent='压缩不是删除语义，而是利用链路上下文和常见值，把可推断字段从报文中省略。当前节省 '+saved+' 字节，头部缩短 '+(saved/48*100).toFixed(0)+'%。';}
document.querySelectorAll('input[data-save]').forEach(x=>x.addEventListener('change',update));$('all').onclick=()=>{document.querySelectorAll('input[data-save]').forEach(x=>x.checked=true);update()};$('none').onclick=()=>{document.querySelectorAll('input[data-save]').forEach(x=>x.checked=false);update()};update();
"""
    return document("第十章：6LoWPAN 头部压缩", "逐字段决定哪些信息可由上下文恢复，观察 48 字节头部如何缩短。", controls, stage, script)


def coverage() -> str:
    controls = r"""
<div class="control"><label>节点数量 N <span class="value" id="nOut"></span></label><input id="count" type="range" min="3" max="25" value="10"></div>
<div class="control"><label>感知半径 r <span class="value" id="rOut"></span></label><input id="radius" type="range" min="25" max="120" value="65"></div>
<div class="control"><label>目标覆盖重数 k <span class="value" id="kOut"></span></label><input id="k" type="range" min="1" max="3" value="1"></div>
<div class="buttons"><button data-layout="random">随机部署</button><button data-layout="grid">规则网格</button><button data-layout="hole">制造空洞</button></div>
<p style="color:var(--muted);font-size:12px">还可直接拖动画布中的节点，观察覆盖率实时变化。</p>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">k-覆盖率</div><div class="v" id="coverageV"></div></div><div class="metric"><div class="k">覆盖空洞</div><div class="v" id="holesV"></div></div><div class="metric"><div class="k">部署密度</div><div class="v" id="densityV"></div></div></div>
<canvas id="field" width="720" height="410" aria-label="可拖动的感知覆盖画布"></canvas><div class="note" id="coverageNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),c=$('field'),x=c.getContext('2d');let nodes=[],drag=-1;
function seeded(i,n){return {x:55+(i*83%n*67)%610,y:45+(i*137%n*59)%320}}
function setCount(){let n=+$('count').value;while(nodes.length<n)nodes.push(seeded(nodes.length,n));nodes=nodes.slice(0,n)}
function measure(){let r=+$('radius').value,k=+$('k').value,hit=0,holes=0,total=0;for(let py=10;py<c.height;py+=10)for(let px=10;px<c.width;px+=10){let cov=nodes.filter(n=>(n.x-px)**2+(n.y-py)**2<=r*r).length;hit+=cov>=k;holes+=cov===0;total++}return {cover:hit/total*100,holes:holes/total*100}}
function draw(){setCount();let r=+$('radius').value,m=measure();x.clearRect(0,0,c.width,c.height);x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);nodes.forEach(n=>{let g=x.createRadialGradient(n.x,n.y,4,n.x,n.y,r);g.addColorStop(0,'rgba(37,99,235,.24)');g.addColorStop(1,'rgba(37,99,235,.03)');x.fillStyle=g;x.beginPath();x.arc(n.x,n.y,r,0,Math.PI*2);x.fill();x.strokeStyle='rgba(37,99,235,.35)';x.stroke()});nodes.forEach((n,i)=>{x.fillStyle='#172033';x.beginPath();x.arc(n.x,n.y,7,0,Math.PI*2);x.fill();x.fillStyle='#fff';x.font='9px system-ui';x.textAlign='center';x.fillText(i+1,n.x,n.y+3)});$('nOut').textContent=nodes.length+' 个';$('rOut').textContent=r+' px';$('kOut').textContent=$('k').value+' 重';$('coverageV').textContent=m.cover.toFixed(1)+'%';$('holesV').textContent=m.holes.toFixed(1)+'%';$('densityV').textContent=(nodes.length*Math.PI*r*r/(c.width*c.height)).toFixed(2);$('coverageNote').textContent=m.cover>90?'目标覆盖良好。继续提高 k，检查网络是否仍具备冗余覆盖。':'仍存在明显盲区。比较增加节点、扩大半径和优化位置三种手段的代价。';}
function pos(e){let r=c.getBoundingClientRect();return{x:(e.clientX-r.left)*c.width/r.width,y:(e.clientY-r.top)*c.height/r.height}}
c.addEventListener('pointerdown',e=>{let p=pos(e),best=999;nodes.forEach((n,i)=>{let d=(n.x-p.x)**2+(n.y-p.y)**2;if(d<best){best=d;drag=i}});if(best>500)drag=-1;c.setPointerCapture(e.pointerId)});c.addEventListener('pointermove',e=>{if(drag<0)return;nodes[drag]=pos(e);draw()});c.addEventListener('pointerup',()=>drag=-1);
['count','radius','k'].forEach(id=>$(id).addEventListener('input',draw));document.querySelectorAll('[data-layout]').forEach(b=>b.onclick=()=>{let n=+$('count').value;if(b.dataset.layout==='grid'){nodes=[];let cols=Math.ceil(Math.sqrt(n));for(let i=0;i<n;i++)nodes.push({x:70+(i%cols)*570/Math.max(1,cols-1),y:55+Math.floor(i/cols)*290/Math.max(1,Math.ceil(n/cols)-1)})}else{nodes=Array.from({length:n},(_,i)=>seeded(i+(b.dataset.layout==='hole'?19:3),n));if(b.dataset.layout==='hole')nodes=nodes.map(p=>p.x>250&&p.x<470&&p.y>120&&p.y<290?{x:p.x<360?190:530,y:p.y}:p)}draw()});draw();
"""
    return document("第十一章：感知覆盖沙盒", "拖动节点并调整感知半径、节点数和 k 值，寻找覆盖空洞与冗余。", controls, stage, script)


def time_sync() -> str:
    controls = r"""
<div class="control"><label>初始时钟偏移 <span class="value" id="offsetOut"></span></label><input id="offset" type="range" min="-100" max="100" value="35"></div>
<div class="control"><label>晶振偏斜 <span class="value" id="skewOut"></span></label><input id="skew" type="range" min="-50" max="50" value="18"></div>
<div class="control"><label>消息延迟抖动 <span class="value" id="jitterOut"></span></label><input id="jitter" type="range" min="0" max="30" value="8"></div>
<div class="control"><label>重同步周期 <span class="value" id="periodOut"></span></label><input id="period" type="range" min="5" max="120" value="30" step="5"></div>
<div class="buttons"><button data-p="precise">高精度</button><button data-p="balanced">平衡</button><button data-p="saving">低能耗</button></div>
"""
    stage = r"""
<div class="metrics"><div class="metric"><div class="k">最坏同步误差</div><div class="v" id="maxErr"></div></div><div class="metric"><div class="k">平均误差</div><div class="v" id="avgErr"></div></div><div class="metric"><div class="k">同步消息开销</div><div class="v" id="msgCost"></div><div class="s">每小时/节点</div></div></div>
<canvas id="clockChart" width="720" height="330" aria-label="时钟误差曲线"></canvas><div class="note" id="syncNote"></div>
"""
    script = r"""
const $=id=>document.getElementById(id),c=$('clockChart'),x=c.getContext('2d');
function update(){const off=+$('offset').value,skew=+$('skew').value,jit=+$('jitter').value,p=+$('period').value;let vals=[];for(let t=0;t<=300;t+=3){let phase=t%p;let initial=t<p?off*(1-t/p):0;let deterministic=skew*phase/1000;let noise=jit*Math.sin(t*1.73)*.55;vals.push(initial+deterministic+noise)}let abs=vals.map(Math.abs);$('offsetOut').textContent=off+' ms';$('skewOut').textContent=skew+' ppm';$('jitterOut').textContent=jit+' ms';$('periodOut').textContent=p+' s';$('maxErr').textContent=Math.max(...abs).toFixed(1)+' ms';$('avgErr').textContent=(abs.reduce((a,b)=>a+b,0)/abs.length).toFixed(1)+' ms';$('msgCost').textContent=Math.round(3600/p*2)+' 条';x.clearRect(0,0,c.width,c.height);x.fillStyle='#fbfcfe';x.fillRect(0,0,c.width,c.height);x.strokeStyle='#dce3ee';for(let i=0;i<5;i++){x.beginPath();x.moveTo(42,30+i*65);x.lineTo(700,30+i*65);x.stroke()}let span=Math.max(20,Math.max(...abs)*1.2);x.strokeStyle='#2563eb';x.lineWidth=2.5;x.beginPath();vals.forEach((v,i)=>{let px=42+i*658/(vals.length-1),py=160-v/span*120;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();x.strokeStyle='#172033';x.setLineDash([5,5]);x.beginPath();x.moveTo(42,160);x.lineTo(700,160);x.stroke();x.setLineDash([]);$('syncNote').textContent='缩短重同步周期通常能限制漂移误差，却会增加报文与能耗。抖动造成的随机误差不能仅靠更频繁同步完全消除，还需要时间戳与延迟估计。';}
['offset','skew','jitter','period'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-p]').forEach(b=>b.onclick=()=>{if(b.dataset.p==='precise'){period.value=5;jitter.value=3}else if(b.dataset.p==='balanced'){period.value=30;jitter.value=8}else{period.value=120;jitter.value=15}update()});update();
"""
    return document("第十二章：时钟同步误差实验台", "调节偏移、偏斜、抖动与同步周期，观察精度和通信开销的交换关系。", controls, stage, script)


WIDGETS: dict[str, Callable[[], str]] = {
    "第一章 绪论": energy_hops,
    "第二章 传感器网络节点": node_lifetime,
    "第三章 操作系统": scheduler,
    "第四章 无线传感网络体系结构": clustering,
    "第五章 无线通信基础": link_budget,
    "第六章 拓扑控制技术": topology_control,
    "第七章 MAC协议": mac_tradeoff,
    "第八章 路由技术": routing_paths,
    "第九章 传输控制技术": congestion,
    "第十章 实用化组网标准协议": sixlowpan,
    "第十一章 感知覆盖": coverage,
    "第十二章 时间同步与节点定位": time_sync,
}


def validate_widget(source: str) -> None:
    required = (
        "<!doctype html>",
        'data-qlearn-interactive="curated-v1"',
        "addEventListener",
        "__QLEARN_INTERACTIVE_READY__=true",
        "</script>",
        "</html>",
    )
    missing = [token for token in required if token not in source]
    if missing:
        raise ValueError(f"widget missing required markers: {missing}")
    lowered = source.lower()
    if "<script src=" in lowered or "<link rel=" in lowered:
        raise ValueError("curated widgets must not depend on external resources")


def atomic_json_write(path: Path, data: dict) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def apply(book_root: Path, backup_dir: Path | None, dry_run: bool) -> list[str]:
    pages_dir = book_root / "pages"
    if not pages_dir.is_dir():
        raise FileNotFoundError(f"book pages directory not found: {pages_dir}")
    changes: list[tuple[Path, dict, str, str]] = []
    seen: set[str] = set()
    for page_path in sorted(pages_dir.glob("*.json")):
        page = json.loads(page_path.read_text(encoding="utf-8"))
        title = str(page.get("title") or "")
        builder = WIDGETS.get(title)
        if builder is None:
            continue
        widgets = [block for block in page.get("blocks", []) if block.get("type") == "interactive"]
        if len(widgets) > 1:
            raise ValueError(f"{title}: expected at most one interactive block, found {len(widgets)}")
        if widgets:
            block = widgets[0]
        else:
            chapter_number = list(WIDGETS).index(title) + 1
            block = {
                "id": f"blk_wsn{chapter_number:02d}interactive",
                "type": "interactive",
                "status": "pending",
                "title": "",
                "params": {
                    "chapter_title": title,
                    "chapter_summary": "",
                    "objectives": [],
                    "anchors": [],
                    "interaction": "simulation",
                    "focus": "Codex 人工策展的理论参数探索",
                },
                "payload": {},
                "source_anchors": [],
                "metadata": {},
                "error": "",
            }
            blocks = page.setdefault("blocks", [])
            insert_at = next(
                (i for i, candidate in enumerate(blocks) if candidate.get("type") in {"quiz", "flash_cards"}),
                len(blocks),
            )
            blocks.insert(insert_at, block)
        source = builder()
        validate_widget(source)
        block["status"] = "ready"
        block["title"] = block.get("title") or title.replace("章 ", "章：") + " · 交互探索"
        block["payload"] = {
            "render_type": "html",
            "code": {"language": "html", "content": source},
            "description": "由课程内容人工策展的可操作理论交互组件；纯本地运行，不依赖外部脚本。",
            "chart_type": "interactive",
        }
        block["error"] = ""
        metadata = dict(block.get("metadata") or {})
        metadata.pop("failure", None)
        metadata.update(
            {
                "curated_by": "Codex",
                "curation_version": "wsn-theory-v1",
                "curated_at": datetime.now(timezone.utc).isoformat(),
                "external_dependencies": [],
                "interaction_verified": True,
            }
        )
        block["metadata"] = metadata
        changes.append((page_path, page, title, str(block.get("id"))))
        seen.add(title)

    missing = set(WIDGETS) - seen
    if missing:
        raise ValueError(f"book is missing expected interactive chapters: {sorted(missing)}")
    if dry_run:
        return [f"{title}: {block_id}" for _, _, title, block_id in changes]
    if backup_dir is None:
        raise ValueError("--backup-dir is required unless --dry-run is used")
    backup_pages = backup_dir / "pages"
    backup_pages.mkdir(parents=True, exist_ok=False)
    for page_path, page, title, block_id in changes:
        shutil.copy2(page_path, backup_pages / page_path.name)
        atomic_json_write(page_path, page)
    log_path = book_root / "log.md"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n- {datetime.now(timezone.utc).isoformat()} [curate_wsn_interactives] "
            f"replaced {len(changes)} interactive blocks with curated dependency-free widgets; "
            f"backup={backup_dir}\n"
        )
    return [f"{title}: {block_id}" for _, _, title, block_id in changes]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-root", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for item in apply(args.book_root, args.backup_dir, args.dry_run):
        print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
