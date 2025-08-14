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

                # 执行清理后的代码（仅处理数据，不涉及UI绘制）
                result = self.execute_cleaned_code(cleaned_code)

                # 检查chart_info是否完整
                if "chart_info" in result and result["chart_info"]:
                    required_fields = ["chart_type", "title", "data_prep"]
                    missing = [f for f in required_fields if f not in result["chart_info"]]
                    if missing:
                        result["summary"] += f"\n警告：图表配置不完整，缺少字段：{missing}"
                        result["chart_info"] = None

            else:
                # 直接回答模式
                result = self.processor.direct_answer(self.request, self.file_paths)

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

            # 提取结果，确保三个变量都存在
            result_table = local_vars.get('result_table')
            summary = local_vars.get('summary', '分析完成但未生成总结')
            chart_info = local_vars.get('chart_info', None)

            # 新增：校验chart_info结构
            if chart_info is not None and isinstance(chart_info, dict):
                # 检查顶级字段
                required_top = ["chart_type", "title", "data_prep"]
                missing_top = [f for f in required_top if f not in chart_info]
                if missing_top:
                    summary += f"\n警告：图表配置缺少顶级字段 {missing_top}，已自动禁用图表"
                    chart_info = None
                else:
                    # 检查data_prep字段
                    data_prep = chart_info.get("data_prep", {})
                    chart_type = chart_info.get("chart_type")
                    required_data = []

                    # 根据图表类型检查必要数据列
                    if chart_type in ["bar", "line", "scatter"]:
                        required_data = ["x_col", "y_col"]
                    elif chart_type == "pie":
                        required_data = ["x_col", "values"]
                    elif chart_type == "hist":
                        required_data = ["x_col"]

                    missing_data = [f for f in required_data if f not in data_prep]
                    if missing_data:
                        summary += f"\n警告：图表{chart_type}缺少必要数据列 {missing_data}，已自动禁用图表"
                        chart_info = None
                    else:
                        # 检查列名是否存在于result_table
                        if result_table is not None:
                            all_cols = result_table.columns.tolist()
                            invalid_cols = [f for f in data_prep.values()
                                            if f is not None and f not in all_cols]
                            if invalid_cols:
                                summary += f"\n警告：图表配置中的列 {invalid_cols} 不存在于结果表中，已自动禁用图表"
                                chart_info = None
                        else:
                            chart_info = None

            return {
                "result_table": result_table,
                "summary": summary,
                "chart_info": chart_info
            }

            # 确保result_table始终存在
            if result_table is None:
                # 如果没有生成表格，默认合并所有数据
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