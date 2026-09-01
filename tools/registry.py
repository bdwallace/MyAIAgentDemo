"""Tool Runtime · 注册表。

V1 起工具按组登记，Graph 只认 ALL_TOOLS。
加工具：写 @tool 函数，挂进对应 GROUP，不要直接改 graph.py。
Trading API 不在 V1（要独立密钥，以后再说）。
"""

from tools.browse_page import browse_page
from tools.execute_python import execute_python
from tools.files import delete_file, list_dir, read_file, write_file
from tools.git import git_commit, git_diff, git_init, git_log, git_status
from tools.memory import forget, recall, remember
from tools.rag import ingest_doc, search_docs
from tools.search_web import search_web
from tools.shell import execute_shell

TOOL_GROUPS: list[tuple[str, str, list]] = [
    ("web", "互联网", [search_web, browse_page]),
    ("code", "代码", [execute_python, execute_shell]),
    ("fs", "文件", [list_dir, read_file, write_file, delete_file]),
    ("git", "Git", [git_init, git_status, git_log, git_diff, git_commit]),
    ("memory", "长期记忆", [remember, recall, forget]),
    ("rag", "知识库", [search_docs, ingest_doc]),
]

ALL_TOOLS = [tool for _gid, _title, tools in TOOL_GROUPS for tool in tools]


def catalog() -> list[dict]:
    rows = []
    for group_id, title, tools in TOOL_GROUPS:
        rows.append(
            {
                "id": group_id,
                "title": title,
                "tools": [
                    {
                        "name": item.name,
                        "description": (item.description or "").split("\n", 1)[0],
                    }
                    for item in tools
                ],
            }
        )
    return rows
