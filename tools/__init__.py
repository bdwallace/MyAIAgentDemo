"""Tool Runtime · V0 外部工具；V0.5 长期记忆；V0.6 知识库检索。"""

from tools.browse_page import browse_page
from tools.execute_python import execute_python
from tools.memory import forget, recall, remember
from tools.rag import ingest_doc, search_docs
from tools.search_web import search_web

ALL_TOOLS = [
    search_web,
    browse_page,
    execute_python,
    remember,
    recall,
    forget,
    search_docs,
    ingest_doc,
]
