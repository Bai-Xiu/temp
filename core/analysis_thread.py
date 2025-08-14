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
                # 代码处理模式
                code_block = self.processor.generate_processing_code(self.request, self.file_paths)
                self.update_signal.emit("代码生成完成，开始执行...")

                # 清理代码块
                cleaned_code = self.clean_code_block(code_block)

                # 执行清理后的代码
                result = self.execute_cleaned_code(cleaned_code)

            else:
                # 直接回答模式
                result = self.processor.direct_answer(self.request, self.file_paths)

            self.complete_signal.emit({"status": "success", "result": result})
        except Exception as e:
            self.complete_signal.emit({"status": "error", "message": str(e)})

    def clean_code_block(self, code_block):
        """清理代码块，移除三重反引号和语言标识"""
        if not code_block:
            return ""
        cleaned = re.sub(r'^```[\w]*', '', code_block, flags=re.MULTILINE)
        cleaned = re.sub(r'```$', '', cleaned, flags=re.MULTILINE)
        return cleaned.strip()

    def execute_cleaned_code(self, cleaned_code):
        """执行代码并简化图表配置校验"""
        data_dict = self.processor.load_data_files(self.file_paths)
        full_code = f"{cleaned_code}\n"
        local_vars = {
            'data_dict': data_dict,
            'pd': pd,
            'np': np
        }

        try:
            exec(full_code, globals(), local_vars)
            result_table = local_vars.get('result_table')
            summary = local_vars.get('summary', '分析完成但未生成总结')
            chart_info = local_vars.get('chart_info', None)

            # 简化校验：只做必要检查，不强制禁用图表，仅添加警告
            if chart_info and isinstance(chart_info, dict):
                # 检查顶级必要字段
                top_required = ["chart_type", "title", "data_prep"]
                missing_top = [f for f in top_required if f not in chart_info]
                if missing_top:
                    summary += f"\n警告：图表配置缺少顶级字段 {missing_top}"

                # 检查data_prep子字典
                data_prep = chart_info.get("data_prep", {})
                if not isinstance(data_prep, dict):
                    summary += "\n警告：data_prep必须是字典类型"
                    chart_info["data_prep"] = {}  # 避免后续报错

            # 确保result_table存在
            if result_table is None:
                result_table = pd.concat(data_dict.values(), ignore_index=True)
                summary = "未生成有效分析结果，返回原始数据合并表格\n" + summary

            return {
                "result_table": result_table,
                "summary": summary,
                "chart_info": chart_info
            }
        except Exception as e:
            return {
                "summary": f"代码执行错误: {str(e)}\n\n执行的代码:\n{full_code}",
                "result_table": None,
                "chart_info": None
            }
