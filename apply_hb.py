#!/usr/bin/env python3
# apply_hb.py — 给 openclaw.json 的 girl agent 注入 heartbeat 配置（多机器部署用）
# 用法（新机器）：把本文件和 heartbeat_girl.json 拷到同一目录后运行：
#   python apply_hb.py
# 会先备份 openclaw.json 为 .bak-heartbeat，再写入 girl 的 heartbeat。
# 不含任何密钥/token，可安全提交。
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.expanduser('~/.openclaw/openclaw.json')
HB = os.path.join(HERE, 'heartbeat_girl.json')


def main() -> int:
    if not os.path.exists(HB):
        print(f'ERROR: {HB} 不存在（先拷过来）')
        return 1
    if not os.path.exists(CFG):
        print(f'ERROR: {CFG} 不存在（你在这台机器配过 openclaw 吗）')
        return 1

    hb = json.load(open(HB, encoding='utf-8'))
    cfg = json.load(open(CFG, encoding='utf-8'))

    # 备份
    backup = CFG + '.bak-heartbeat'
    with open(backup, 'w', encoding='utf-8') as f:
        f.write(open(CFG, encoding='utf-8').read())

    agents = cfg.get('agents', {}).get('list', [])
    for a in agents:
        if a.get('id') == 'girl':
            a['heartbeat'] = hb
            with open(CFG, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            print(f'OK: girl 心跳已注入；备份在 {backup}')
            print(f'    every={hb.get("every")} target={hb.get("target")} '
                  f'activeHours={hb.get("activeHours")}')
            return 0

    print('ERROR: agents.list 里没找到 id=girl，未改动任何东西')
    return 1


if __name__ == '__main__':
    sys.exit(main())
