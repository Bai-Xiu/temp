import re
import pandas as pd
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal


class AnalysisThread(QThread):
    update_signal = pyqtSignal(str)
    complete_signal = pyqtSignal(dict)

    def __init__(self, processor, file_paths, request, mode):
        super().__init__()
        self.processor = processor
        self.file_paths = file_paths
        self.request = request
        self.mode = mode

    def run(self):
        try:
            self.update_signal.emit("正在进行分析...")
            if self.mode == "1":
                # 代码处理模式 - 仅处理数据，不生成图表
                code_block = self.processor.generate_processing_code(self.request, self.file_paths)
                self.update_signal.emit("代码生成完成，开始执行...")
                cleaned_code = self.clean_code_block(code_block)
                result = self.execute_cleaned_code(cleaned_code)
            else:
                # 直接回答模式
                result = self.processor.direct_answer(self.request, self.file_paths)

            # 确保结果中不包含任何绘图指令，只返回数据
            self.complete_signal.emit({"status": "success", "result": result})
        except Exception as e:
            self.complete_signal.emit({"status": "error", "message": str(e)})

    def clean_code_block(self, code_block):  # 修复方法名定义
        """清理代码块，移除三重反引号和语言标识"""
        if not code_block:
            return ""

        # 移除代码块中的三重反引号和可能的语言标识（如```python）
        cleaned = re.sub(r'^```[\w]*', '', code_block, flags=re.MULTILINE)
        cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE)
        return cleaned.strip()

    def execute_cleaned_code(self, cleaned_code):
        """执行完整代码（无包装函数）"""
        # 准备数据字典
        data_dict = self.processor.load_data_files(self.file_paths)

        # 构建完整执行代码
        full_code = f"{cleaned_code}\n"

        # 执行代码
        local_vars = {
            'data_dict': data_dict,
            'pd': pd,
            'np': np
        }
        try:
            exec(full_code, globals(), local_vars)

            # 提取结果（增加chart_info提取）
            result_table = local_vars.get('result_table')
            summary = local_vars.get('summary', '分析完成但未生成总结')
            chart_info = local_vars.get('chart_info')  # 新增提取chart_info

            return {
                "result_table": result_table,
                "summary": summary,
                "chart_info": chart_info  # 新增返回chart_info
            }
        except Exception as e:
            return {
                "summary": f"代码执行错误: {str(e)}\n\n执行的代码:\n{full_code}",
                "chart_info": None  # 错误时也返回chart_info键
            }