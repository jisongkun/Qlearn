#!/usr/bin/env python3
"""Repair and complete the hand-authored WSN theory book.

This companion migration installs the twelve curated interactive widgets,
replaces known failed figures and quiz placeholders, and fills the structurally
short chapters (5–8) with a theory self-check and review cards.  The migration
is intentionally scoped by exact book/page titles and is idempotent.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

try:
    from curate_wsn_interactives import apply as apply_interactives
    from curate_wsn_interactives import atomic_json_write
except ModuleNotFoundError:  # imported as ``scripts.curate_wsn_book`` in tests
    from scripts.curate_wsn_interactives import apply as apply_interactives
    from scripts.curate_wsn_interactives import atomic_json_write


def q(
    qid: str,
    kind: str,
    prompt: str,
    answer: str,
    explanation: str,
    *,
    options: dict[str, str] | None = None,
    concentration: str = "",
) -> dict[str, Any]:
    return {
        "question_id": qid,
        "question": prompt,
        "question_type": kind,
        "options": options or {},
        "correct_answer": answer,
        "explanation": explanation,
        "difficulty": "medium",
        "concentration": concentration or prompt[:80],
    }


FAILED_QUESTION_REPLACEMENTS: dict[str, dict[str, Any]] = {
    "第一章 绪论": q(
        "q_4",
        "written",
        "设相邻节点间距相等、总距离为 D，发射放大器能耗与距离的 α 次方成正比。说明为什么把一次长距离发送拆成 n 次短距离发送，通常能降低功放能耗；同时解释 n 不能无限增大的原因。",
        "若忽略常数，每跳距离为 D/n，n 跳功放能耗约为 n·(D/n)^α=D^α/n^(α-1)。当 α>1 时，它随 n 增大而下降；但每一跳都要重复支付发送/接收电子电路、侦听、确认与排队开销，所以总能耗存在折中点。",
        "关键是同时保留两部分：距离相关的功放项因分段而下降，逐跳固定开销却随跳数增加。多跳短距通常更省电，但不是跳数越多越好。",
        concentration="多跳短距的能耗量级与最优跳数",
    ),
    "第二章 传感器网络节点": q(
        "q_3",
        "written",
        "某节点使用 2400 mAh 电池：活动状态电流 18 mA、持续 20 ms；其余时间休眠电流 0.02 mA，周期为 1 s。计算平均电流和理想寿命，并说明若工作电压由 3.3 V 降至 2.7 V，动态功耗近似 P∝CV²f 时为什么还能进一步节能。",
        "占空比为 0.02。平均电流 Ī=18×0.02+0.02×0.98≈0.3796 mA；理想寿命约 2400/0.3796≈6322 h≈263 天。若电容负载与频率近似不变，动态功耗比约为 (2.7/3.3)²≈0.67，即理论上下降约 33%。",
        "寿命估算先按一个周期做加权平均，再用容量除以平均电流。实际寿命还受电池自放电、稳压损耗、温度、脉冲放电与电压下限影响。",
        concentration="占空比、平均电流、寿命与动态电压调节",
    ),
    "第三章 操作系统": q(
        "q_5",
        "written",
        "低优先级任务 L 持有互斥锁时被中优先级任务 M 抢占；随后高优先级任务 H 请求同一把锁。说明优先级反转链路，并比较优先级继承与优先级天花板如何限制 H 的阻塞时间。",
        "H 因锁被 L 阻塞，但 L 又被与锁无关的 M 抢占，导致 H 间接等待 M，形成优先级反转。优先级继承在 H 阻塞时临时把 L 提升到 H 的优先级，使 L 尽快退出临界区；优先级天花板在 L 获得该资源时就把它提升到所有可能访问者中的最高优先级，从源头避免 M 抢占。响应时间分析把最长一次低优先级临界区阻塞写入 B_i，再与自身执行和高优先级干扰共同计算。",
        "两种协议都给反转建立上界；继承是冲突发生后的动态提升，天花板是获得资源时的预防性提升，代价是需要预先配置资源天花板。",
        concentration="优先级反转、继承、天花板与阻塞界",
    ),
    "第十章 实用化组网标准协议": q(
        "q_6",
        "short_answer",
        "ZigBee 树路由为什么能够仅凭目的短地址和 Cskip 地址块大小决定下一跳，而不必在每个节点保存完整路由表？说明其适用条件与局限。",
        "分布式地址分配为每个路由器及其后代预留连续地址区间。节点先判断目的地址是否落在自己的后代区间；若落入，就用 Cskip 计算它属于哪个子路由器的地址块并向该子节点转发，否则向父节点转发。它适合拓扑稳定、层次明确且内存受限的树网络；但路径受树结构约束，可能绕路，链路或父节点失效时鲁棒性不如维护邻居/路由信息的网状路由。",
        "Cskip 的本质是把路由状态编码进地址区间，用计算换路由表空间；这种简洁性以路径灵活性与故障绕行为代价。",
        concentration="ZigBee Cskip 地址区间与树路由权衡",
    ),
    "第十二章 时间同步与节点定位": q(
        "q_5",
        "written",
        "两节点最大相对频率偏斜为 40 ppm。若同步后希望相位误差不超过 2 ms，忽略消息抖动时最大重同步间隔是多少？再说明时间误差如何影响 TDMA 时隙和基于飞行时间的测距。",
        "40 ppm=40×10⁻⁶。误差近似为 Δt=ρT，因此 T≤2×10⁻³/(40×10⁻⁶)=50 s。实际应给消息延迟抖动和估计误差留裕量，周期需短于 50 s。TDMA 中误差可能把发送边界推入相邻时隙，引起碰撞；飞行时间测距中距离误差为 c·Δt，1 ns 就约对应 0.3 m，因此毫秒级误差完全不可接受，必须使用硬件时间戳、双向测量或差分方法消除公共偏差。",
        "本题把 ppm 转成无量纲频差后，用误差上限除以频差得到周期；不同应用对时间误差的放大方式不同，定位的时间精度要求远高于一般采样同步。",
        concentration="频率偏斜、重同步周期、TDMA 与飞行时间测距",
    ),
}


NEW_QUIZZES: dict[str, list[dict[str, Any]]] = {
    "第五章 无线通信基础": [
        q("q_1", "choice", "在自由空间近似下，距离加倍而频率、天线和发射功率不变，路径损耗约增加多少？", "B", "自由空间路径损耗含 20log10(d)，距离加倍增加 20log10(2)≈6.02 dB。", options={"A": "3 dB", "B": "6 dB", "C": "10 dB", "D": "12 dB"}),
        q("q_2", "concept", "大尺度路径损耗给出接收功率的长期平均趋势，小尺度衰落描述多径相量叠加造成的快速起伏。", "true", "两者作用尺度不同：前者随距离和遮挡缓慢变化，后者可在波长量级位移内剧烈波动。"),
        q("q_3", "short_answer", "链路预算中“裕量”如何计算？为什么设计值通常不能只做到 0 dB？", "链路裕量=预计接收功率−接收机灵敏度。0 dB 只代表名义条件下刚好可解调；实际还存在阴影、天线偏差、温湿度、干扰与器件离散性，因此需要保留若干 dB 的工程余量。", "裕量用于吸收模型没有精确描述的随机和系统误差。"),
        q("q_4", "written", "比较提高发射功率、降低数据率和增加中继三种改善弱链路的方法，并说明各自代价。", "提高发射功率直接增加接收功率，但耗能和干扰上升；降低数据率或采用更强编码可提高每比特能量与处理增益，但吞吐下降、占空时间增加；增加中继缩短单跳距离，可能显著降低功放开销，但增加收发固定开销、排队时延和协议复杂度。", "无线链路优化是能耗、吞吐、时延和网络复杂度的联合权衡。"),
    ],
    "第六章 拓扑控制技术": [
        q("q_1", "choice", "拓扑控制把所有节点发射功率统一调到最大，最可能造成什么结果？", "C", "最大功率通常提高邻居度，却增加干扰、空闲侦听和能耗，并不等于网络整体最优。", options={"A": "必然延长网络寿命", "B": "必然消除隐藏终端", "C": "连通性提高但干扰与能耗上升", "D": "覆盖率必然下降"}),
        q("q_2", "concept", "通信图保持连通，并不能单独证明监测区域没有感知空洞。", "true", "连通性约束节点之间能否传递数据，覆盖约束空间中的目标点能否被感知，二者由不同半径和几何条件决定。"),
        q("q_3", "short_answer", "睡眠调度为什么需要保留冗余邻居？", "若只按当前最短路径保留节点，单节点失效或链路波动就可能分割网络。保留适量冗余邻居可提供替代路径、故障恢复和负载轮换，但会增加待机与侦听能耗。", "冗余是可靠性与能耗之间的保险。"),
        q("q_4", "written", "说明“最小连通发射功率”为什么是有用基线，但不一定是长期最优工作点。", "它给出维持当前拓扑连通所需的最低功率，可减少不必要的能耗和干扰；但节点移动、衰落、能量消耗与故障会改变图结构，恰好临界的链路缺乏裕量。长期运行通常需要滞回、冗余边或按链路质量自适应，而不是固定在一次测得的绝对最小值。", "理论最小值与工程鲁棒工作点并不相同。"),
    ],
    "第七章 MAC协议": [
        q("q_1", "choice", "CSMA/CA 中两个彼此听不到、却同时向同一接收节点发送的节点构成什么问题？", "A", "发送端互相侦听不到对方，均判断信道空闲，最终在共同接收端发生碰撞。", options={"A": "隐藏终端", "B": "暴露终端", "C": "时钟漂移", "D": "路由环路"}),
        q("q_2", "concept", "TDMA 可以消除同一调度域内的竞争碰撞，但需要时间同步，且轻载时可能浪费预留时隙。", "true", "TDMA 用调度换确定性；同步开销和低负载利用率是其主要代价。"),
        q("q_3", "short_answer", "空闲侦听为什么是低负载传感网络的重要能耗来源？低功耗侦听如何缓解？", "无线接收机即使没有有效帧也会消耗接近接收状态的电流。低功耗侦听让节点周期性短暂采样信道，其余时间休眠；代价是发送端需要更长前导码或重复唤醒序列，增加发送开销和接入时延。", "占空调度把接收端空闲成本转化为发送端唤醒成本。"),
        q("q_4", "written", "事件突发型监测与严格周期采样分别更适合怎样的 MAC 机制？", "事件突发且平时轻载时，CSMA/CA 或自适应低功耗侦听能避免长期预留空闲时隙，但突发时要处理碰撞与退避；周期稳定且有确定时延要求时，TDMA 或预约式机制更容易保证时限和无碰撞访问，但需要同步与调度维护。混合协议可在平时竞争、负载升高后切换预约。", "协议选择取决于业务负载的时间结构，而非只看峰值吞吐。"),
    ],
    "第八章 路由技术": [
        q("q_1", "choice", "以数据为中心的路由与传统地址路由相比，最突出的特点是什么？", "D", "它围绕数据属性、兴趣和聚合组织传输，关注“需要什么数据”，而非只按主机地址建立端到端会话。", options={"A": "必须使用 GPS", "B": "只允许单跳", "C": "不需要任何路由状态", "D": "按数据属性命名、匹配与聚合"}),
        q("q_2", "concept", "跳数最少的路径不一定最节能，因为长距离弱链路可能需要更高发射功率和更多重传。", "true", "能量代价还取决于距离、链路质量、接收开销、剩余能量和重传概率。"),
        q("q_3", "short_answer", "地理位置路由为什么容易出现局部最小点？常见恢复思路是什么？", "贪心转发要求下一跳比当前节点更接近目的地；在空洞或边界处可能不存在这样的邻居，即使全局仍有绕行路径。常见做法是切换到面路由/周界转发，沿空洞边界绕行，恢复到可继续贪心的位置后再切回。", "局部几何最优不保证全局可达。"),
        q("q_4", "written", "说明数据聚合为什么通常能节能，以及它可能损害哪些信息属性。", "相邻节点观测往往相关，中继可去重、求均值或提取事件后再发送，减少后续跳上的字节数和报文数，因通信通常比计算耗能而节能。但聚合会引入等待时延，可能丢失单节点细节，且聚合节点成为故障与篡改集中点。需按应用对实时性、可追溯性与容错的要求选择聚合粒度。", "聚合以本地计算和信息压缩换通信能耗。"),
    ],
}


REVIEW_CARDS: dict[str, list[tuple[str, str]]] = {
    "第五章 无线通信基础": [("链路预算", "发射功率与增益减去路径、遮挡和实现损耗"), ("自由空间路径损耗", "随距离和频率的平方增长；对数域中各为 20log 项"), ("小尺度衰落", "多径信号相量叠加导致的快速包络起伏"), ("接收灵敏度", "接收机在目标误码率下可正确解调的最低输入功率"), ("链路裕量", "预计接收功率高于灵敏度的余量")],
    "第六章 拓扑控制技术": [("通信图", "节点为顶点、可通信链路为边的图模型"), ("邻居度", "节点直接可达邻居的数量"), ("连通分量", "内部互相可达、与外部不可达的最大节点集合"), ("功率控制", "调节发射功率以改变通信半径和拓扑"), ("睡眠调度", "在维持覆盖和连通前提下关闭冗余节点")],
    "第七章 MAC协议": [("空闲侦听", "接收机等待可能到来的帧而消耗能量"), ("隐藏终端", "发送端互相听不到但在共同接收端碰撞"), ("CSMA/CA", "发送前侦听并随机退避的竞争接入"), ("TDMA", "按时间片预约发送的无竞争接入"), ("占空比", "无线电处于活动状态的时间比例")],
    "第八章 路由技术": [("数据中心路由", "按兴趣和数据属性组织查询、匹配与传输"), ("地理路由", "根据节点与目的位置选择下一跳"), ("局部最小", "当前节点没有更靠近目的地的邻居"), ("能量感知路由", "把剩余能量或预计耗能纳入路径代价"), ("数据聚合", "在中继处合并冗余数据以减少传输")],
}


FIGURES: dict[tuple[str, str], tuple[str, str]] = {
    ("第五章 无线通信基础", "blk_870bf6b5e5"): (
        "多径叠加与小尺度衰落",
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 420" role="img" aria-label="多径传播导致小尺度衰落"><rect width="900" height="420" fill="#f8fafc"/><text x="30" y="40" font-size="24" font-family="sans-serif" fill="#172033">多径相量叠加：同相增强，反相衰落</text><circle cx="90" cy="200" r="28" fill="#2563eb"/><text x="90" y="205" text-anchor="middle" fill="white" font-family="sans-serif">Tx</text><circle cx="810" cy="200" r="28" fill="#172033"/><text x="810" y="205" text-anchor="middle" fill="white" font-family="sans-serif">Rx</text><path d="M118 190 Q450 40 782 190" fill="none" stroke="#0891b2" stroke-width="5"/><path d="M118 205 Q430 360 782 205" fill="none" stroke="#d97706" stroke-width="5"/><path d="M118 200 L360 200 L500 105 L782 200" fill="none" stroke="#7c3aed" stroke-width="4" stroke-dasharray="10 7"/><rect x="345" y="185" width="40" height="50" fill="#94a3b8"/><text x="450" y="390" text-anchor="middle" font-size="18" font-family="sans-serif" fill="#475467">不同路径具有不同幅度与相位；接收点轻微移动也会改变合成结果</text><g transform="translate(610 65)"><line x1="0" y1="70" x2="210" y2="70" stroke="#cbd5e1"/><path d="M0 70 C30 20 55 120 90 70 S150 20 210 70" fill="none" stroke="#dc2626" stroke-width="4"/><text x="105" y="0" text-anchor="middle" font-size="16" font-family="sans-serif">接收包络快速起伏</text></g></svg>""",
    ),
    ("第十章 实用化组网标准协议", "blk_b54022d031"): (
        "IEEE 802.15.4 超帧与设备角色",
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 430" role="img" aria-label="802.15.4超帧时序"><rect width="980" height="430" fill="#f8fafc"/><text x="30" y="42" font-size="24" font-family="sans-serif" fill="#172033">IEEE 802.15.4 信标使能超帧</text><g transform="translate(35 85)" font-family="sans-serif"><rect x="0" y="0" width="90" height="90" fill="#172033"/><text x="45" y="52" text-anchor="middle" fill="white">Beacon</text><rect x="90" y="0" width="390" height="90" fill="#2563eb"/><text x="285" y="42" text-anchor="middle" fill="white" font-size="20">CAP</text><text x="285" y="67" text-anchor="middle" fill="white">时隙 CSMA/CA</text><rect x="480" y="0" width="245" height="90" fill="#0891b2"/><text x="602" y="42" text-anchor="middle" fill="white" font-size="20">CFP</text><text x="602" y="67" text-anchor="middle" fill="white">最多 7 个 GTS</text><rect x="725" y="0" width="185" height="90" fill="#cbd5e1"/><text x="817" y="52" text-anchor="middle" fill="#344054">非活跃期 / 休眠</text><line x1="0" y1="115" x2="910" y2="115" stroke="#475467" stroke-width="2"/><text x="455" y="145" text-anchor="middle" fill="#475467">Beacon Interval</text></g><g transform="translate(90 300)" font-family="sans-serif"><circle cx="120" cy="45" r="32" fill="#172033"/><text x="120" y="50" text-anchor="middle" fill="white">协调器</text><circle cx="40" cy="120" r="25" fill="#2563eb"/><text x="40" y="125" text-anchor="middle" fill="white">RFD</text><circle cx="200" cy="120" r="25" fill="#0891b2"/><text x="200" y="125" text-anchor="middle" fill="white">FFD</text><line x1="100" y1="68" x2="55" y2="100" stroke="#64748b"/><line x1="140" y1="68" x2="185" y2="100" stroke="#64748b"/><text x="120" y="170" text-anchor="middle">星型：协调器居中</text><circle cx="550" cy="45" r="26" fill="#2563eb"/><circle cx="670" cy="45" r="26" fill="#0891b2"/><circle cx="610" cy="130" r="26" fill="#7c3aed"/><path d="M575 45H645 M563 66L597 110 M657 66L623 110" stroke="#64748b" stroke-width="3"/><text x="610" y="170" text-anchor="middle">对等网状：FFD 可互联与转发</text></g></svg>""",
    ),
    ("第十二章 时间同步与节点定位", "blk_486fffacba"): (
        "时钟偏移、频率偏斜与再次发散",
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 430" role="img" aria-label="时钟误差随时间发散"><rect width="900" height="430" fill="#f8fafc"/><text x="30" y="40" font-size="24" font-family="sans-serif" fill="#172033">同步校正只能消除当下偏移，频率偏斜会让误差再次累积</text><g transform="translate(85 70)"><line x1="0" y1="300" x2="750" y2="300" stroke="#64748b" stroke-width="2"/><line x1="0" y1="300" x2="0" y2="10" stroke="#64748b" stroke-width="2"/><text x="760" y="305" font-family="sans-serif">真实时间</text><text x="-55" y="20" font-family="sans-serif">时钟读数</text><path d="M0 270 L750 20" stroke="#172033" stroke-width="4"/><path d="M0 230 L300 95 L300 190 L750 45" fill="none" stroke="#2563eb" stroke-width="5"/><path d="M0 290 Q180 185 300 145 L300 190 Q560 95 750 70" fill="none" stroke="#d97706" stroke-width="4" stroke-dasharray="10 7"/><line x1="300" y1="20" x2="300" y2="300" stroke="#dc2626" stroke-width="2" stroke-dasharray="6 6"/><text x="300" y="330" text-anchor="middle" font-family="sans-serif" fill="#dc2626">同步校正点</text><text x="590" y="145" font-family="sans-serif" fill="#2563eb">恒定偏斜：线性发散</text><text x="500" y="235" font-family="sans-serif" fill="#d97706">漂移率变化：曲线发散</text></g></svg>""",
    ),
    ("第十二章 时间同步与节点定位", "blk_fa371625a2"): (
        "三边测量与测距误差",
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 430" role="img" aria-label="三边定位示意图"><rect width="900" height="430" fill="#f8fafc"/><text x="30" y="40" font-size="24" font-family="sans-serif" fill="#172033">三个锚节点的距离圆交会确定未知节点</text><g transform="translate(60 70)"><circle cx="210" cy="80" r="145" fill="none" stroke="#2563eb" stroke-width="4" opacity=".75"/><circle cx="90" cy="275" r="145" fill="none" stroke="#0891b2" stroke-width="4" opacity=".75"/><circle cx="350" cy="285" r="150" fill="none" stroke="#d97706" stroke-width="4" opacity=".75"/><circle cx="210" cy="80" r="13" fill="#2563eb"/><circle cx="90" cy="275" r="13" fill="#0891b2"/><circle cx="350" cy="285" r="13" fill="#d97706"/><text x="210" y="58" text-anchor="middle" font-family="sans-serif">锚点 A</text><text x="90" y="310" text-anchor="middle" font-family="sans-serif">锚点 B</text><text x="350" y="320" text-anchor="middle" font-family="sans-serif">锚点 C</text><ellipse cx="220" cy="210" rx="34" ry="27" fill="#dc2626" opacity=".18" stroke="#dc2626" stroke-width="3"/><circle cx="220" cy="210" r="8" fill="#dc2626"/><text x="260" y="215" font-family="sans-serif" fill="#dc2626">位置估计</text></g><g transform="translate(560 110)" font-family="sans-serif"><text x="0" y="0" font-size="18" fill="#172033">误差如何扩散？</text><text x="0" y="45" fill="#475467">• 距离圆半径有误差带</text><text x="0" y="80" fill="#475467">• 理想交点变成交会区域</text><text x="0" y="115" fill="#475467">• 锚点几何分布影响放大倍数</text><text x="0" y="170" font-size="18" fill="#172033">非测距方法</text><text x="0" y="210" fill="#475467">用连通关系、跳数或质心估计</text><text x="0" y="245" fill="#475467">成本低，但坐标呈区域/跳跃式近似</text></g></svg>""",
    ),
}


def flashcard_block(title: str, cards: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "id": f"blk_wsn{list(REVIEW_CARDS).index(title)+5:02d}cards",
        "type": "flash_cards",
        "status": "ready",
        "title": "概念复习卡",
        "params": {"chapter_title": title},
        "payload": {"cards": [{"front": front, "back": back} for front, back in cards]},
        "source_anchors": [],
        "metadata": {"curated_by": "Codex", "curation_version": "wsn-theory-v1"},
        "error": "",
    }


def quiz_block(title: str, questions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": f"blk_wsn{list(NEW_QUIZZES).index(title)+5:02d}quiz",
        "type": "quiz",
        "status": "ready",
        "title": "章节自测",
        "params": {"chapter_title": title, "num_questions": len(questions), "difficulty": "medium"},
        "payload": {"questions": questions, "topic": title},
        "source_anchors": [],
        "metadata": {"curated_by": "Codex", "curation_version": "wsn-theory-v1", "completed": len(questions), "failed": 0},
        "error": "",
    }


def repair_pages(book_root: Path, *, dry_run: bool) -> list[str]:
    actions: list[str] = []
    for page_path in sorted((book_root / "pages").glob("*.json")):
        page = json.loads(page_path.read_text(encoding="utf-8"))
        title = str(page.get("title") or "")
        changed = False
        for block in page.get("blocks", []):
            figure = FIGURES.get((title, str(block.get("id"))))
            if figure:
                figure_title, svg = figure
                block.update(
                    status="ready",
                    title=figure_title,
                    payload={"render_type": "svg", "code": {"language": "svg", "content": svg}, "description": figure_title, "chart_type": "diagram"},
                    error="",
                )
                meta = dict(block.get("metadata") or {})
                meta.pop("failure", None)
                meta.update({"curated_by": "Codex", "curation_version": "wsn-theory-v1", "review_notes": "Hand-authored SVG validated locally."})
                block["metadata"] = meta
                actions.append(f"{title}: repaired figure {block['id']}")
                changed = True
            if block.get("type") == "quiz" and title in FAILED_QUESTION_REPLACEMENTS:
                questions = (block.get("payload") or {}).get("questions") or []
                replacement = FAILED_QUESTION_REPLACEMENTS[title]
                replaced = False
                for index, question in enumerate(questions):
                    if "generation failed" in str(question.get("question") or "").lower():
                        questions[index] = replacement
                        replaced = True
                if replaced:
                    block["payload"]["questions"] = questions
                    block["metadata"] = {**(block.get("metadata") or {}), "failed": 0, "curated_by": "Codex", "curation_version": "wsn-theory-v1"}
                    actions.append(f"{title}: replaced failed quiz question")
                    changed = True

        types = [block.get("type") for block in page.get("blocks", [])]
        if title in NEW_QUIZZES and "quiz" not in types:
            page["blocks"].append(quiz_block(title, NEW_QUIZZES[title]))
            actions.append(f"{title}: added curated quiz")
            changed = True
        types = [block.get("type") for block in page.get("blocks", [])]
        if title in REVIEW_CARDS and "flash_cards" not in types:
            page["blocks"].append(flashcard_block(title, REVIEW_CARDS[title]))
            actions.append(f"{title}: added review cards")
            changed = True

        if changed:
            errors = [block for block in page.get("blocks", []) if block.get("status") != "ready"]
            page["status"] = "partial" if errors else "ready"
            page["error"] = "; ".join(str(block.get("error") or "") for block in errors if block.get("error"))
            if not dry_run:
                atomic_json_write(page_path, page)
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-root", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and args.backup_dir is None:
        parser.error("--backup-dir is required unless --dry-run is used")
    interactive_actions = apply_interactives(args.book_root, args.backup_dir, args.dry_run)
    repair_actions = repair_pages(args.book_root, dry_run=args.dry_run)
    for item in interactive_actions + repair_actions:
        print(item)
    if not args.dry_run:
        with (args.book_root / "log.md").open("a", encoding="utf-8") as handle:
            handle.write(f"- {datetime.now(timezone.utc).isoformat()} [curate_wsn_book] completed full-book repair and completion\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
