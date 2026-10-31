#!/usr/bin/env python3
"""Add five reviewed theory interactives to every WSN chapter.

The platform's native interactive prompt builder supplies the prompt recorded
on every block.  The actual widget is deterministic, self-contained HTML made
from the reviewed specifications below; no model output is trusted as code.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from deeptutor.book.blocks.interactive import build_interactive_prompt

try:
    from curate_wsn_interactives import atomic_json_write, document, validate_widget
except ModuleNotFoundError:
    from scripts.curate_wsn_interactives import atomic_json_write, document, validate_widget


@dataclass(frozen=True)
class Axis:
    label: str
    minimum: float
    maximum: float
    value: float
    step: float
    unit: str = ""


@dataclass(frozen=True)
class Metric:
    label: str
    expression: str
    unit: str = ""
    decimals: int = 1


@dataclass(frozen=True)
class Lab:
    slug: str
    title: str
    focus: str
    x: Axis
    y: Axis
    metrics: tuple[Metric, Metric, Metric]
    note: str


def A(label: str, lo: float, hi: float, value: float, step: float, unit: str = "") -> Axis:
    return Axis(label, lo, hi, value, step, unit)


def M(label: str, expression: str, unit: str = "", decimals: int = 1) -> Metric:
    return Metric(label, expression, unit, decimals)


def L(
    slug: str,
    title: str,
    focus: str,
    x: Axis,
    y: Axis,
    metrics: tuple[Metric, Metric, Metric],
    note: str,
) -> Lab:
    return Lab(slug, title, focus, x, y, metrics, note)


LABS: dict[str, list[Lab]] = {
    "第一章 绪论": [
        L(
            "density",
            "部署密度与邻居规模",
            "节点密度、通信半径与平均邻居数",
            A("节点密度", 5, 100, 35, 5, " 个/km²"),
            A("通信半径", 50, 400, 180, 10, " m"),
            (
                M("平均邻居数", "Math.PI*y*y*x/1e6", " 个"),
                M("孤立概率", "100*Math.exp(-Math.PI*y*y*x/1e6)", "%"),
                M("每节点维护开销", "12*Math.PI*y*y*x/1e6", " B/s"),
            ),
            "密度或通信半径增大通常改善局部连通，却同步放大邻居维护、竞争和干扰范围。",
        ),
        L(
            "aggregation",
            "数据聚合节流",
            "相关观测、聚合率与网络通信量",
            A("源节点数", 10, 500, 120, 10, " 个"),
            A("聚合后保留比例", 5, 100, 35, 5, "%"),
            (
                M("原始报文", "x", " 包/轮", 0),
                M("聚合报文", "x*y/100", " 包/轮", 0),
                M("减少比例", "100-y", "%"),
            ),
            "以数据为中心的价值来自去冗余；保留比例过低时，也可能损失局部异常和可追溯性。",
        ),
        L(
            "scale",
            "网络规模与控制面",
            "规模、更新周期与控制报文负担",
            A("节点数", 20, 2000, 300, 20, " 个"),
            A("状态更新周期", 1, 120, 30, 1, " s"),
            (
                M("集中式状态项", "x*x", " 项", 0),
                M("分布式邻居项", "x*8", " 项", 0),
                M("每秒更新量", "x*8/y", " 项/s"),
            ),
            "集中掌握全网状态随规模呈平方级膨胀，局部邻居状态更易扩展，但只能获得局部视图。",
        ),
        L(
            "latency-chain",
            "感知到决策的时延链",
            "采样、逐跳转发与端到端反应时间",
            A("平均跳数", 1, 20, 6, 1, " 跳"),
            A("单跳时延", 2, 100, 18, 2, " ms"),
            (
                M("网络时延", "x*y", " ms"),
                M("含采样等待", "x*y+250", " ms"),
                M("每秒可响应事件", "1000/(x*y+250)", " 次"),
            ),
            "端到端时延不仅来自无线转发，采样周期、排队、聚合和网关处理常占据更大比例。",
        ),
        L(
            "redundancy",
            "冗余部署与可靠性",
            "单节点可靠性、冗余数量与任务成功率",
            A("单节点成功率", 50, 99, 85, 1, "%"),
            A("同区冗余节点", 1, 8, 3, 1, " 个"),
            (
                M("至少一个成功", "100*(1-Math.pow(1-x/100,y))", "%"),
                M("全部成功", "100*Math.pow(x/100,y)", "%"),
                M("额外能耗系数", "y", "×"),
            ),
            "冗余能显著提高至少一次成功的概率，但如果所有节点同时工作，能耗和信道占用也按数量增长。",
        ),
    ],
    "第二章 传感器网络节点": [
        L(
            "sampling",
            "采样率与节点能耗",
            "采样频率、单次采样能量与日耗电",
            A("采样频率", 1, 100, 10, 1, " Hz"),
            A("单次采样能量", 1, 200, 35, 1, " μJ"),
            (
                M("采样功率", "x*y/1000", " mW"),
                M("每日能量", "x*y*86400/3600000", " Wh"),
                M("每日电量@3V", "x*y*86400/10800000", " Ah"),
            ),
            "提高采样率可捕获更快动态，却会同时增加传感器、ADC、处理和存储负担。",
        ),
        L(
            "radio-state",
            "无线电状态占比",
            "发送占空比、接收占空比与平均电流",
            A("发送占空比", 0, 20, 2, 0.5, "%"),
            A("接收占空比", 0, 50, 8, 1, "%"),
            (
                M("平均电流", "17*x/100+19*y/100+0.02*(1-x/100-y/100)", " mA", 2),
                M("2400mAh寿命", "2400/(17*x/100+19*y/100+0.02*(1-x/100-y/100))/24", " 天"),
                M("休眠比例", "100-x-y", "%"),
            ),
            "接收与空闲侦听往往不比发送省电；低功耗设计必须同时压缩发送和接收活动时间。",
        ),
        L(
            "adc",
            "ADC 位数与数据规模",
            "量化位数、采样率与原始数据量",
            A("ADC 位数", 8, 24, 12, 1, " bit"),
            A("采样率", 1, 2000, 100, 10, " Hz"),
            (
                M("量化级数", "Math.pow(2,x)", " 级", 0),
                M("单通道数据率", "x*y/1000", " kb/s", 2),
                M("每日原始数据", "x*y*86400/8/1024/1024", " MiB"),
            ),
            "分辨率提升降低量化步长，却线性增加传输与存储量；传感器本身的噪声底决定有效位数。",
        ),
        L(
            "cpu-duty",
            "处理器频率与任务占空",
            "计算频率、活动时间与动态能量",
            A("CPU 频率", 1, 80, 16, 1, " MHz"),
            A("每周期活动时间", 1, 100, 20, 1, " ms"),
            (
                M("计算占空比", "Math.min(100,y/10)", "%"),
                M("相对动态功耗", "x*x*y/1000", " 单位"),
                M("每秒空闲时间", "Math.max(0,1000-y)", " ms"),
            ),
            "频率提高可缩短任务完成时间，但电压常需随频率上升，动态功耗可能呈超线性增长。",
        ),
        L(
            "harvest",
            "能量采集收支平衡",
            "节点日耗能、平均采集功率与能量中性",
            A("节点平均功耗", 0.1, 50, 8, 0.1, " mW"),
            A("平均采集功率", 0, 60, 12, 0.5, " mW"),
            (
                M("每日净能量", "(y-x)*24/1000", " Wh", 3),
                M("能量覆盖率", "100*y/Math.max(x,0.01)", "%"),
                M("10Wh储能变化期", "10/Math.max(Math.abs(y-x)*24/1000,0.001)", " 天"),
            ),
            "能量采集系统追求长期收支平衡；均值足够仍不代表阴天、遮挡或振动中断时不会断电。",
        ),
    ],
    "第三章 操作系统": [
        L(
            "event-queue",
            "事件队列等待",
            "事件到达率、服务率与排队时延",
            A("事件到达率", 1, 90, 35, 1, " 次/s"),
            A("处理能力", 10, 100, 60, 1, " 次/s"),
            (
                M("利用率", "100*x/y", "%"),
                M("近似等待时间", "x<y?1000/(y-x):9999", " ms"),
                M("稳定裕量", "y-x", " 次/s"),
            ),
            "当到达率逼近处理率，排队时延会陡增；事件驱动并不自动保证实时性。",
        ),
        L(
            "stack",
            "任务栈内存预算",
            "任务数、单任务栈与 RAM 压力",
            A("并发任务数", 1, 32, 8, 1, " 个"),
            A("单任务栈", 128, 4096, 512, 128, " B"),
            (
                M("栈总量", "x*y/1024", " KiB"),
                M("占64KiB比例", "100*x*y/65536", "%"),
                M("剩余RAM", "64-x*y/1024", " KiB"),
            ),
            "线程模型直观但每个任务都要预留栈；事件驱动常用共享栈换取更低内存占用。",
        ),
        L(
            "timer",
            "定时器粒度与唤醒",
            "定时精度、任务数量与中断开销",
            A("时钟滴答", 1, 100, 10, 1, " ms"),
            A("周期任务数", 1, 50, 12, 1, " 个"),
            (
                M("每秒滴答中断", "1000/x", " 次"),
                M("调度检查", "1000*y/x", " 次/s"),
                M("最大量化误差", "x", " ms"),
            ),
            "更细的滴答提高定时精度，却带来更频繁的中断与调度检查；无滴答设计可减少空闲唤醒。",
        ),
        L(
            "mutex",
            "临界区阻塞上界",
            "低优先级临界区、中优先级干扰与高优先级阻塞",
            A("低优先级临界区", 1, 100, 20, 1, " ms"),
            A("中优先级干扰", 0, 200, 80, 5, " ms"),
            (
                M("无协议阻塞", "x+y", " ms"),
                M("优先级继承阻塞", "x", " ms"),
                M("减少比例", "100*y/Math.max(x+y,1)", "%"),
            ),
            "优先级继承把高优先级任务的额外等待限制在相关临界区，而不是任由无关中优先级任务延长反转。",
        ),
        L(
            "context",
            "上下文切换代价",
            "切换频率、切换耗时与 CPU 占用",
            A("每秒切换次数", 10, 5000, 500, 10, " 次"),
            A("单次切换耗时", 1, 200, 20, 1, " μs"),
            (
                M("切换CPU占比", "x*y/10000", "%"),
                M("每秒切换耗时", "x*y/1000", " ms"),
                M("有效CPU时间", "1000-x*y/1000", " ms"),
            ),
            "任务切得越细，响应可能越快，但保存恢复上下文和缓存扰动会蚕食有效计算时间。",
        ),
    ],
    "第四章 无线传感网络体系结构": [
        L(
            "cluster-size",
            "簇规模与汇聚开销",
            "簇数、成员数与簇头负载",
            A("节点总数", 20, 1000, 200, 20, " 个"),
            A("簇数量", 1, 50, 10, 1, " 个"),
            (
                M("平均簇规模", "x/y", " 节点"),
                M("簇内上报", "x-y", " 包/轮", 0),
                M("簇头转发", "y", " 包/轮", 0),
            ),
            "簇太少会让簇头过载并拉长簇内距离，簇太多又削弱聚合收益并增加簇头竞争。",
        ),
        L(
            "gateway",
            "网关瓶颈",
            "汇聚流量、网关处理能力与积压",
            A("节点上报总率", 10, 5000, 800, 10, " 包/s"),
            A("网关处理能力", 100, 6000, 1200, 50, " 包/s"),
            (
                M("网关利用率", "100*x/y", "%"),
                M("每秒积压", "Math.max(0,x-y)", " 包"),
                M("10秒队列", "10*Math.max(0,x-y)", " 包"),
            ),
            "多对一流量会把压力集中到汇聚节点附近；体系结构必须为热点链路和网关预留容量。",
        ),
        L(
            "cross-layer",
            "跨层节能收益",
            "链路重传率、路由绕行与总发送次数",
            A("单跳丢包率", 0, 50, 12, 1, "%"),
            A("路径跳数", 1, 20, 6, 1, " 跳"),
            (
                M("期望发送次数", "y/(1-x/100)", " 次"),
                M("端到端一次成功", "100*Math.pow(1-x/100,y)", "%"),
                M("跨层减少重传", "0.2*y*x/(100-x)", " 次"),
            ),
            "链路质量、路由代价和 MAC 重传相互耦合；跨层共享信息可降低重复试错，但也增加模块依赖。",
        ),
        L(
            "hierarchy",
            "层次化状态压缩",
            "节点数、层级分组与状态条目",
            A("节点数", 50, 5000, 500, 50, " 个"),
            A("每组节点数", 5, 100, 20, 5, " 个"),
            (
                M("组数量", "Math.ceil(x/y)", " 组", 0),
                M("平面状态", "x*x", " 项", 0),
                M("层次状态", "x*y+Math.pow(Math.ceil(x/y),2)", " 项", 0),
            ),
            "层次化用局部详细、全局摘要压缩状态规模，代价是聚合节点负担和路径不一定最短。",
        ),
        L(
            "rotation",
            "簇头轮换公平性",
            "簇头比例、轮次与平均当选次数",
            A("节点数", 20, 500, 100, 10, " 个"),
            A("簇头比例", 1, 30, 8, 1, "%"),
            (
                M("每轮簇头", "x*y/100", " 个"),
                M("完整轮换周期", "100/y", " 轮"),
                M("20轮每节点当选", "20*y/100", " 次"),
            ),
            "随机轮换只有在足够长时间和均匀能耗假设下才趋于公平；异构能量节点应采用加权策略。",
        ),
    ],
    "第五章 无线通信基础": [
        L(
            "path-loss",
            "对数距离路径损耗",
            "距离、路径损耗指数与附加衰减",
            A("距离", 1, 500, 100, 5, " m"),
            A("路径损耗指数", 2, 5, 3, 0.1, ""),
            (
                M("相对路径损耗", "10*y*Math.log10(x)", " dB"),
                M("距离加倍增量", "10*y*Math.log10(2)", " dB"),
                M("相对接收功率", "100/Math.pow(x,y)", "%", 5),
            ),
            "路径损耗指数由环境决定；同样的距离变化，在室内遮挡或城市峡谷中影响更大。",
        ),
        L(
            "snr",
            "信噪比与误码趋势",
            "接收信号、噪声底与误码概率",
            A("接收功率", -110, -40, -85, 1, " dBm"),
            A("噪声底", -120, -70, -100, 1, " dBm"),
            (
                M("SNR", "x-y", " dB"),
                M("线性SNR", "Math.pow(10,(x-y)/10)", "×", 2),
                M("BPSK误码近似", "50*Math.exp(-Math.pow(10,(x-y)/10))", "%", 4),
            ),
            "SNR 是接收功率与噪声功率之比；误码率还取决于调制、编码和接收机实现。",
        ),
        L(
            "sinr",
            "干扰与 SINR",
            "信号功率、干扰功率与解调裕量",
            A("期望信号", -100, -30, -75, 1, " dBm"),
            A("干扰加噪声", -110, -40, -88, 1, " dBm"),
            (
                M("SINR", "x-y", " dB"),
                M("线性比", "Math.pow(10,(x-y)/10)", "×", 2),
                M("距6dB门限裕量", "x-y-6", " dB"),
            ),
            "仅看 RSSI 可能误判链路；强信号若伴随更强干扰，实际可解调性仍然很差。",
        ),
        L(
            "coherence",
            "多径相干带宽",
            "时延扩展、信号带宽与平坦衰落条件",
            A("均方根时延扩展", 0.01, 10, 0.5, 0.01, " μs"),
            A("信号带宽", 0.01, 20, 2, 0.01, " MHz"),
            (
                M("相干带宽近似", "1/(5*x)", " MHz", 3),
                M("带宽比", "y/(1/(5*x))", "×", 2),
                M("频率选择性指数", "100*Math.min(1,y*5*x)", "%"),
            ),
            "当信号带宽明显小于相干带宽时可近似平坦衰落；反之不同频率分量受到不同衰减。",
        ),
        L(
            "shadow",
            "阴影衰落与可靠裕量",
            "阴影衰落标准差、链路余量与越限风险",
            A("阴影衰落标准差", 0.5, 12, 4, 0.5, " dB"),
            A("链路衰落余量", 0, 30, 10, 1, " dB"),
            (
                M("余量/标准差", "y/x", "σ", 2),
                M("一σ波动范围", "2*x", " dB"),
                M("近似越限指数", "100*Math.exp(-0.5*Math.pow(y/x,2))", "%", 3),
            ),
            "阴影衰落通常用对数正态模型描述；预留的衰落余量相对标准差越大，随机遮挡导致越限的风险越低。",
        ),
    ],
    "第六章 拓扑控制技术": [
        L(
            "degree",
            "通信半径与节点度",
            "密度、通信半径和邻居度",
            A("区域节点密度", 10, 200, 60, 5, " 个/km²"),
            A("通信半径", 30, 500, 160, 10, " m"),
            (
                M("平均节点度", "Math.PI*y*y*x/1e6", ""),
                M("无邻居概率", "100*Math.exp(-Math.PI*y*y*x/1e6)", "%"),
                M("边数近似", "0.5*100*Math.PI*y*y*x/1e6", " 条/百节点"),
            ),
            "节点度过低容易分割网络，过高则增加竞争和干扰；拓扑控制寻求可连通的稀疏图。",
        ),
        L(
            "power",
            "发射功率控制",
            "功率档位、路径损耗指数与可达距离",
            A("相对发射功率", 1, 100, 25, 1, "%"),
            A("路径损耗指数", 2, 5, 3, 0.1, ""),
            (
                M("相对通信半径", "100*Math.pow(x/100,1/y)", "%"),
                M("相对能耗", "x", "%"),
                M("覆盖面积比例", "100*Math.pow(x/100,2/y)", "%"),
            ),
            "功率与距离不是线性关系；降低功率能节能降干扰，但覆盖面积和候选邻居也会缩小。",
        ),
        L(
            "backbone",
            "连通支配集骨干",
            "骨干节点比例、转发负载与休眠收益",
            A("节点总数", 50, 1000, 300, 10, " 个"),
            A("骨干节点比例", 5, 80, 25, 5, "%"),
            (
                M("骨干节点", "x*y/100", " 个", 0),
                M("可休眠节点", "x*(1-y/100)", " 个", 0),
                M("骨干负载系数", "100/y", "×", 2),
            ),
            "稀疏骨干可让更多节点休眠，但剩余骨干承担更高转发负载，需轮换或按能量加权。",
        ),
        L(
            "hysteresis",
            "拓扑切换滞回",
            "链路波动、切换门限与重配置频率",
            A("链路质量波动", 1, 30, 10, 1, " dB"),
            A("滞回宽度", 0, 20, 5, 1, " dB"),
            (
                M("切换敏感度", "100*x/(x+y+0.1)", "%"),
                M("抖动抑制", "100*y/(x+y+0.1)", "%"),
                M("响应延迟指数", "y/x", "×", 2),
            ),
            "滞回可避免链路在门限附近反复加入和删除，但过大的滞回会延迟对真实拓扑变化的响应。",
        ),
        L(
            "coverage-connect",
            "覆盖与连通双约束",
            "感知半径、通信半径与安全比例",
            A("感知半径", 10, 200, 60, 5, " m"),
            A("通信半径", 10, 400, 150, 5, " m"),
            (
                M("通信/感知比", "y/x", "×", 2),
                M("覆盖圆面积", "Math.PI*x*x/1000", " 千m²"),
                M("连通裕量", "y-2*x", " m"),
            ),
            "在某些规则部署中，通信半径不小于两倍感知半径可帮助覆盖推导连通；随机部署仍需图分析。",
        ),
    ],
    "第七章 MAC协议": [
        L(
            "duty",
            "占空比与等待时延",
            "唤醒占空比、周期与平均接入等待",
            A("无线电占空比", 1, 100, 10, 1, "%"),
            A("唤醒周期", 10, 2000, 500, 10, " ms"),
            (
                M("平均等待", "y*(1-x/100)/2", " ms"),
                M("相对待机能耗", "x", "%"),
                M("每秒唤醒次数", "1000/y", " 次"),
            ),
            "更低占空比节省空闲侦听，却延长异步发送者等待接收端醒来的时间。",
        ),
        L(
            "csma",
            "CSMA 竞争碰撞",
            "同时竞争节点数、竞争窗口与碰撞风险",
            A("竞争节点数", 2, 100, 20, 1, " 个"),
            A("退避窗口", 4, 256, 32, 4, " 槽"),
            (
                M("同槽冲突指数", "100*(1-Math.pow(1-1/y,x-1))", "%"),
                M("平均退避", "(y-1)/2", " 槽"),
                M("窗口/节点比", "y/x", "×", 2),
            ),
            "扩大竞争窗口可降低同槽选择概率，却增加接入等待；突发事件时固定窗口往往不够。",
        ),
        L(
            "tdma",
            "TDMA 时隙利用",
            "活跃节点、时隙数与帧利用率",
            A("活跃节点", 1, 100, 30, 1, " 个"),
            A("每帧时隙", 4, 128, 40, 4, " 个"),
            (
                M("时隙利用率", "100*Math.min(x,y)/y", "%"),
                M("溢出节点", "Math.max(0,x-y)", " 个"),
                M("空闲时隙", "Math.max(0,y-x)", " 个"),
            ),
            "TDMA 在稳定周期流量下高效且确定；轻载时空闲时隙浪费，突发节点超过容量时则需要重排。",
        ),
        L(
            "preamble",
            "低功耗侦听前导码",
            "侦听周期、前导码长度与发送开销",
            A("信道检查周期", 10, 1000, 250, 10, " ms"),
            A("前导码字节率", 1, 50, 8, 1, " B/ms"),
            (
                M("最长前导码", "x*y", " B"),
                M("平均前导码", "x*y/2", " B"),
                M("每秒检查次数", "1000/x", " 次"),
            ),
            "长前导码确保覆盖接收端睡眠窗口，但把接收端节省的能量部分转移给发送端和信道占用。",
        ),
        L(
            "hidden",
            "隐藏终端暴露风险",
            "隐藏发送者数量、发送概率与碰撞概率",
            A("隐藏发送者", 1, 30, 5, 1, " 个"),
            A("单节点发送概率", 1, 80, 15, 1, "%"),
            (
                M("至少一方冲突", "100*(1-Math.pow(1-y/100,x))", "%"),
                M("无冲突概率", "100*Math.pow(1-y/100,x)", "%"),
                M("期望同时发送", "x*y/100", " 个", 2),
            ),
            "载波侦听只看到本地信道；彼此不可听见的发送者仍可能在共同接收端碰撞。",
        ),
    ],
    "第八章 路由技术": [
        L(
            "etx",
            "ETX 路径代价",
            "正向成功率、反向确认率与期望传输次数",
            A("数据帧成功率", 10, 100, 85, 1, "%"),
            A("确认帧成功率", 10, 100, 90, 1, "%"),
            (
                M("ETX", "1/((x/100)*(y/100))", " 次", 2),
                M("一次双向成功", "x*y/100", "%"),
                M("额外重传", "1/((x/100)*(y/100))-1", " 次", 2),
            ),
            "ETX 同时考虑数据与确认方向；单看 RSSI 或跳数会忽略非对称链路和重传成本。",
        ),
        L(
            "hop-energy",
            "跳数与能耗路径",
            "路径跳数、单跳固定开销与总能量",
            A("路径跳数", 1, 30, 6, 1, " 跳"),
            A("每跳能耗", 0.01, 5, 0.4, 0.01, " mJ"),
            (
                M("总能耗", "x*y", " mJ"),
                M("收发操作数", "2*x-1", " 次", 0),
                M("每1000包能量", "x*y", " J"),
            ),
            "更多短跳可能降低功放能耗，却增加电子电路、接收和排队开销；路由度量应估算完整路径成本。",
        ),
        L(
            "leach",
            "簇头比例与轮次",
            "簇头比例、节点数与簇内规模",
            A("簇头比例", 1, 30, 5, 1, "%"),
            A("节点总数", 20, 1000, 200, 20, " 个"),
            (
                M("每轮簇头", "x*y/100", " 个"),
                M("平均簇规模", "100/x", " 节点"),
                M("理论轮换周期", "100/x", " 轮"),
            ),
            "簇头比例决定簇内距离与汇聚数量；固定概率只能给出平均值，实际还受几何和剩余能量影响。",
        ),
        L(
            "greedy",
            "地理贪心与空洞",
            "候选邻居数、有效前进比例与停滞概率",
            A("候选邻居数", 1, 30, 8, 1, " 个"),
            A("更近邻居比例", 0, 100, 55, 5, "%"),
            (
                M("可继续概率", "100*(1-Math.pow(1-y/100,x))", "%"),
                M("局部最小概率", "100*Math.pow(1-y/100,x)", "%"),
                M("有效候选数", "x*y/100", " 个", 2),
            ),
            "贪心只利用局部几何信息；空洞边界会产生局部最小，需要周界转发等恢复机制。",
        ),
        L(
            "aggregate-route",
            "路由内聚合收益",
            "源数量、聚合比例与上游包数",
            A("下游源节点", 2, 500, 80, 2, " 个"),
            A("聚合保留比例", 5, 100, 30, 5, "%"),
            (
                M("未聚合包数", "x", " 包"),
                M("聚合后包数", "x*y/100", " 包"),
                M("上游节省", "x*(1-y/100)", " 包"),
            ),
            "聚合越早，上游多跳链路节省越大；但等待聚合会增加时延并集中故障风险。",
        ),
    ],
    "第九章 传输控制技术": [
        L(
            "queue",
            "队列稳定性",
            "到达率、服务率与积压趋势",
            A("数据到达率", 1, 500, 180, 5, " 包/s"),
            A("链路服务率", 10, 600, 240, 5, " 包/s"),
            (
                M("利用率", "100*x/y", "%"),
                M("每秒净积压", "Math.max(0,x-y)", " 包"),
                M("稳定裕量", "y-x", " 包/s"),
            ),
            "长期稳定需要平均到达率低于服务率；短期突发仍需要队列吸收和回压协调。",
        ),
        L(
            "retransmit",
            "可靠性与重传代价",
            "单次成功率、最大尝试次数与最终交付率",
            A("单次成功率", 10, 99, 75, 1, "%"),
            A("最大尝试次数", 1, 10, 3, 1, " 次"),
            (
                M("最终交付率", "100*(1-Math.pow(1-x/100,y))", "%"),
                M("期望尝试上界", "(1-Math.pow(1-x/100,y))/(x/100)", " 次", 2),
                M("最坏时延系数", "y", "×"),
            ),
            "增加重传提高交付概率，却拉长尾时延并消耗能量；重要数据可采用更高重试上限。",
        ),
        L(
            "rate",
            "源端速率控制",
            "源数量、单源速率与瓶颈负载",
            A("并发源数量", 1, 100, 20, 1, " 个"),
            A("单源发送率", 1, 100, 15, 1, " 包/s"),
            (
                M("汇聚到达率", "x*y", " 包/s"),
                M("占500包/s容量", "100*x*y/500", "%"),
                M("公平限速", "500/x", " 包/s"),
            ),
            "多源汇聚时，每个源独立看来都不高，却可能共同压垮汇聚路径；需要端到端或逐跳反馈。",
        ),
        L(
            "backpressure",
            "逐跳回压传播",
            "拥塞跳数、反馈延迟与额外积压",
            A("拥塞点距离", 1, 20, 6, 1, " 跳"),
            A("每跳反馈延迟", 1, 100, 20, 1, " ms"),
            (
                M("反馈总延迟", "x*y", " ms"),
                M("100包/s新增积压", "x*y/10", " 包"),
                M("控制报文往返", "2*x", " 跳"),
            ),
            "回压反应速度取决于反馈传播；拥塞点越远，源在收到信号前继续注入的数据越多。",
        ),
        L(
            "priority",
            "优先级与公平性",
            "高优先级份额、总容量与普通业务余量",
            A("高优先级保留", 0, 100, 35, 5, "%"),
            A("链路容量", 10, 1000, 300, 10, " 包/s"),
            (
                M("高优先级额度", "x*y/100", " 包/s"),
                M("普通业务额度", "(100-x)*y/100", " 包/s"),
                M("优先级比", "x/Math.max(100-x,1)", "×", 2),
            ),
            "任务关键数据需要优先保障，但完全抢占会让普通监测长期饥饿；应设置额度和老化机制。",
        ),
    ],
    "第十章 实用化组网标准协议": [
        L(
            "superframe",
            "802.15.4 超帧占空",
            "Beacon Order、Superframe Order 与活跃比例",
            A("Beacon Order", 0, 14, 6, 1, ""),
            A("Superframe Order", 0, 14, 4, 1, ""),
            (
                M("占空比", "100*Math.pow(2,Math.min(y,x)-x)", "%"),
                M("相对信标间隔", "Math.pow(2,x)", "×", 0),
                M("相对活跃期", "Math.pow(2,Math.min(y,x))", "×", 0),
            ),
            "SO 不应大于 BO；两者差值决定非活跃期和省电幅度，也影响等待下一超帧的时延。",
        ),
        L(
            "fragment",
            "6LoWPAN 分片",
            "IPv6 数据报大小、链路帧净荷与分片数",
            A("IPv6 数据报", 40, 1280, 500, 20, " B"),
            A("每帧可用净荷", 20, 100, 70, 5, " B"),
            (
                M("需要分片", "Math.ceil(x/y)", " 片", 0),
                M("分片头开销", "Math.ceil(x/y)*5", " B", 0),
                M("全片成功@95%", "100*Math.pow(0.95,Math.ceil(x/y))", "%"),
            ),
            "低功耗链路帧很小；数据报越大，分片数量和整包失败概率越高，应优先压缩头部和控制应用载荷。",
        ),
        L(
            "ble",
            "BLE 连接间隔",
            "连接间隔、每事件耗时与无线电占空",
            A("连接间隔", 7.5, 4000, 100, 2.5, " ms"),
            A("单次连接事件", 0.5, 20, 3, 0.5, " ms"),
            (
                M("无线电占空比", "100*y/x", "%"),
                M("每秒连接事件", "1000/x", " 次"),
                M("平均等待上界", "x", " ms"),
            ),
            "长连接间隔通常更省电，却增加数据等待；事件时长还受包数量、重传和 PHY 速率影响。",
        ),
        L(
            "channel-hop",
            "工业跳频可靠性",
            "可用信道数、单信道受扰率与全路径可用性",
            A("跳频信道数", 1, 32, 16, 1, " 个"),
            A("单信道受扰概率", 0, 90, 25, 5, "%"),
            (
                M("至少一个干净", "100*(1-Math.pow(y/100,x))", "%"),
                M("平均干净信道", "x*(1-y/100)", " 个"),
                M("全被干扰", "100*Math.pow(y/100,x)", "%", 4),
            ),
            "信道跳变把窄带持续干扰转化为部分时隙损失；信道并非独立时，收益会低于该理想估计。",
        ),
        L(
            "zigbee-tree",
            "ZigBee 树路由深度",
            "树深度、每级分支与潜在节点规模",
            A("最大深度", 1, 10, 5, 1, " 层"),
            A("每路由器子节点", 1, 10, 4, 1, " 个"),
            (
                M("满树节点数", "y===1?x+1:(Math.pow(y,x+1)-1)/(y-1)", " 个", 0),
                M("最坏路径跳数", "2*x", " 跳", 0),
                M("单点祖先数", "x", " 个", 0),
            ),
            "树结构地址与转发简单，但深层路径可能绕行，祖先节点故障会影响整个子树。",
        ),
    ],
    "第十一章 感知覆盖": [
        L(
            "disk",
            "圆盘感知覆盖率",
            "节点数量、感知半径与理想覆盖面积",
            A("节点数量", 1, 300, 60, 2, " 个"),
            A("感知半径", 5, 100, 25, 1, " m"),
            (
                M("圆面积总和", "x*Math.PI*y*y/10000", " 公顷"),
                M("1公顷理想覆盖", "100*Math.min(1,x*Math.PI*y*y/10000)", "%"),
                M("平均覆盖重数", "x*Math.PI*y*y/10000", "×", 2),
            ),
            "圆面积相加忽略重叠与边界，只给出乐观上界；实际覆盖必须结合节点几何位置。",
        ),
        L(
            "poisson",
            "随机部署覆盖概率",
            "节点密度、感知半径与点覆盖概率",
            A("节点密度", 1, 300, 80, 5, " 个/km²"),
            A("感知半径", 10, 150, 50, 5, " m"),
            (
                M("平均覆盖节点", "Math.PI*y*y*x/1e6", " 个", 2),
                M("至少一重覆盖", "100*(1-Math.exp(-Math.PI*y*y*x/1e6))", "%"),
                M("覆盖空洞概率", "100*Math.exp(-Math.PI*y*y*x/1e6)", "%"),
            ),
            "泊松模型把节点视为独立随机点，可估计任一点被覆盖的概率，但不能描述连片空洞形状。",
        ),
        L(
            "kcover",
            "k-覆盖概率",
            "平均覆盖重数、目标 k 值与可靠性",
            A("平均覆盖重数", 0.1, 10, 2.5, 0.1, " λ"),
            A("目标 k 值", 1, 6, 2, 1, ""),
            (
                M(
                    "至少k覆盖",
                    "100*(1-Array.from({length:Math.floor(y)},(_,i)=>Math.pow(x,i)*Math.exp(-x)/factorial(i)).reduce((a,b)=>a+b,0))",
                    "%",
                ),
                M("期望冗余", "x", " 个"),
                M("k/均值", "y/x", "×", 2),
            ),
            "k-覆盖用冗余抵抗节点失效；当 k 接近或超过平均覆盖重数时，满足概率会快速下降。",
        ),
        L(
            "grid",
            "连续区域的网格化评估",
            "网格边长、区域尺度与覆盖计算量",
            A("正方形区域边长", 100, 5000, 1000, 100, " m"),
            A("网格边长", 2, 100, 20, 2, " m"),
            (
                M("网格点数量", "Math.pow(Math.ceil(x/y)+1,2)", " 点", 0),
                M("单元格数量", "Math.pow(Math.ceil(x/y),2)", " 格", 0),
                M("边界量化尺度", "Math.SQRT2*y", " m", 1),
            ),
            "网格越细，连续覆盖越接近可计算的离散判定，但网格点数量按边长比的平方增长。",
        ),
        L(
            "failure",
            "节点失效后的覆盖保持",
            "初始覆盖重数、节点存活率与剩余覆盖",
            A("初始平均覆盖重数", 1, 10, 3, 0.5, "×"),
            A("节点存活率", 10, 100, 80, 5, "%"),
            (
                M("剩余平均重数", "x*y/100", "×", 2),
                M("至少一重近似", "100*(1-Math.exp(-x*y/100))", "%"),
                M("冗余损失", "x*(1-y/100)", "×", 2),
            ),
            "冗余部署能延缓覆盖退化；失效若具有空间相关性，独立失效近似会过于乐观。",
        ),
    ],
    "第十二章 时间同步与节点定位": [
        L(
            "drift",
            "频率偏斜误差",
            "相对频率偏斜、重同步周期与相位误差",
            A("相对偏斜", 1, 100, 40, 1, " ppm"),
            A("重同步周期", 1, 600, 60, 1, " s"),
            (
                M("最大漂移", "x*y/1000", " ms"),
                M("每小时同步次数", "3600/y", " 次"),
                M("10分钟无同步误差", "x*600/1000", " ms"),
            ),
            "ppm 表示每百万单位的频率误差；延长重同步周期可省报文，却让相位误差线性积累。",
        ),
        L(
            "twoway",
            "双向同步延迟不对称",
            "往返时延、路径不对称与偏移估计误差",
            A("往返时延", 1, 200, 40, 1, " ms"),
            A("上下行不对称", -100, 100, 20, 1, "%"),
            (
                M("单向均值", "x/2", " ms"),
                M("偏移估计误差", "x*y/200", " ms"),
                M("估计一程延迟", "x*(1+y/100)/2", " ms"),
            ),
            "双向交换可以消除未知绝对发送时刻，但通常假设上下行近似对称；不对称直接映射为偏移误差。",
        ),
        L(
            "rbs",
            "参考广播接收误差",
            "接收时间戳抖动、样本数与平均误差",
            A("单次时间戳抖动", 0.1, 20, 5, 0.1, " ms"),
            A("广播样本数", 1, 100, 10, 1, " 次"),
            (
                M("均值标准误差", "x/Math.sqrt(y)", " ms", 3),
                M("样本开销", "y", " 帧", 0),
                M("相对精度改善", "100*(1-1/Math.sqrt(y))", "%"),
            ),
            "参考广播让多个接收者比较同一帧的到达时间，削弱发送侧不确定性；独立噪声可由多样本平均降低。",
        ),
        L(
            "rssi",
            "RSSI 测距误差",
            "阴影衰落标准差、路径损耗指数与距离倍率误差",
            A("RSSI 标准差", 0.5, 12, 4, 0.5, " dB"),
            A("路径损耗指数", 1.5, 5, 3, 0.1, ""),
            (
                M("一σ距离倍率", "Math.pow(10,x/(10*y))", "×", 3),
                M("100m一σ误差", "100*(Math.pow(10,x/(10*y))-1)", " m"),
                M("对数斜率", "10*y", " dB/十倍距"),
            ),
            "RSSI 测距把功率波动映射为指数型距离误差；环境标定和多点滤波很关键。",
        ),
        L(
            "gdop",
            "锚点几何与定位精度",
            "测距误差、锚点夹角与几何放大",
            A("单次测距误差", 0.1, 20, 3, 0.1, " m"),
            A("有效夹角", 10, 170, 60, 5, "°"),
            (
                M("几何放大因子", "1/Math.max(Math.sin(y*Math.PI/180),0.05)", "×", 2),
                M("位置误差近似", "x/Math.max(Math.sin(y*Math.PI/180),0.05)", " m"),
                M("几何质量", "100*Math.sin(y*Math.PI/180)", "%"),
            ),
            "锚点方向越分散，距离圆交会越稳定；锚点近共线时，小测距误差会被显著放大。",
        ),
    ],
}


# Every added lab is anchored to one exact theory subsection.  The migration
# splits multi-subsection section blocks without rewriting their prose, then
# inserts the widget immediately after the matching subsection.
PLACEMENTS: dict[str, dict[str, str]] = {
    "第一章 绪论": {
        "density": "从节点到网络：自组织与多跳通信",
        "aggregation": "以数据为中心与能量受限",
        "scale": "动态拓扑与大规模冗余部署",
        "latency-chain": "全书主线：节点—网络—协议—感知应用",
        "redundancy": "典型应用场景概览",
    },
    "第二章 传感器网络节点": {
        "sampling": "传感单元：从物理量到电信号",
        "radio-state": "通信单元：收发链路与协议开销",
        "adc": "信号调理与模数转换",
        "cpu-duty": "动态电压频率调节：计算单元的能耗优化",
        "harvest": "能量收集：从环境到节点的能量补给",
    },
    "第三章 操作系统": {
        "event-queue": "事件驱动与线程模型：两种基本取舍",
        "stack": "任务与事件抽象：从并发模型到编程接口",
        "timer": "非抢占、协作、抢占与时间片轮转",
        "mutex": "同步与通信原语：轻量级实现与约束",
        "context": "实时性分析：从响应时间到可调度性",
    },
    "第四章 无线传感网络体系结构": {
        "cluster-size": "簇头与簇成员的角色分工",
        "gateway": "从节点到网络：组织问题的提出",
        "cross-layer": "跨层设计的典型机制与实例",
        "hierarchy": "分层结构的运行机制",
        "rotation": "簇头轮换策略与能量均衡",
    },
    "第五章 无线通信基础": {
        "path-loss": "大尺度路径损耗：距离与频率的衰减规律",
        "snr": "无线信道的三大核心损伤",
        "sinr": "干扰：共享频谱的代价",
        "coherence": "小尺度多径衰落：时变与频选特性",
        "shadow": "阴影衰落：对数正态分布的慢变波动",
    },
    "第六章 拓扑控制技术": {
        "degree": "通信范围如何塑造网络拓扑",
        "power": "发射功率与通信半径的映射关系",
        "backbone": "典型功率控制算法",
        "hysteresis": "功率控制对网络连通性的影响",
        "coverage-connect": "约束二：保障覆盖质量",
    },
    "第七章 MAC协议": {
        "duty": "能量效率：无线节点的生命线",
        "csma": "冲突避免：从随机竞争到有序接入",
        "tdma": "公平性：节点间的机会均等",
        "preamble": "MAC协议的角色与基本问题",
        "hidden": "设计目标之间的权衡",
    },
    "第八章 路由技术": {
        "etx": "平面路由：洪泛与协商的朴素路线",
        "hop-energy": "传统 IP 路由为何在传感器网络中失效",
        "leach": "层次路由：分簇与数据聚合的协同",
        "greedy": "地理位置路由：利用位置信息做贪婪转发",
        "aggregate-route": "以数据为中心：从地址寻址到数据寻址",
    },
    "第九章 传输控制技术": {
        "queue": "拥塞控制为何是传输控制的下位子话题",
        "retransmit": "高误码率与链路不对称的挑战",
        "rate": "ESRT：可靠性与拥塞协同",
        "backpressure": "CODA：拥塞检测与开环/闭环缓解",
        "priority": "从 TCP 到 WSN：为何不能直接照搬",
    },
    "第十章 实用化组网标准协议": {
        "superframe": "超帧结构与 GTS 保障时隙",
        "fragment": "6LoWPAN 适配层：头部压缩与分片重组",
        "ble": "BLE 与 Bluetooth Mesh：低功耗广播与中继泛洪",
        "channel-hop": "WirelessHART：TDMA、跳频与网状路由",
        "zigbee-tree": "ZigBee 网络层：树路由与 AODV 类网状路由",
    },
    "第十一章 感知覆盖": {
        "disk": "感知圆盘模型与布尔感知",
        "poisson": "概率感知模型与覆盖度定义",
        "kcover": "k-覆盖的判定与冗余代价",
        "grid": "从连续区域到可计算量",
        "failure": "网格与随机部署策略",
    },
    "第十二章 时间同步与节点定位": {
        "drift": "时钟漂移的物理来源",
        "twoway": "NTP：分层往返估计与时钟过滤",
        "rbs": "传感器网络同步协议：TPSN、RBS 与 FTSP",
        "rssi": "基于测距的定位方法",
        "gdop": "锚节点部署与连通度影响",
    },
}


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def widget(lab: Lab) -> str:
    controls = f"""
<div class="control"><label>{lab.x.label}<span class="value" id="xOut"></span></label><input id="x" type="range" min="{_number(lab.x.minimum)}" max="{_number(lab.x.maximum)}" value="{_number(lab.x.value)}" step="{_number(lab.x.step)}"></div>
<div class="control"><label>{lab.y.label}<span class="value" id="yOut"></span></label><input id="y" type="range" min="{_number(lab.y.minimum)}" max="{_number(lab.y.maximum)}" value="{_number(lab.y.value)}" step="{_number(lab.y.step)}"></div>
<div class="buttons"><button data-preset="low">低负载</button><button data-preset="mid" class="on">典型</button><button data-preset="high">高负载</button></div>
"""
    cards = "".join(
        f'<div class="metric"><div class="k">{metric.label}</div><div class="v" id="m{index}"></div><div class="s">随参数实时更新</div></div>'
        for index, metric in enumerate(lab.metrics)
    )
    stage = f'<div class="metrics">{cards}</div><canvas id="curve" width="720" height="300" aria-label="参数变化曲线"></canvas><div class="note">{lab.note}</div>'
    expressions = ",".join(metric.expression for metric in lab.metrics)
    units = json.dumps([metric.unit for metric in lab.metrics], ensure_ascii=False)
    decimals = json.dumps([metric.decimals for metric in lab.metrics])
    script = f"""
const $=id=>document.getElementById(id), units={units}, decimals={decimals}, xEl=$('x'), yEl=$('y');
const factorial=n=>{{let r=1;for(let i=2;i<=n;i++)r*=i;return r}};
function calc(x,y){{return [{expressions}]}}
function fmt(v,i){{if(!Number.isFinite(v))return '—';return v.toFixed(decimals[i])+units[i]}}
function update(){{const xv=+xEl.value,yv=+yEl.value,vals=calc(xv,yv);$('xOut').textContent=xv+'{lab.x.unit}';$('yOut').textContent=yv+'{lab.y.unit}';vals.forEach((v,i)=>$('m'+i).textContent=fmt(v,i));
 const c=$('curve'),g=c.getContext('2d'),lo=+xEl.min,hi=+xEl.max,pts=[];for(let i=0;i<=80;i++){{let sample=lo+(hi-lo)*i/80;pts.push(calc(sample,yv)[0])}}let finite=pts.filter(Number.isFinite),mn=Math.min(...finite),mx=Math.max(...finite);if(mx===mn)mx=mn+1;g.clearRect(0,0,c.width,c.height);g.fillStyle='#fbfcfe';g.fillRect(0,0,c.width,c.height);g.strokeStyle='#dce3ee';for(let j=0;j<5;j++){{g.beginPath();g.moveTo(45,25+j*58);g.lineTo(700,25+j*58);g.stroke()}}g.strokeStyle='#2563eb';g.lineWidth=3;g.beginPath();pts.forEach((v,i)=>{{let px=45+i*655/80,py=257-(v-mn)/(mx-mn)*220;i?g.lineTo(px,py):g.moveTo(px,py)}});g.stroke();g.fillStyle='#667085';g.font='12px system-ui';g.fillText('{lab.metrics[0].label}',48,18);g.fillText('{lab.x.label}',610,288);
}}
['x','y'].forEach(id=>$(id).addEventListener('input',update));document.querySelectorAll('[data-preset]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('[data-preset]').forEach(button=>button.classList.remove('on'));b.classList.add('on');let r=b.dataset.preset==='low'?.2:b.dataset.preset==='high'?.8:.5;xEl.value=+xEl.min+(+xEl.max-+xEl.min)*r;yEl.value=+yEl.min+(+yEl.max-+yEl.min)*r;update()}}));update();
"""
    return document(lab.title, lab.focus, controls, stage, script)


def block_for(
    page: dict[str, Any], chapter: dict[str, Any], chapter_number: int, lab: Lab
) -> dict[str, Any]:
    prompt = build_interactive_prompt(
        language="zh",
        chapter_title=chapter["title"],
        chapter_summary=str(chapter.get("summary") or ""),
        objectives=[str(item) for item in chapter.get("learning_objectives") or []],
        focus=lab.focus,
        interaction="参数探索",
    )
    code = widget(lab)
    validate_widget(code)
    timestamp = datetime.now(timezone.utc).timestamp()
    return {
        "id": f"blk_wsnx_{chapter_number:02d}_{lab.slug}",
        "type": "interactive",
        "status": "ready",
        "title": lab.title,
        "params": {
            "chapter_title": chapter["title"],
            "chapter_summary": chapter.get("summary") or "",
            "objectives": chapter.get("learning_objectives") or [],
            "focus": lab.focus,
            "interaction": "参数探索",
        },
        "payload": {
            "render_type": "html",
            "code": {"language": "html", "content": code},
            "description": f"{lab.focus}的中文可操作理论探索组件。",
            "chart_type": "interactive_parameter_lab",
        },
        "source_anchors": [],
        "metadata": {
            "curated_by": "Codex",
            "curation_version": "wsn-theory-v2",
            "native_prompt": prompt.user_input,
            "native_history_context": prompt.history_context,
            "review_notes": "Native prompt recorded; deterministic reviewed implementation installed.",
        },
        "error": "",
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def split_section(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Split a section into independently placeable subsection blocks.

    The prose and source anchors are retained verbatim.  The section intro is
    shown only before the first subsection and the takeaway only after the
    last, preserving the original reading order without duplicate framing.
    """

    payload = block.get("payload") or {}
    subsections = payload.get("subsections")
    if not isinstance(subsections, list) or len(subsections) <= 1:
        return [block]

    source_id = str(block.get("id") or "section")
    fragments: list[dict[str, Any]] = []
    for index, subsection in enumerate(subsections):
        fragment = deepcopy(block)
        if index:
            fragment["id"] = f"{source_id}_wsnpart_{index + 1:02d}"
        fragment_payload = fragment.setdefault("payload", {})
        fragment_payload["intro"] = payload.get("intro", "") if index == 0 else ""
        fragment_payload["subsections"] = [deepcopy(subsection)]
        fragment_payload["key_takeaway"] = (
            payload.get("key_takeaway", "") if index == len(subsections) - 1 else ""
        )
        fragment_payload["focus"] = subsection.get("focus", "")
        fragment_payload["role"] = subsection.get("role", "core")
        params = fragment.setdefault("params", {})
        params["focus"] = subsection.get("focus", params.get("focus", ""))
        params["role"] = subsection.get("role", params.get("role", "core"))
        params["target_words"] = subsection.get("target_words", params.get("target_words", 0))
        metadata = fragment.setdefault("metadata", {})
        metadata.update(
            {
                "wsn_section_split": True,
                "wsn_source_section_id": source_id,
                "wsn_section_part": index + 1,
                "wsn_section_part_count": len(subsections),
            }
        )
        fragments.append(fragment)
    return fragments


def subsection_heading(block: dict[str, Any]) -> str:
    subsections = (block.get("payload") or {}).get("subsections")
    if not isinstance(subsections, list) or len(subsections) != 1:
        return ""
    return str(subsections[0].get("heading") or "")


def apply(book_root: Path, *, backup_dir: Path | None, dry_run: bool) -> list[str]:
    spine = json.loads((book_root / "spine.json").read_text(encoding="utf-8"))
    chapters = {chapter["title"]: chapter for chapter in spine.get("chapters", [])}
    pages: list[tuple[Path, dict[str, Any]]] = []
    actions: list[str] = []
    for page_path in sorted((book_root / "pages").glob("*.json")):
        page = json.loads(page_path.read_text(encoding="utf-8"))
        title = str(page.get("title") or "")
        labs = LABS.get(title)
        if labs is None:
            continue
        if len(labs) != 5:
            raise ValueError(f"{title} must define exactly five expansion labs")
        placements = PLACEMENTS.get(title)
        if placements is None or set(placements) != {lab.slug for lab in labs}:
            raise ValueError(f"{title} must map every expansion lab to one subsection")
        chapter = chapters.get(title)
        if chapter is None:
            raise ValueError(f"missing spine chapter: {title}")
        chapter_number = int(page.get("order") or 0)
        retained = [
            block
            for block in page.get("blocks", [])
            if not str(block.get("id") or "").startswith("blk_wsnx_")
        ]
        additions = {lab.slug: block_for(page, chapter, chapter_number, lab) for lab in labs}
        slug_by_heading = {heading: slug for slug, heading in placements.items()}
        placed: list[str] = []
        distributed: list[dict[str, Any]] = []
        for block in retained:
            fragments = split_section(block) if block.get("type") == "section" else [block]
            for fragment in fragments:
                distributed.append(fragment)
                heading = subsection_heading(fragment)
                slug = slug_by_heading.get(heading)
                if slug:
                    distributed.append(additions[slug])
                    placed.append(slug)
        if set(placed) != set(additions) or len(placed) != len(additions):
            missing = sorted(set(additions) - set(placed))
            duplicates = sorted(slug for slug in placed if placed.count(slug) > 1)
            raise ValueError(
                f"{title} placement failed; missing={missing}, duplicates={duplicates}"
            )
        page["blocks"] = distributed
        page["updated_at"] = datetime.now(timezone.utc).timestamp()
        pages.append((page_path, page))
        actions.append(
            f"{title}: distributed 5 expansion interactives after matched subsections (total 6)"
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
    log_path = book_root / "curation.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(timezone.utc).isoformat()} installed 60 v2 interactives\n")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--book-root", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    actions = apply(args.book_root.resolve(), backup_dir=args.backup_dir, dry_run=args.dry_run)
    for action in actions:
        print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
