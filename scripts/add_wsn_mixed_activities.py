#!/usr/bin/env python3
"""Add five mixed-format learning activities to every WSN theory chapter.

Each chapter receives one native quiz, one native flash-card deck, one drag
classification, one drag ordering task, and one concept-matching task.  Every
activity is inserted after an exact, reviewed subsection anchor.  The three
HTML activities are dependency-free and support both pointer dragging and a
click/keyboard fallback.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import shutil
from typing import Any

from deeptutor.book.blocks.interactive import build_interactive_prompt

try:
    from curate_wsn_interactives import atomic_json_write, validate_widget
    from expand_wsn_interactives import PLACEMENTS, split_section, subsection_heading
except ModuleNotFoundError:
    from scripts.curate_wsn_interactives import atomic_json_write, validate_widget
    from scripts.expand_wsn_interactives import PLACEMENTS, split_section, subsection_heading


@dataclass(frozen=True)
class Quiz:
    slug: str
    title: str
    question: str
    options: tuple[str, str, str, str]
    correct: str
    explanation: str


@dataclass(frozen=True)
class Flash:
    slug: str
    title: str
    cards: tuple[tuple[str, str, str], ...]


@dataclass(frozen=True)
class Classify:
    slug: str
    title: str
    instruction: str
    groups: tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True)
class Sequence:
    slug: str
    title: str
    instruction: str
    steps: tuple[str, ...]


@dataclass(frozen=True)
class Match:
    slug: str
    title: str
    instruction: str
    pairs: tuple[tuple[str, str], ...]


Activity = Quiz | Flash | Classify | Sequence | Match


def Q(
    slug: str,
    title: str,
    question: str,
    options: tuple[str, str, str, str],
    correct: str,
    explanation: str,
) -> Quiz:
    return Quiz(slug, title, question, options, correct, explanation)


def F(slug: str, title: str, *cards: tuple[str, str, str]) -> Flash:
    return Flash(slug, title, tuple(cards))


def C(slug: str, title: str, instruction: str, *groups: tuple[str, tuple[str, ...]]) -> Classify:
    return Classify(slug, title, instruction, tuple(groups))


def S(slug: str, title: str, instruction: str, *steps: str) -> Sequence:
    return Sequence(slug, title, instruction, tuple(steps))


def P(slug: str, title: str, instruction: str, *pairs: tuple[str, str]) -> Match:
    return Match(slug, title, instruction, tuple(pairs))


PACKS: dict[str, tuple[Activity, ...]] = {
    "第一章 绪论": (
        Q(
            "density",
            "连通性快速判断",
            "在节点均匀随机部署、通信半径不变时，提高节点密度最直接改变的是哪一项？",
            ("平均邻居数增大", "单包长度减小", "采样精度提高", "时钟漂移消失"),
            "A",
            "密度首先改变空间邻接关系；它可能改善连通，但也会增加竞争与维护开销。",
        ),
        F(
            "aggregation",
            "数据中心网络概念卡",
            (
                "数据聚合",
                "在中间节点合并相关观测，减少重复传输。",
                "想一想：聚合率越高是否一定越好？",
            ),
            (
                "以数据为中心",
                "按观测内容和属性组织通信，而不是只按节点地址。",
                "关注‘要什么数据’，而非‘哪个节点’。",
            ),
            ("能量约束", "通信通常是节点最主要、也最可控的能耗来源。", "先减少无效传输。"),
        ),
        C(
            "scale",
            "控制信息分类",
            "把卡片拖到更符合的控制方式中。",
            ("集中式全局状态", ("维护全网拓扑矩阵", "汇聚节点统一计算路由")),
            ("分布式局部状态", ("只维护一跳邻居表", "节点依据局部信息转发")),
        ),
        S(
            "latency-chain",
            "感知到决策链排序",
            "按一次环境事件从发生到执行反馈的典型顺序排列。",
            "传感器采样物理量",
            "节点完成量化与预处理",
            "多跳网络转发数据",
            "汇聚端分析并形成决策",
            "执行器或人员采取行动",
        ),
        P(
            "redundancy",
            "应用场景与关键约束配对",
            "选择左侧场景，再选择最典型的首要约束。",
            ("森林火情监测", "低功耗与大范围覆盖"),
            ("工业设备监测", "低时延与高可靠性"),
            ("结构健康监测", "长期稳定采样"),
            ("战场侦察", "自组织与抗毁性"),
        ),
    ),
    "第二章 传感器网络节点": (
        Q(
            "sampling",
            "采样策略快速判断",
            "目标信号最高有效频率为 20 Hz。为了避免混叠，理论上采样率至少应满足什么关系？",
            ("低于 20 Hz", "等于 20 Hz", "不低于 40 Hz", "与信号频率无关"),
            "C",
            "奈奎斯特条件要求采样率至少为最高频率的两倍，工程上还需留出滤波裕量。",
        ),
        F(
            "radio-state",
            "无线电状态翻转卡",
            ("发送态", "功放与射频链工作，瞬时功耗通常较高。", "发送完成后应尽快退出。"),
            ("接收/监听态", "接收机持续开启，功耗可能接近发送态。", "空闲侦听是隐蔽的耗能大户。"),
            ("休眠态", "关闭大部分射频电路，仅保留唤醒条件。", "低占空比设计的基础。"),
        ),
        C(
            "adc",
            "节点信号链分类",
            "将功能放入传感前端、处理单元或通信单元。",
            ("传感与调理", ("温度敏感元件", "抗混叠滤波")),
            ("计算与存储", ("ADC量化后的数字滤波", "本地缓存")),
            ("无线通信", ("信道编码", "射频发射")),
        ),
        S(
            "cpu-duty",
            "节点一次唤醒周期排序",
            "按低功耗节点从休眠到再次休眠的典型流程排列。",
            "定时器触发唤醒",
            "启动传感器并等待稳定",
            "采样与本地处理",
            "打开发射机发送结果",
            "关闭外设并进入休眠",
        ),
        P(
            "harvest",
            "能量采集方式配对",
            "把环境能源与更典型的采集器件配对。",
            ("日光", "光伏电池"),
            ("设备振动", "压电或电磁采集器"),
            ("冷热温差", "热电发电器"),
            ("射频环境", "整流天线"),
        ),
    ),
    "第三章 操作系统": (
        Q(
            "event-queue",
            "并发模型快速判断",
            "事件驱动系统最适合哪类节点负载？",
            (
                "大量长期阻塞线程",
                "短小、非阻塞的事件处理",
                "必须依赖桌面虚拟内存",
                "每个任务都需要独立大栈",
            ),
            "B",
            "事件处理应短小并尽快返回；长计算会阻塞后续事件，需拆分或交给任务机制。",
        ),
        F(
            "stack",
            "轻量操作系统概念卡",
            ("事件", "由中断、定时器或消息触发的短处理过程。", "共享栈可节省内存。"),
            ("线程", "拥有独立执行上下文，可自然表达阻塞流程。", "需要额外栈空间。"),
            ("任务", "操作系统调度和资源分配的基本执行实体。", "粒度取决于内核设计。"),
        ),
        C(
            "timer",
            "调度策略分类",
            "把调度特征拖到对应模型。",
            ("协作式", ("任务主动让出处理器", "实现简单且切换开销低")),
            ("抢占式", ("高优先级任务可打断低优先级任务", "响应及时但同步更复杂")),
            ("时间片轮转", ("周期性切换就绪任务", "强调公平分享处理器")),
        ),
        S(
            "mutex",
            "互斥访问流程排序",
            "按安全更新共享传感缓存的流程排列。",
            "等待并获得互斥锁",
            "读取共享缓存当前状态",
            "完成不可分割的更新",
            "释放互斥锁",
            "通知等待任务数据已更新",
        ),
        P(
            "context",
            "实时性指标配对",
            "把指标与它描述的时间含义配对。",
            ("响应时间", "请求到任务完成的时间"),
            ("截止期", "任务必须完成的最晚时刻"),
            ("抖动", "周期任务实际启动时刻的波动"),
            ("上下文切换开销", "保存与恢复执行状态所耗时间"),
        ),
    ),
    "第四章 无线传感网络体系结构": (
        Q(
            "cluster-size",
            "分簇规模快速判断",
            "簇过大时，簇头最可能首先面临什么压力？",
            (
                "成员数据接收与聚合负担增大",
                "所有成员距离自动缩短",
                "路径损耗指数变为零",
                "节点不再需要同步",
            ),
            "A",
            "簇成员增加会放大簇内调度、接收和聚合负担；簇太小则会增加簇间控制开销。",
        ),
        F(
            "gateway",
            "体系结构角色卡",
            ("普通节点", "完成感知、局部处理和短距离转发。", "资源最受限。"),
            ("簇头", "汇聚成员数据并承担较多协调与转发。", "宜轮换以均衡能量。"),
            ("网关/汇聚节点", "连接传感网络与外部网络或应用。", "常是流量与安全边界。"),
        ),
        C(
            "cross-layer",
            "跨层信息分类",
            "将信息拖到其主要来源协议层。",
            ("物理/MAC层", ("RSSI与链路质量", "信道忙闲状态")),
            ("网络层", ("邻居与下一跳", "路径代价")),
            ("应用层", ("事件紧急程度", "数据相关性")),
        ),
        S(
            "hierarchy",
            "分层网络成形排序",
            "按一次典型分簇组网过程排序。",
            "节点发现邻居并估计链路",
            "选举或指定候选簇头",
            "普通节点选择并加入簇",
            "簇头建立簇内调度",
            "簇头汇聚数据并向网关转发",
        ),
        P(
            "rotation",
            "轮换依据配对",
            "把轮换依据与主要目标配对。",
            ("剩余能量", "避免低电量节点继续担任簇头"),
            ("到汇聚节点距离", "降低簇间转发代价"),
            ("节点度", "选择连接较丰富的协调者"),
            ("历史担任次数", "提高长期公平性"),
        ),
    ),
    "第五章 无线通信基础": (
        Q(
            "path-loss",
            "路径损耗快速判断",
            "在对数距离模型中，其他条件不变、距离增大十倍时，路径损耗增加约多少？",
            ("n dB", "10n dB", "20n² dB", "与 n 无关"),
            "B",
            "模型中的距离项是 10n·log10(d/d0)，距离变为十倍时对数项增加 1。",
        ),
        F(
            "snr",
            "链路质量概念卡",
            ("SNR", "接收信号功率与噪声功率之比。", "反映无外部干扰时的接收质量。"),
            ("SINR", "信号相对于干扰与噪声之和的比值。", "共享信道中更有解释力。"),
            ("BER", "接收比特发生错误的概率。", "由调制、编码与信道共同决定。"),
        ),
        C(
            "sinr",
            "无线损伤分类",
            "把现象拖到噪声、干扰或衰落类别。",
            ("噪声", ("接收机热噪声", "电子器件噪声")),
            ("干扰", ("邻近节点同信道发送", "外部无线系统占用频谱")),
            ("衰落", ("建筑物遮挡", "多径相消")),
        ),
        S(
            "coherence",
            "接收机处理链排序",
            "按数字无线接收机恢复数据的典型顺序排列。",
            "天线接收叠加的射频信号",
            "下变频与滤波",
            "采样和同步",
            "解调与判决",
            "信道译码并校验数据",
        ),
        P(
            "shadow",
            "传播现象配对",
            "把传播现象与典型时间/空间特征配对。",
            ("自由空间损耗", "平均功率随距离规律下降"),
            ("阴影衰落", "障碍遮挡导致慢变功率起伏"),
            ("小尺度多径", "波长尺度移动即可明显变化"),
            ("频率选择性衰落", "不同频率分量受到不同衰减"),
        ),
    ),
    "第六章 拓扑控制技术": (
        Q(
            "degree",
            "节点度快速判断",
            "通信半径不断增大，通常会带来哪组同时发生的结果？",
            ("节点度提高且竞争范围扩大", "节点度降低且能耗归零", "覆盖必然下降", "路由不再需要"),
            "A",
            "较大半径改善局部连通，但会增加发射能耗、干扰和邻居维护开销。",
        ),
        F(
            "power",
            "拓扑控制概念卡",
            ("功率控制", "调整发射功率改变可达邻居集合。", "目标不是一味降低功率。"),
            ("逻辑拓扑", "从物理可达链路中选择实际使用的连接。", "可稀疏化以减少干扰。"),
            ("连通支配集", "少量骨干节点覆盖并连接全网。", "常用于构造虚拟骨干。"),
        ),
        C(
            "backbone",
            "骨干节点角色分类",
            "将行为拖到骨干节点或普通节点。",
            ("骨干节点", ("承担跨区域转发", "维护骨干邻接关系", "接收多个成员的数据")),
            ("普通节点", ("选择附近骨干接入", "大部分时间可低功耗休眠", "只在本地生成感知数据")),
        ),
        S(
            "hysteresis",
            "拓扑调整流程排序",
            "按带滞回的功率调整流程排列。",
            "周期测量链路质量",
            "比较指标与上下阈值",
            "连续多次越界后触发调整",
            "改变发射功率或父节点",
            "观察稳定窗口再允许下一次切换",
        ),
        P(
            "coverage-connect",
            "拓扑目标配对",
            "把目标与主要判据配对。",
            ("连通性", "任意必要节点间存在通信路径"),
            ("覆盖性", "关注区域被足够传感器感知"),
            ("能量效率", "降低发射、监听和维护开销"),
            ("鲁棒性", "节点失效后仍保留可用结构"),
        ),
    ),
    "第七章 MAC协议": (
        Q(
            "duty",
            "占空比快速判断",
            "低功耗监听协议中，缩短节点唤醒周期通常会怎样？",
            ("时延降低但监听能耗增加", "时延和能耗都必然降低", "碰撞完全消失", "不再需要前导码"),
            "A",
            "更频繁唤醒更容易及时接收，却增加空闲监听；MAC设计需在时延与寿命之间取舍。",
        ),
        F(
            "csma",
            "MAC机制翻转卡",
            ("载波侦听", "发送前检测信道是否忙。", "不能彻底解决隐藏终端。"),
            ("随机退避", "冲突后等待随机时间再竞争。", "减少重复同步碰撞。"),
            ("确认与重传", "用 ACK 判断链路层交付是否成功。", "提高可靠性但增加开销。"),
        ),
        C(
            "tdma",
            "接入方式分类",
            "将特征拖到竞争式或调度式接入。",
            ("CSMA类竞争接入", ("按需发送灵活", "高负载时碰撞增多", "需要载波侦听与退避")),
            ("TDMA类调度接入", ("时隙可提供确定性", "需要时间同步", "空闲时隙可能浪费")),
        ),
        S(
            "preamble",
            "低功耗侦听发送排序",
            "按异步低功耗监听的一次典型通信过程排序。",
            "接收节点周期性短暂侦听",
            "发送节点发出足够长的前导序列",
            "接收节点检测到前导并保持唤醒",
            "发送节点传输数据帧",
            "接收节点确认后双方休眠",
        ),
        P(
            "hidden",
            "MAC问题配对",
            "把问题与最典型的成因配对。",
            ("隐藏终端", "两个发送者互听不到却同时干扰同一接收者"),
            ("暴露终端", "节点误以为邻近发送会妨碍自己的接收者"),
            ("空闲侦听", "无线电开启但没有有效帧到达"),
            ("串音接收", "接收并处理并非发给自己的帧"),
        ),
    ),
    "第八章 路由技术": (
        Q(
            "etx",
            "ETX快速判断",
            "一条链路正向成功率 0.8、反向确认成功率 0.5，其 ETX 约为多少？",
            ("0.4", "1.3", "2.5", "8"),
            "C",
            "ETX=1/(df×dr)=1/(0.8×0.5)=2.5，表示平均约需 2.5 次发送完成一次确认交付。",
        ),
        F(
            "hop-energy",
            "路由代价概念卡",
            ("最少跳数", "优先选择跳数最少的路径。", "可能包含长距离高损耗链路。"),
            ("ETX", "累计期望发送次数衡量链路可靠代价。", "需同时估计数据与确认方向。"),
            ("剩余能量感知", "让路径避开电量紧张节点。", "可延缓热点节点过早死亡。"),
        ),
        C(
            "leach",
            "LEACH轮次角色分类",
            "把动作拖到建立阶段或稳定传输阶段。",
            ("簇建立阶段", ("广播簇头候选", "成员选择簇头", "分配簇内时隙")),
            ("稳定传输阶段", ("成员按时隙上传", "簇头聚合数据", "簇头向汇聚节点发送")),
        ),
        S(
            "greedy",
            "地理贪心转发排序",
            "按节点进行一次地理路由决策的逻辑顺序排列。",
            "获得自身、邻居和目的地位置",
            "筛选比自己更接近目的地的邻居",
            "计算候选邻居的距离或综合代价",
            "选择最优候选作为下一跳",
            "若无候选则进入空洞恢复策略",
        ),
        P(
            "aggregate-route",
            "路由范式配对",
            "把路由范式与其寻址依据配对。",
            ("地址中心路由", "目标节点标识"),
            ("数据中心路由", "属性、事件或查询内容"),
            ("地理路由", "节点与目的区域的位置"),
            ("层次路由", "簇、区域或角色层级"),
        ),
    ),
    "第九章 传输控制技术": (
        Q(
            "queue",
            "拥塞快速判断",
            "节点到达速率长期大于服务速率时，即使缓存很大，最终最可能发生什么？",
            ("队列稳定在零", "排队时延持续增长并最终丢包", "链路误码率自动变零", "吞吐量无限增长"),
            "B",
            "缓存只能延迟溢出，不能改变长期到达率大于服务率这一不稳定条件。",
        ),
        F(
            "retransmit",
            "可靠传输概念卡",
            ("端到端重传", "由源端在超时后重发整段路径。", "状态简单但长路径代价高。"),
            ("逐跳重传", "每一跳本地确认并修复丢包。", "反应快但节点需维护状态。"),
            ("选择性确认", "只指出缺失的数据片段。", "减少已成功数据的重复发送。"),
        ),
        C(
            "rate",
            "拥塞信号分类",
            "把观测拖到隐式信号或显式信号。",
            ("隐式拥塞信号", ("队列长度持续上升", "信道忙比例升高", "往返时间增长")),
            ("显式拥塞信号", ("拥塞通知位", "下游回压消息", "汇聚端请求降低报告频率")),
        ),
        S(
            "backpressure",
            "逐跳回压过程排序",
            "按下游拥塞向上游传播的典型顺序排列。",
            "中继节点检测队列超过阈值",
            "向其上游邻居发出回压通知",
            "上游降低发送或聚合数据",
            "本地队列逐步排空",
            "拥塞解除后渐进恢复速率",
        ),
        P(
            "priority",
            "业务与控制目标配对",
            "把数据类别与更合适的传输目标配对。",
            ("火警事件", "低时延和高优先级"),
            ("周期温度数据", "稳定吞吐与能量效率"),
            ("固件更新", "完整可靠并允许较长时延"),
            ("重复环境样本", "可聚合或降采样"),
        ),
    ),
    "第十章 实用化组网标准协议": (
        Q(
            "superframe",
            "超帧快速判断",
            "IEEE 802.15.4 信标模式中，GTS 的主要作用是什么？",
            (
                "为关键设备预留无竞争时隙",
                "增加 IPv6 地址长度",
                "完成应用层加密",
                "替代所有信标同步",
            ),
            "A",
            "GTS位于无竞争期，为有确定性需求的设备提供专用时隙，但数量和带宽有限。",
        ),
        F(
            "fragment",
            "协议适配概念卡",
            ("IPv6头压缩", "利用链路上下文省略可推断字段。", "降低小帧中的头部比例。"),
            ("分片", "把超出链路MTU的数据报拆成多个片段。", "丢一个片段可能导致整报重组失败。"),
            ("重组", "接收端按标识和偏移恢复原始数据报。", "需要缓存与超时管理。"),
        ),
        C(
            "ble",
            "协议特征分类",
            "把特征拖到更符合的协议族。",
            ("BLE", ("低功耗广播与连接事件", "手机生态兼容性强")),
            ("ZigBee", ("基于802.15.4的网状组网", "常见协调器与簇树角色")),
            ("6LoWPAN", ("面向IPv6适配", "头压缩与分片重组")),
        ),
        S(
            "channel-hop",
            "工业跳频通信排序",
            "按一次预先调度的跳频链路过程排列。",
            "网络分配时隙与信道偏移",
            "节点依据绝对时隙计算实际信道",
            "发送端和接收端同步切换信道",
            "在指定时隙交换数据与确认",
            "链路统计用于后续调度优化",
        ),
        P(
            "zigbee-tree",
            "标准协议机制配对",
            "把机制与其主要解决的问题配对。",
            ("ZigBee树地址", "沿层次结构进行低状态路由"),
            ("AODV类路由", "按需发现网状路径"),
            ("BLE广播", "无连接发布少量数据"),
            ("WirelessHART跳频", "降低窄带干扰与深衰落影响"),
        ),
    ),
    "第十一章 感知覆盖": (
        Q(
            "disk",
            "布尔感知模型快速判断",
            "布尔圆盘模型认为目标位于感知半径之外时，检测概率是多少？",
            ("必为1", "随距离线性下降", "直接视为0", "由通信半径决定"),
            "C",
            "布尔模型用清晰边界简化覆盖判定；真实传感通常更接近概率模型。",
        ),
        F(
            "poisson",
            "覆盖指标翻转卡",
            ("1-覆盖", "区域中每一点至少被一个节点感知。", "最基本的覆盖要求。"),
            ("k-覆盖", "区域中每一点至少被k个节点感知。", "提高冗余与容错能力。"),
            ("覆盖率", "满足覆盖判据的区域占总区域的比例。", "可通过网格采样近似计算。"),
        ),
        C(
            "kcover",
            "覆盖冗余分类",
            "把部署状态拖到欠覆盖、单覆盖或冗余覆盖。",
            ("欠覆盖", ("目标点没有任何节点可感知", "失效后出现监测盲区")),
            ("单覆盖", ("目标点恰好由一个节点感知", "该节点失效即失去覆盖")),
            ("冗余覆盖", ("目标点同时被多个节点感知", "可轮换休眠部分节点")),
        ),
        S(
            "grid",
            "网格覆盖评估排序",
            "按把连续区域转成可计算覆盖率的步骤排列。",
            "确定监测区域边界",
            "按给定分辨率划分网格",
            "逐格计算被多少节点感知",
            "依据k值标记满足与不满足",
            "统计满足网格占比并分析盲区",
        ),
        P(
            "failure",
            "部署策略配对",
            "把部署策略与其典型特点配对。",
            ("规则网格部署", "覆盖可预测且便于规划"),
            ("随机撒布", "实施方便但局部密度不均"),
            ("障碍感知部署", "绕开不可达区并重点补洞"),
            ("移动节点修复", "运行期重新布置以恢复覆盖"),
        ),
    ),
    "第十二章 时间同步与节点定位": (
        Q(
            "drift",
            "时钟漂移快速判断",
            "节点晶振偏差为40 ppm，连续100秒未同步，累计时间误差约为多少？",
            ("0.004 ms", "0.04 ms", "4 ms", "40 ms"),
            "C",
            "40 ppm×100 s=0.004 s，即4 ms；偏差会随未同步时间近似线性积累。",
        ),
        F(
            "twoway",
            "时间同步概念卡",
            ("时钟偏移", "两个时钟在同一真实时刻的读数差。", "同步首先要估计偏移。"),
            ("频率偏斜", "两个时钟走时速率的相对差异。", "不校正会不断重新产生偏移。"),
            ("传播时延", "报文从发送端到接收端所需时间。", "不对称会污染双向估计。"),
        ),
        C(
            "rbs",
            "同步误差来源分类",
            "将误差拖到发送侧、传播侧或接收侧。",
            ("发送侧", ("介质访问等待", "发送时刻软件排队")),
            ("传播侧", ("上下行路径不对称", "多跳路由变化")),
            ("接收侧", ("中断响应抖动", "时间戳位置不同")),
        ),
        S(
            "rssi",
            "RSSI定位流程排序",
            "按基于RSSI的多锚点定位流程排列。",
            "锚节点广播自身位置",
            "未知节点测量各锚点RSSI",
            "利用环境模型换算距离",
            "通过多边定位估计坐标",
            "用残差或滤波修正异常测量",
        ),
        P(
            "gdop",
            "定位方法配对",
            "把定位方法与其主要观测量配对。",
            ("RSSI测距", "接收信号强度"),
            ("ToA/TDoA", "信号到达时间或时间差"),
            ("AoA", "信号到达方向"),
            ("质心定位", "可听见的锚节点坐标集合"),
        ),
    ),
}


COMMON_CSS = r"""
:root{--bg:#f5f7fb;--card:#fff;--ink:#172033;--muted:#667085;--line:#dce3ee;--blue:#2563eb;--green:#16865b;--red:#dc2626;--soft:#eff6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 system-ui,-apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}.app{max-width:1000px;margin:auto;padding:18px}.head h1{font-size:20px;margin:0 0 4px}.head p{margin:0 0 14px;color:var(--muted)}.board{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:0 8px 24px rgba(15,23,42,.04)}button{font:inherit}.btn{border:1px solid var(--line);border-radius:9px;background:#fff;color:var(--ink);padding:8px 11px;cursor:pointer}.btn:hover,.btn:focus{border-color:var(--blue);outline:2px solid transparent}.btn.primary{background:var(--blue);color:#fff;border-color:var(--blue)}.items,.zones,.columns{display:grid;gap:10px}.items{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin-bottom:12px}.zones,.columns{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}.item,.choice{border:1px solid var(--line);border-radius:10px;background:#fff;padding:10px;cursor:grab;min-height:46px}.item.selected,.choice.selected{outline:2px solid var(--blue);background:var(--soft)}.item.good,.choice.good{border-color:var(--green);background:#ecfdf3}.item.bad,.choice.bad{border-color:var(--red);background:#fff1f2}.zone{border:2px dashed #b9c5d6;border-radius:12px;background:#fbfcfe;min-height:120px;padding:10px}.zone h2{font-size:13px;margin:0 0 8px}.zone .item{margin:7px 0}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.feedback{margin-top:12px;padding:10px 12px;border-left:3px solid var(--blue);border-radius:0 8px 8px 0;background:var(--soft);color:#1e3a8a;min-height:42px}.sequence{display:grid;gap:8px}.sequence .item{display:flex;align-items:center;gap:9px}.badge{display:inline-flex;width:25px;height:25px;align-items:center;justify-content:center;border-radius:50%;background:#e8eef8;color:#344054;font-weight:700}.pair-col{display:grid;gap:8px}.choice{cursor:pointer}.progress{color:var(--muted);font-size:12px;margin-top:8px}@media(max-width:680px){.app{padding:12px}.columns{grid-template-columns:1fr}}
"""


def _document(title: str, instruction: str, body: str, script: str, kind: str) -> str:
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title><style>{COMMON_CSS}</style></head><body>"
        '<main class="app" data-qlearn-interactive="curated-v1">'
        f'<header class="head"><h1>{html.escape(title)}</h1><p>{html.escape(instruction)}</p></header>'
        f'<section class="board" data-activity-kind="{kind}">{body}</section></main>'
        f"<script>{script}\nwindow.__QLEARN_INTERACTIVE_READY__=true;</script></body></html>"
    )


def classification_widget(activity: Classify) -> str:
    items = [(item, group) for group, values in activity.groups for item in values]
    item_html = "".join(
        f'<button class="item" draggable="true" data-answer="{html.escape(group)}">{html.escape(item)}</button>'
        for item, group in items
    )
    zones = "".join(
        f'<div class="zone" data-zone="{html.escape(group)}"><h2>{html.escape(group)}</h2></div>'
        for group, _ in activity.groups
    )
    body = f'<div class="items" id="bank">{item_html}</div><div class="zones">{zones}</div><div class="actions"><button class="btn primary" id="check">检查分类</button><button class="btn" id="reset">重新开始</button></div><div class="feedback" id="feedback">可拖拽卡片；也可先点卡片，再点目标分类框。</div>'
    script = r"""
const bank=document.getElementById('bank'),items=[...document.querySelectorAll('.item')],zones=[...document.querySelectorAll('.zone')];let chosen=null,dragged=null;
function choose(el){items.forEach(x=>x.classList.remove('selected'));chosen=el;el.classList.add('selected')}
items.forEach(el=>{el.addEventListener('click',()=>choose(el));el.addEventListener('dragstart',()=>{dragged=el;choose(el)})});
zones.forEach(z=>{z.addEventListener('dragover',e=>e.preventDefault());z.addEventListener('drop',e=>{e.preventDefault();if(dragged)z.appendChild(dragged)});z.addEventListener('click',e=>{if(e.target===z||e.target.tagName==='H2'){if(chosen)z.appendChild(chosen)}})});
document.getElementById('check').addEventListener('click',()=>{let ok=0;items.forEach(el=>{let good=el.parentElement?.dataset.zone===el.dataset.answer;el.classList.toggle('good',good);el.classList.toggle('bad',!good);if(good)ok++});feedback.textContent=ok===items.length?'全部正确：你已经能依据机制特征完成分类。':'已正确 '+ok+'/'+items.length+'；红色卡片需要重新判断。'});
document.getElementById('reset').addEventListener('click',()=>{items.forEach(el=>{bank.appendChild(el);el.className='item'});chosen=null;feedback.textContent='已重置。拖拽卡片，或使用点击方式重新分类。'});
"""
    return _document(activity.title, activity.instruction, body, script, "drag-classify")


def sequence_widget(activity: Sequence) -> str:
    scrambled = list(activity.steps[1::2] + activity.steps[::2])
    items = "".join(
        f'<button class="item" draggable="true" data-answer="{activity.steps.index(step)}"><span class="badge">↕</span><span>{html.escape(step)}</span></button>'
        for step in scrambled
    )
    body = f'<div class="sequence" id="sequence">{items}</div><div class="actions"><button class="btn" id="up">上移所选</button><button class="btn" id="down">下移所选</button><button class="btn primary" id="check">检查顺序</button><button class="btn" id="reset">重新打乱</button></div><div class="feedback" id="feedback">拖拽调整顺序；也可选择卡片后使用上移、下移。</div>'
    script = r"""
const list=document.getElementById('sequence');let selected=null,dragged=null;function rows(){return [...list.querySelectorAll('.item')]}function choose(el){rows().forEach(x=>x.classList.remove('selected'));selected=el;el.classList.add('selected')}
list.addEventListener('click',e=>{let el=e.target.closest('.item');if(el)choose(el)});list.addEventListener('dragstart',e=>{dragged=e.target.closest('.item');choose(dragged)});list.addEventListener('dragover',e=>{e.preventDefault();let over=e.target.closest('.item');if(over&&dragged&&over!==dragged){let r=over.getBoundingClientRect();list.insertBefore(dragged,e.clientY<r.top+r.height/2?over:over.nextSibling)}});
document.getElementById('up').addEventListener('click',()=>{if(selected&&selected.previousElementSibling)list.insertBefore(selected,selected.previousElementSibling)});document.getElementById('down').addEventListener('click',()=>{if(selected&&selected.nextElementSibling)list.insertBefore(selected.nextElementSibling,selected)});
document.getElementById('check').addEventListener('click',()=>{let all=rows(),ok=0;all.forEach((el,i)=>{let good=+el.dataset.answer===i;el.classList.toggle('good',good);el.classList.toggle('bad',!good);if(good)ok++});feedback.textContent=ok===all.length?'顺序正确：流程中的因果与依赖关系已经理清。':'当前有 '+ok+'/'+all.length+' 个位置正确；根据前后依赖继续调整。'});
document.getElementById('reset').addEventListener('click',()=>{rows().sort(()=>Math.random()-.5).forEach(el=>{el.className='item';list.appendChild(el)});selected=null;feedback.textContent='已重新打乱，请再次排序。'});
"""
    return _document(activity.title, activity.instruction, body, script, "drag-sequence")


def matching_widget(activity: Match) -> str:
    left = "".join(
        f'<button class="choice left" data-key="{i}">{html.escape(a)}</button>'
        for i, (a, _) in enumerate(activity.pairs)
    )
    ordered = list(enumerate(activity.pairs))[1::2] + list(enumerate(activity.pairs))[::2]
    right = "".join(
        f'<button class="choice right" data-key="{i}">{html.escape(pair[1])}</button>'
        for i, pair in ordered
    )
    body = f'<div class="columns"><div class="pair-col" id="left">{left}</div><div class="pair-col" id="right">{right}</div></div><div class="actions"><button class="btn" id="reset">重新开始</button></div><div class="progress" id="progress">已完成 0/{len(activity.pairs)} 对</div><div class="feedback" id="feedback">先选择左侧概念，再选择右侧对应解释。</div>'
    script = r"""
const left=[...document.querySelectorAll('.left')],right=[...document.querySelectorAll('.right')];let selected=null,done=new Set();function clear(){left.forEach(x=>x.classList.remove('selected'));selected=null}left.forEach(el=>el.addEventListener('click',()=>{if(done.has(el.dataset.key))return;clear();selected=el;el.classList.add('selected')}));right.forEach(el=>el.addEventListener('click',()=>{if(!selected){feedback.textContent='请先选择一个左侧概念。';return}let good=el.dataset.key===selected.dataset.key;if(good){selected.classList.add('good');el.classList.add('good');selected.disabled=true;el.disabled=true;done.add(el.dataset.key);feedback.textContent=done.size===left.length?'全部配对正确：概念与机制已建立联系。':'配对正确，请继续。';progress.textContent='已完成 '+done.size+'/'+left.length+' 对';clear()}else{el.classList.add('bad');feedback.textContent='这组关系不成立，请比较定义中的关键词。';setTimeout(()=>el.classList.remove('bad'),600)}}));document.getElementById('reset').addEventListener('click',()=>{done.clear();[...left,...right].forEach(el=>{el.disabled=false;el.className='choice '+(el.classList.contains('left')?'left':'right')});clear();progress.textContent='已完成 0/'+left.length+' 对';feedback.textContent='已重置，请重新配对。'});
"""
    return _document(activity.title, activity.instruction, body, script, "concept-match")


def _prompt(chapter: dict[str, Any], activity: Activity) -> tuple[str, str]:
    kind = {
        Quiz: "知识检查题",
        Flash: "翻转记忆卡",
        Classify: "拖拽分类",
        Sequence: "拖拽排序",
        Match: "概念配对",
    }[type(activity)]
    result = build_interactive_prompt(
        language="zh",
        chapter_title=chapter["title"],
        chapter_summary=str(chapter.get("summary") or ""),
        objectives=[str(item) for item in chapter.get("learning_objectives") or []],
        focus=activity.title,
        interaction=kind,
    )
    return result.user_input, result.history_context


def block_for(chapter: dict[str, Any], chapter_number: int, activity: Activity) -> dict[str, Any]:
    prompt, history = _prompt(chapter, activity)
    timestamp = datetime.now(timezone.utc).timestamp()
    base: dict[str, Any] = {
        "id": f"blk_wsnmix_{chapter_number:02d}_{activity.slug}_{type(activity).__name__.lower()}",
        "status": "ready",
        "title": activity.title,
        "params": {"focus": activity.title, "interaction": type(activity).__name__.lower()},
        "source_anchors": [],
        "metadata": {
            "curated_by": "Codex",
            "curation_version": "wsn-mixed-v3",
            "activity_type": type(activity).__name__.lower(),
            "native_prompt": prompt,
            "native_history_context": history,
            "review_notes": "Native prompt recorded; reviewed deterministic activity installed.",
        },
        "error": "",
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    if isinstance(activity, Quiz):
        base.update(
            {
                "type": "quiz",
                "payload": {
                    "questions": [
                        {
                            "question_id": f"{base['id']}_q1",
                            "question": activity.question,
                            "question_type": "single_choice",
                            "options": dict(zip("ABCD", activity.options, strict=True)),
                            "correct_answer": activity.correct,
                            "explanation": activity.explanation,
                            "difficulty": "concept",
                        }
                    ]
                },
            }
        )
    elif isinstance(activity, Flash):
        base.update(
            {
                "type": "flash_cards",
                "payload": {
                    "cards": [
                        {"front": front, "back": back, "hint": hint}
                        for front, back, hint in activity.cards
                    ]
                },
            }
        )
    else:
        if isinstance(activity, Classify):
            code, chart_type = classification_widget(activity), "drag_classification"
        elif isinstance(activity, Sequence):
            code, chart_type = sequence_widget(activity), "drag_sequence"
        else:
            code, chart_type = matching_widget(activity), "concept_matching"
        validate_widget(code)
        base.update(
            {
                "type": "interactive",
                "payload": {
                    "render_type": "html",
                    "code": {"language": "html", "content": code},
                    "description": f"{activity.title}：完成操作后获得即时中文反馈。",
                    "chart_type": chart_type,
                },
            }
        )
    return base


def apply(book_root: Path, *, backup_dir: Path | None, dry_run: bool) -> list[str]:
    spine = json.loads((book_root / "spine.json").read_text(encoding="utf-8"))
    chapters = {chapter["title"]: chapter for chapter in spine.get("chapters", [])}
    pages: list[tuple[Path, dict[str, Any]]] = []
    actions: list[str] = []
    for page_path in sorted((book_root / "pages").glob("*.json")):
        page = json.loads(page_path.read_text(encoding="utf-8"))
        title = str(page.get("title") or "")
        activities = PACKS.get(title)
        if activities is None:
            continue
        if len(activities) != 5 or len({type(item) for item in activities}) != 5:
            raise ValueError(f"{title}: expected five distinct activity formats")
        placements = PLACEMENTS.get(title)
        if placements is None or {item.slug for item in activities} != set(placements):
            raise ValueError(f"{title}: activity slugs must match reviewed placements")
        chapter = chapters.get(title)
        if chapter is None:
            raise ValueError(f"missing spine chapter: {title}")
        additions = {
            item.slug: block_for(chapter, int(page.get("order") or 0), item) for item in activities
        }
        retained = [
            block
            for block in page.get("blocks", [])
            if not str(block.get("id") or "").startswith("blk_wsnmix_")
        ]
        slug_by_heading = {heading: slug for slug, heading in placements.items()}
        distributed: list[dict[str, Any]] = []
        placed: list[str] = []
        for block in retained:
            fragments = split_section(block) if block.get("type") == "section" else [block]
            for fragment in fragments:
                distributed.append(fragment)
                slug = slug_by_heading.get(subsection_heading(fragment))
                if slug:
                    distributed.append(additions[slug])
                    placed.append(slug)
        if set(placed) != set(additions) or len(placed) != 5:
            raise ValueError(f"{title}: placement failed; placed={placed}")
        page["blocks"] = distributed
        page["updated_at"] = datetime.now(timezone.utc).timestamp()
        pages.append((page_path, page))
        actions.append(
            f"{title}: placed quiz, flash cards, classification, sequence, and matching activities"
        )
    if len(pages) != 12:
        raise ValueError(f"expected 12 theory pages, found {len(pages)}")
    if dry_run:
        return actions
    if backup_dir is None:
        raise ValueError("--backup-dir is required unless --dry-run is used")
    if backup_dir.exists():
        raise FileExistsError(f"backup directory already exists: {backup_dir}")
    backup_dir.mkdir(parents=True)
    for page_path, page in pages:
        shutil.copy2(page_path, backup_dir / page_path.name)
        atomic_json_write(page_path, page)
    with (book_root / "curation.log").open("a", encoding="utf-8") as handle:
        handle.write(
            f"{datetime.now(timezone.utc).isoformat()} installed 60 mixed-format v3 activities\n"
        )
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-root", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for action in apply(args.book_root.resolve(), backup_dir=args.backup_dir, dry_run=args.dry_run):
        print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
