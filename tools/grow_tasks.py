"""查询华为云开发者成长中心的公开任务清单（匿名接口，零第三方依赖）。

数据源：devdata.huaweicloud.com 的 fwdo 转发路径，无需登录态。
注意：匿名访问拿不到个人完成状态（is_finish 恒为 false），只能拿到「有哪些任务」。

用法：
    python grow_tasks.py            # 默认取 60 条
    python grow_tasks.py 100        # 取 100 条
    python grow_tasks.py --json     # 输出原始 JSON，便于自己处理

积分值、周期、任务条数会随平台调整变化，以页面现状为准。
"""
import json
import sys
from urllib.request import Request, urlopen

BASE = "https://devdata.huaweicloud.com"
PREFIX = "/rest/developer/fwdo/rest/developer/servlet/hdcommunitysoservice/v1/growth"
CYCLE_CN = {"LIMIT": "仅一次", "DAILY": "每日", "WEEKLY": "每周", "MONTHLY": "每月"}


def post(path, payload=None, timeout=20):
    url = BASE + PREFIX + path
    data = json.dumps(payload or {}).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "grow-tasks/1.0 (+https://github.com/)")
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_tasks(page_size=60):
    raw = post("/mission/query-mission-list-by-condition",
               {"page_no": 1, "page_size": page_size})
    out = []
    for r in raw.get("QueryMissionDtoList") or []:
        rule = (r.get("rule_list") or [{}])[0]
        out.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "points": int(r.get("bonus") or 0),
            "cycle": CYCLE_CN.get(rule.get("mission_cycle_type") or "",
                                  rule.get("mission_cycle_type") or ""),
            "category": r.get("categoryName", ""),
            "desc": (r.get("description") or "")[:60],
            "url": r.get("url", ""),
        })
    return out, raw


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--json" in args:
        _, raw = list_tasks(60)
        print(json.dumps(raw, ensure_ascii=False, indent=2))
        sys.exit(0)
    size = int(args[0]) if args and args[0].isdigit() else 60
    tasks, raw = list_tasks(size)
    print("count=", len(tasks))
    for t in sorted(tasks, key=lambda x: (-x["points"], x["cycle"])):
        print(f'{t["cycle"]:<4} {t["points"]:>4}分  {t["title"]}')
        if t["desc"]:
            print(f'          └ {t["desc"]}')
