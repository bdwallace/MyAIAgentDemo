"""Tool Runtime · V0 三个外部工具；V0.5 加上长期记忆工具。"""

from tools.browse_page import browse_page
from tools.execute_python import execute_python
from tools.memory import forget, recall, remember
from tools.search_web import search_web

ALL_TOOLS = [search_web, browse_page, execute_python, remember, recall, forget]
