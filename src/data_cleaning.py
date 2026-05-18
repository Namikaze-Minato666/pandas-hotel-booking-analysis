"""
数据清洗模块：
- 加载原始 CSV
- 输出数据概览
- 缺失值统计
- 缺失值处理
"""

import pandas as pd
from src.config import RAW_DATA_PATH


def load_data(path=None):
    """读取酒店预订原始 CSV 文件。"""
    if path is None:
        path = RAW_DATA_PATH
    df = pd.read_csv(path)
    return df


def get_data_overview(df):
    """打印数据基本概览：shape、dtypes、前几行、统计描述。"""
    print("=" * 60)
    print("【数据概览】")
    print("=" * 60)
    print(f"Shape: {df.shape}")
    print(f"内存占用: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    print()
    print("列名与数据类型:")
    print(df.dtypes.to_string())
    print()
    print("前 5 行:")
    print(df.head().to_string())
    print()
    print("数值列描述统计:")
    print(df.describe().to_string())
    print()
    print("分类列示例值:")
    cat_cols = df.select_dtypes(include="object").columns
    for col in cat_cols:
        unique_vals = df[col].dropna().unique()
        preview = unique_vals[:5] if len(unique_vals) > 5 else unique_vals
        print(f"  {col}: {len(unique_vals)} 个唯一值, 示例: {list(preview)}")


def get_missing_summary(df):
    """返回缺失值统计 DataFrame，含数量和比例。"""
    missing_count = df.isnull().sum()
    missing_pct = (missing_count / len(df) * 100).round(2)
    summary = pd.DataFrame({
        "列名": missing_count.index,
        "缺失数量": missing_count.values,
        "缺失比例(%)": missing_pct.values
    })
    summary = summary[summary["缺失数量"] > 0].sort_values(
        "缺失数量", ascending=False
    )
    return summary


def clean_missing_values(df):
    """
    处理缺失值并返回清洗后的 DataFrame。

    策略：
    - company  : 新建 has_company 布尔列后删除原列（缺失率 94.3%）
    - agent    : 缺失填充 0，新建 has_agent 布尔列
    - country  : 缺失填充 'Unknown'
    - children : 缺失填充 0，转为 int 类型
    - reservation_status_date : 转为 datetime 类型

    所有列操作前先判断列是否存在，避免重复运行时出错。
    """
    df = df.copy()  # 不修改原始数据

    # company：缺失率 94.3%，转为布尔标识后删除
    if "company" in df.columns:
        df["has_company"] = df["company"].notna().astype(int)
        df.drop(columns=["company"], inplace=True)

    # agent：缺失表示无旅行社中介，填充 0 并新建布尔标识
    if "agent" in df.columns:
        df["has_agent"] = df["agent"].notna().astype(int)
        df["agent"] = df["agent"].fillna(0).astype(int)

    # country：极少缺失，填充 "Unknown"
    if "country" in df.columns:
        df["country"] = df["country"].fillna("Unknown")

    # children：缺失填充 0，转为 int（原为 float 因含 NaN）
    if "children" in df.columns:
        df["children"] = df["children"].fillna(0).astype(int)

    # reservation_status_date：转为 datetime
    if "reservation_status_date" in df.columns:
        df["reservation_status_date"] = pd.to_datetime(
            df["reservation_status_date"]
        )

    return df
