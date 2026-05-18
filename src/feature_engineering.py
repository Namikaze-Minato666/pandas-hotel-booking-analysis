"""
特征工程模块：
基于清洗后的数据构造业务分析所需的衍生字段。
"""

import pandas as pd
import numpy as np


def create_features(df):
    """
    构造衍生字段并返回增强后的 DataFrame。

    新增字段：
    - arrival_date     : 由年月日拼接而成的日期
    - total_nights      : 总入住天数（周末 + 平日）
    - total_guests      : 总入住人数（成人 + 儿童 + 婴儿）
    - is_family         : 是否为家庭客（有儿童即为家庭）
    - lead_time_group   : 提前预订天数分组（包含 lead_time=0）
    - adr_level         : 日均房价水平（低/中/高/异常免费）
    - season            : 入住月份所属季节
    - room_match        : 分配的房型是否与预订一致
    - is_valid_guest    : 是否为有效入住记录（人数 > 0 且 ADR > 0）
    """
    df = df.copy()

    # --- 日期字段 ---
    df["arrival_date"] = pd.to_datetime(
        df["arrival_date_year"].astype(str) + "-"
        + df["arrival_date_month"] + "-"
        + df["arrival_date_day_of_month"].astype(str),
        errors="coerce"
    )

    # --- 入住总天数 ---
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]

    # --- 入住总人数 ---
    df["total_guests"] = df["adults"] + df["children"] + df["babies"]

    # --- 是否家庭客 ---
    df["is_family"] = (df["children"] > 0).astype(int)

    # --- 提前预订天数分组（bins 起点为 -1 确保 lead_time=0 归入第一组） ---
    bins = [-1, 7, 30, 90, 180, float("inf")]
    labels = ["0-7天", "8-30天", "31-90天", "91-180天", "180天以上"]
    df["lead_time_group"] = pd.cut(
        df["lead_time"], bins=bins, labels=labels, right=True
    )

    # --- ADR 房价水平 ---
    # 先标记 ADR <= 0 为 "异常/免费"，再对 ADR > 0 做分位数切分
    df["adr_level"] = "异常/免费"
    mask_positive = df["adr"] > 0
    try:
        df.loc[mask_positive, "adr_level"] = pd.qcut(
            df.loc[mask_positive, "adr"],
            q=3,
            labels=["低", "中", "高"],
            duplicates="drop"
        )
    except ValueError:
        # 极端情况：可分位数不足以分出 3 组时，全部归为 "中"
        df.loc[mask_positive, "adr_level"] = "中"

    # --- 季节 ---
    season_map = {
        "January": "冬季", "February": "冬季", "March": "春季",
        "April": "春季",   "May": "春季",      "June": "夏季",
        "July": "夏季",    "August": "夏季",    "September": "秋季",
        "October": "秋季", "November": "秋季",  "December": "冬季",
    }
    df["season"] = df["arrival_date_month"].map(season_map)

    # --- 房型匹配 ---
    df["room_match"] = (
        df["reserved_room_type"] == df["assigned_room_type"]
    ).astype(int)

    # --- 有效客户标识 ---
    df["is_valid_guest"] = (
        (df["total_guests"] > 0) & (df["adr"] > 0)
    ).astype(int)

    return df
