import pandas as pd
import numpy as np


def prepare_chart_data(df, chart_info):
    """
    转换DataFrame数据为图表所需格式

    参数:
        df: 输入的DataFrame
        chart_info: 包含图表配置的字典，应包含:
            - chart_type: 图表类型
            - x_col: x轴数据列名
            - y_col: y轴数据列名 (可选)
            - group_col: 分组列名 (可选)
            - bins: 直方图的分箱数 (可选，仅用于hist类型)

    返回:
        适合图表绘制的数据字典，或None如果处理失败
    """
    try:
        # 数据有效性校验
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("无效的DataFrame数据")

        if not chart_info or not isinstance(chart_info, dict):
            raise ValueError("无效的图表配置信息")

        # 检查必要字段
        required_fields = ['chart_type', 'x_col']
        for field in required_fields:
            if field not in chart_info:
                raise ValueError(f"图表配置缺少必要字段: {field}")

        chart_type = chart_info['chart_type']
        x_col = chart_info['x_col']

        # 检查列是否存在
        if x_col not in df.columns:
            raise ValueError(f"数据中不存在列: {x_col}")

        if 'y_col' in chart_info and chart_info['y_col'] and chart_info['y_col'] not in df.columns:
            raise ValueError(f"数据中不存在列: {chart_info['y_col']}")

        if 'group_col' in chart_info and chart_info['group_col'] and chart_info['group_col'] not in df.columns:
            raise ValueError(f"数据中不存在列: {chart_info['group_col']}")

        # 处理数据，移除None值
        data = df.copy()
        data = data.dropna(subset=[x_col])

        if 'y_col' in chart_info and chart_info['y_col']:
            y_col = chart_info['y_col']
            data = data.dropna(subset=[y_col])

        # 根据图表类型准备数据
        result = {}

        if chart_type in ['bar', 'line', 'scatter']:
            result['x'] = data[x_col].tolist()

            if 'y_col' in chart_info and chart_info['y_col']:
                result['y'] = data[chart_info['y_col']].tolist()
            else:
                # 如果没有指定y列，使用计数
                counts = data[x_col].value_counts().sort_index()
                result['x'] = counts.index.tolist()
                result['y'] = counts.values.tolist()

        elif chart_type == 'pie':
            # 统计x列各值的出现次数
            counts = data[x_col].value_counts()
            result['labels'] = counts.index.tolist()
            result['values'] = counts.values.tolist()

        elif chart_type == 'hist':
            # 使用x列的数据绘制直方图
            result['values'] = data[x_col].tolist()
            if 'bins' in chart_info:
                result['bins'] = chart_info['bins']

        else:
            raise ValueError(f"不支持的图表类型: {chart_type}")

        return result

    except Exception as e:
        print(f"准备图表数据时出错: {str(e)}")
        return None