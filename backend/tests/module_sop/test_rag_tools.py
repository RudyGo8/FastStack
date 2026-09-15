import unittest
from unittest.mock import patch

from app.modules.sop.rag.runtime import reset_tool_call_guards
from app.modules.sop.tools.rag_tools import search_knowledge_base


class KnowledgeToolFormattingTests(unittest.TestCase):
    def tearDown(self):
        reset_tool_call_guards()

    def test_search_result_keeps_document_chunks_intact(self):
        reset_tool_call_guards()
        rag_result = {
            "docs": [
                {"filename": "alpha.pdf", "page_number": 1, "text": "Alpha fact"},
                {"filename": "beta.pdf", "page_number": 2, "text": "Beta fact"},
            ],
            "rag_trace": {},
        }

        with patch("app.modules.sop.rag.run_rag_graph", return_value=rag_result):
            result = search_knowledge_base.invoke({"query": "facts"})

        self.assertEqual(
            result,
            "检索块:\n[1] alpha.pdf (Page 1):\nAlpha fact\n\n---\n\n[2] beta.pdf (Page 2):\nBeta fact",
        )


if __name__ == "__main__":
    unittest.main()
