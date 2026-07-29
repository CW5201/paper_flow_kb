# processor/import_processor/nodes/node_entry.py
import logging
from pathlib import Path

from processor.import_processor.base import BaseNode
from processor.import_processor.exceptions import StateFieldError, FileProcessingError
from processor.import_processor.state import ImportGraphState


class NodeEntry(BaseNode):
    """
    入口节点：任务分发
    """
    name = "node_entry"

    def process(self, state: ImportGraphState):
        logging.info(f"state: {self.name}节点开始执行")

         #1获取输入路径
        import_file_path =state.get("import_file_path")

        #2校验路径是否存在
        if not import_file_path:
            raise StateFieldError(field_name="import_file_path",expected_type=str)

        #3校验文件是否存在
        import_file_path_obj=Path(import_file_path)
        if not import_file_path_obj.is_file():
            raise StateFieldError(message="文件不存在:{import_file_path}")
        #4通过后缀判断是什么文件
        if import_file_path_obj.suffix ==".md":
            state["is_md_read_enabled"] = True
        elif import_file_path_obj.suffix == ".pdf":
            state["is_pdf_read_enabled"] =True
        else:
            raise FileProcessingError(message=f"暂不支持当前文件:{import_file_path}")
        state["file_title"] = import_file_path_obj.stem
        state["file_dir"] =r"D:\output"

        return state