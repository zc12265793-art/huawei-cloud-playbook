"""提交前脱敏自检：扫描仓库里有没有把个人信息带进去。

用法：python tools/check_secrets.py [仓库根目录]
退出码 0 = 干净；1 = 发现疑似敏感内容（把命中打印出来，人工判断）。

它只做「字符串特征」检查，不能替代你自己通读一遍。
"""
import io
import os
import re
import sys

# 疑似敏感特征；命中不一定是泄漏（比如文档里在讲解这个格式），需要人工看一眼
# 注意：只匹配「看起来像真实值」的串，讲解用的占位符 <XXX> 不会被命中
PATTERNS = [
    ("中国大陆手机号",     r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ("IAM/实例 32位hex",   r"\b[0-9a-f]{32}\b"),
    ("飞书 base/table id", r"\b(?:bas[A-Za-z0-9]{20,}|tbl[A-Za-z0-9]{16,})\b"),
    ("占位密钥变量",       r"\{\{SECRET_[A-Za-z0-9_]+\}\}"),
    ("本机绝对路径",       r"[A-Za-z]:\\(?:Users|Users\\Administrator|huawei-gallery|npm-global|Desktop)\b"),
]

# 这些文件本身是「讲解/占位」，跳过
# ⚠️ 注意：本文件在 SKIP_FILES 里，意味着下面这份「前提条件」整份不在自动扫描范围内。
#    就算它里面真的有真实值，check_secrets 也看不出来。改动那一份之后要人眼过一遍。
SKIP_FILES = {"check_secrets.py", "00-前提条件与配置.md"}

# 公开的、经核对不是个人信息的串，命中后跳过（免得每次误报）
# 判据：公开目录地址 / 全体用户同值 / 不含账号标识 → 可以写真实值
#   - a134fb53…：「0元领证书」活动页 ID，所有用户同一个入口
#   - 5 个 32 位认证 ID（见 docs/01 §9 表格）：edu.huaweicloud.com/certification/<ID>
#     公开课程详情页地址，不是账号标识；写成占位符挡不住任何人，只挡住了读者的便利
ALLOWLIST = {
    "a134fb53c0344989b8d2812c4b0564ac",  # 活动页 ID
    "ab32296d08d344bb86c5525c36adc0f4",  # 华为云计算服务实践
    "92841b01030c47f2864d38461546112c",  # 华为云存储服务实践
    "2e8fa91a249d4b399ab64b30dba095f9",  # 华为云数据库服务实践
    "ae1d1d6cb66448fdbd2208ff9b583702",  # 搭建 Discuz 论坛网站
    "9b164a73f33545d3bc69a523db79a04e",  # 鲲鹏弹性云服务器高可用性架构实践
}

TEXT_EXT = {".md", ".py", ".mjs", ".js", ".json", ".txt", ".sh", ".ps1", ".yml", ".yaml", ".html", ".css"}


def scan(root):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            if fn in SKIP_FILES:
                continue
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dirpath, fn)
            try:
                with io.open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                for label, pat in PATTERNS:
                    for m in re.finditer(pat, line):
                        if m.group(0) in ALLOWLIST:
                            continue
                        rel = os.path.relpath(p, root)
                        snippet = line.strip()[:100]
                        hits.append((label, rel, i, snippet))
    return hits


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = scan(root)
    if hits:
        print("发现 %d 处疑似敏感内容，请逐条核对：\n" % len(hits))
        for label, rel, line, snippet in hits:
            print("  [%s] %s:%d" % (label, rel, line))
            print("      %s" % snippet)
        print("\n若确认是讲解用的占位符，把它加进 PATTERNS 的例外或 SKIP_FILES。")
        sys.exit(1)
    print("干净：未发现疑似敏感内容。")
    sys.exit(0)
