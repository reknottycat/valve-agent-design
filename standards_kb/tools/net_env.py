#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
standards_kb / net_env.py —— 代理环境自愈

背景
----
本机常年挂着 FlClash(127.0.0.1:7890)。FlClash 有三种状态:
  1. 正常     —— 7890 在监听
  2. DNS-only —— 只听 1053,7890/7897 都没有
  3. 全停     —— 进程只剩 FlClashHelperService(守护),一个口都不听

系统环境变量里 HTTP_PROXY/HTTPS_PROXY 通常还残留着 http://127.0.0.1:7890。
在状态 2/3 下,任何尊重 env 的 HTTP 客户端都会**静默走死代理**,
表现为 `Connection refused (os error 10061)`,很容易被误判成
「对方站点挂了」或「需要换数据源」。

规则
----
注入代理前先探端口;探不通就**主动清掉**残留 env
(含小写形式),让请求直连。残留 env 比没有 env 更危险。

用法
----
    from net_env import prepare_env
    prepare_env()          # 会在需要时 pop 掉死代理 env
"""
from __future__ import annotations

import os
import socket
import sys

PROXY_HOST = "127.0.0.1"
PROXY_PORTS = (7890, 7897, 1053)  # mixed / http / dns,按 FlClash 实际监听
PROXY_ENV_KEYS = (
    "HTTP_PROXY", "http_proxy",
    "HTTPS_PROXY", "https_proxy",
    "ALL_PROXY", "all_proxy",
)


def _port_alive(port: int, host: str = PROXY_HOST, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def proxy_ports_alive() -> list[int]:
    """当前真正在监听的代理端口。"""
    return [p for p in PROXY_PORTS if _port_alive(p)]


def prepare_env(verbose: bool = True) -> dict:
    """探测代理口;不通就把残留 proxy env 清掉。

    返回诊断字典,便于脚本记录到台账。
    """
    alive = proxy_ports_alive()
    env_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or ""
    diag = {
        "alive_ports": alive,
        "env_proxy": env_proxy,
        "action": "none",
        "dropped": [],
    }

    if alive:
        diag["action"] = "keep_env_proxy"
        if verbose:
            print(f"[net_env] 代理口存活 {alive}，保留 env 代理 {env_proxy}")
        return diag

    # 没有端口在监听 —— env 里的代理是死的，必须清掉
    dropped = []
    for k in PROXY_ENV_KEYS:
        if k in os.environ:
            os.environ.pop(k, None)
            dropped.append(k)
    diag["action"] = "dropped_dead_proxy_env"
    diag["dropped"] = dropped
    if verbose:
        if dropped:
            print(f"[net_env] 无代理口在监听（试过 {list(PROXY_PORTS)}），"
                  f"已清除残留 env: {dropped}")
        else:
            print(f"[net_env] 无代理口在监听（试过 {list(PROXY_PORTS)}），env 本就干净")
    return diag


if __name__ == "__main__":
    import json
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(prepare_env(), ensure_ascii=False, indent=1))
