"""
分析模块：
- 取消行为分析
- 需求趋势分析
- 客户结构与渠道分析
- ADR房价与收入贡献分析
"""

import pandas as pd
import numpy as np
from src.config import PROCESSED_DATA_PATH


def load_cleaned_data(path=None):
    """加载清洗后的数据，默认从 config.PROCESSED_DATA_PATH 读取。"""
    filepath = path or PROCESSED_DATA_PATH
    return pd.read_csv(filepath, parse_dates=["arrival_date", "reservation_status_date"])


def calculate_overall_cancel_rate(df):
    """返回整体预订数、取消订单数、未取消订单数、整体取消率。"""
    total = len(df)
    canceled = int(df["is_canceled"].sum())
    non_canceled = total - canceled
    rate = canceled / total if total > 0 else 0.0
    return total, canceled, non_canceled, rate


def calculate_cancel_rate_by_group(df, group_col):
    """按指定字段分组，返回含 cancel_rate 的 DataFrame（按取消率降序）。"""
    grouped = df.groupby(group_col)["is_canceled"].agg(
        total_bookings="count",
        canceled_bookings="sum",
    ).reset_index()
    grouped["non_canceled_bookings"] = grouped["total_bookings"] - grouped["canceled_bookings"]
    grouped["cancel_rate"] = grouped["canceled_bookings"] / grouped["total_bookings"]
    return grouped.sort_values("cancel_rate", ascending=False).reset_index(drop=True)


def calculate_monthly_cancel_trend(df):
    """基于 arrival_date 按月份统计预订量与取消率趋势。"""
    monthly = df.groupby(pd.Grouper(key="arrival_date", freq="M")).agg(
        total_bookings=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
    ).reset_index()
    monthly["month"] = monthly["arrival_date"].dt.strftime("%Y-%m")
    monthly["non_canceled_bookings"] = monthly["total_bookings"] - monthly["canceled_bookings"]
    monthly["cancel_rate"] = monthly["canceled_bookings"] / monthly["total_bookings"]
    return monthly[["month", "total_bookings", "canceled_bookings",
                    "non_canceled_bookings", "cancel_rate"]]


def calculate_monthly_demand_trend(df):
    """只统计 is_canceled == 0 的订单，按 month 和 hotel 统计真实入住需求量。"""
    not_canceled = df[df["is_canceled"] == 0].copy()
    not_canceled["arrival_date"] = pd.to_datetime(not_canceled["arrival_date"])
    demand = not_canceled.groupby(
        [pd.Grouper(key="arrival_date", freq="M"), "hotel"]
    ).size().reset_index(name="demand")
    demand["month"] = demand["arrival_date"].dt.strftime("%Y-%m")
    return demand[["month", "hotel", "demand"]]


def calculate_group_summary(df, group_col):
    """按指定字段分组，返回预订量、取消率、全量平均ADR（按预订量降序）。"""
    grouped = df.groupby(group_col).agg(
        total_bookings=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
        avg_adr=("adr", "mean"),
    ).reset_index()
    grouped["cancel_rate"] = grouped["canceled_bookings"] / grouped["total_bookings"]
    grouped["avg_adr"] = grouped["avg_adr"].round(2)
    return grouped.sort_values("total_bookings", ascending=False).reset_index(drop=True)


def calculate_special_request_cancel_rate(df):
    """按 total_of_special_requests 分组，统计各组的取消率。"""
    grouped = df.groupby("total_of_special_requests")["is_canceled"].agg(
        total_bookings="count",
        canceled_bookings="sum",
    ).reset_index()
    grouped["non_canceled_bookings"] = grouped["total_bookings"] - grouped["canceled_bookings"]
    grouped["cancel_rate"] = grouped["canceled_bookings"] / grouped["total_bookings"]
    return grouped.sort_values("cancel_rate", ascending=False).reset_index(drop=True)


# ============================================================
#  ADR 房价与收入贡献分析
# ============================================================

def prepare_revenue_data(df):
    """
    构造收入分析字段并返回仅含有效未取消订单的 DataFrame。

    新增字段：
        total_nights      — 入住总晚数（从原始列重新计算）
        estimated_revenue — adr * total_nights

    过滤条件：is_canceled == 0, adr > 0, total_nights > 0
    """
    df = df.copy()
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
    df["estimated_revenue"] = df["adr"] * df["total_nights"]
    valid = df[(df["is_canceled"] == 0) & (df["adr"] > 0) & (df["total_nights"] > 0)]
    return valid


def calculate_revenue_overview(df):
    """
    返回整体 ADR 与收入概览统计（基于未取消订单）。

    返回 dict：
        total_bookings, avg_adr, median_adr,
        total_estimated_revenue, avg_revenue_per_booking, avg_nights
    """
    valid = prepare_revenue_data(df)
    return {
        "total_bookings": len(valid),
        "avg_adr": round(valid["adr"].mean(), 2),
        "median_adr": round(valid["adr"].median(), 2),
        "total_estimated_revenue": round(valid["estimated_revenue"].sum(), 2),
        "avg_revenue_per_booking": round(valid["estimated_revenue"].mean(), 2),
        "avg_nights": round(valid["total_nights"].mean(), 2),
    }


def calculate_revenue_by_group(df, group_col):
    """
    按指定字段分组统计 ADR 与收入贡献（基于未取消订单）。

    返回列：
        group_col, booking_count, avg_adr, median_adr,
        total_estimated_revenue, revenue_pct
    """
    valid = prepare_revenue_data(df)
    grouped = valid.groupby(group_col).agg(
        booking_count=("estimated_revenue", "count"),
        avg_adr=("adr", "mean"),
        median_adr=("adr", "median"),
        total_estimated_revenue=("estimated_revenue", "sum"),
    ).reset_index()
    total_rev = grouped["total_estimated_revenue"].sum()
    grouped["revenue_pct"] = (grouped["total_estimated_revenue"] / total_rev).round(4)
    grouped["avg_adr"] = grouped["avg_adr"].round(2)
    grouped["median_adr"] = grouped["median_adr"].round(2)
    grouped["total_estimated_revenue"] = grouped["total_estimated_revenue"].round(2)
    return grouped.sort_values("total_estimated_revenue", ascending=False).reset_index(drop=True)


def calculate_monthly_revenue_trend(df):
    """
    按月统计 ADR 与收入趋势（基于未取消订单，兼容旧版 pandas）。

    使用 dt.to_period("M") 避免 "ME" 兼容性问题。
    """
    valid = prepare_revenue_data(df)
    valid = valid.copy()
    valid["arrival_date"] = pd.to_datetime(valid["arrival_date"])
    valid["month"] = valid["arrival_date"].dt.to_period("M").astype(str)
    monthly = valid.groupby("month").agg(
        booking_count=("estimated_revenue", "count"),
        avg_adr=("adr", "mean"),
        total_estimated_revenue=("estimated_revenue", "sum"),
    ).reset_index()
    monthly["avg_adr"] = monthly["avg_adr"].round(2)
    monthly["total_estimated_revenue"] = monthly["total_estimated_revenue"].round(2)
    return monthly


def calculate_canceled_potential_revenue(df, group_col):
    """
    按指定字段汇总取消订单的潜在收入损失。

    只统计 is_canceled == 1 的订单，构造 canceled_potential_revenue = adr * total_nights。
    """
    canceled = df[df["is_canceled"] == 1].copy()
    canceled["total_nights"] = (
        canceled["stays_in_weekend_nights"] + canceled["stays_in_week_nights"]
    )
    canceled["canceled_potential_revenue"] = (
        canceled["adr"] * canceled["total_nights"]
    )
    grouped = canceled.groupby(group_col).agg(
        canceled_bookings=("is_canceled", "count"),
        potential_revenue_loss=("canceled_potential_revenue", "sum"),
    ).reset_index()
    grouped["potential_revenue_loss"] = grouped["potential_revenue_loss"].round(2)
    return grouped.sort_values("potential_revenue_loss", ascending=False).reset_index(drop=True)


# ============================================================
#  入住时长与提前预订行为分析
# ============================================================

def add_stay_lead_features(df):
    """
    添加入住行为分析所需的衍生字段。

    新增/覆写：
        total_nights        — 入住总晚数
        estimated_revenue   — adr * total_nights
        is_family           — (children + babies) > 0
        stay_length_group   — 入住晚数分组（1晚 / 2-3晚 / 4-7晚 / 8晚以上）
    """
    df = df.copy()
    df["total_nights"] = df["stays_in_weekend_nights"] + df["stays_in_week_nights"]
    df["estimated_revenue"] = df["adr"] * df["total_nights"]
    df["is_family"] = ((df["children"] + df["babies"]) > 0).astype(int)

    stay_bins = [0, 1, 3, 7, float("inf")]
    stay_labels = ["1晚", "2-3晚", "4-7晚", "8晚以上"]
    df["stay_length_group"] = pd.cut(
        df["total_nights"], bins=stay_bins, labels=stay_labels, right=True
    )
    return df


def _merge_revenue_stats(all_stats, non_canceled, group_col):
    """将全量统计与非取消订单的收入统计合并。"""
    non_canceled = non_canceled[
        (non_canceled["adr"] > 0) & (non_canceled["total_nights"] > 0)
    ]
    rev = non_canceled.groupby(group_col).agg(
        avg_adr=("adr", "mean"),
        total_estimated_revenue=("estimated_revenue", "sum"),
        avg_estimated_revenue=("estimated_revenue", "mean"),
    ).reset_index()
    result = all_stats.merge(rev, on=group_col, how="left")
    result["avg_adr"] = result["avg_adr"].round(2)
    result["avg_estimated_revenue"] = result["avg_estimated_revenue"].round(2)
    result["total_estimated_revenue"] = result["total_estimated_revenue"].round(2)
    return result


def calculate_stay_length_summary(df):
    """按入住晚数分组统计预订量、取消率、ADR、预估收入。"""
    df = add_stay_lead_features(df)
    all_stats = df.groupby("stay_length_group").agg(
        booking_count=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
    ).reset_index()
    all_stats["cancel_rate"] = (
        all_stats["canceled_bookings"] / all_stats["booking_count"]
    )
    all_stats["booking_pct"] = (
        all_stats["booking_count"] / all_stats["booking_count"].sum()
    )

    result = _merge_revenue_stats(all_stats, df[df["is_canceled"] == 0],
                                  "stay_length_group")
    result["cancel_rate"] = result["cancel_rate"].round(4)
    result["booking_pct"] = result["booking_pct"].round(4)

    stay_order = ["1晚", "2-3晚", "4-7晚", "8晚以上"]
    result["stay_length_group"] = pd.Categorical(
        result["stay_length_group"], categories=stay_order, ordered=True
    )
    return result.sort_values("stay_length_group").reset_index(drop=True)


def calculate_lead_time_summary(df):
    """按提前预订天数分组统计预订量、取消率、ADR、预估收入。"""
    df = add_stay_lead_features(df)
    all_stats = df.groupby("lead_time_group").agg(
        booking_count=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
        avg_lead_time=("lead_time", "mean"),
    ).reset_index()
    all_stats["cancel_rate"] = (
        all_stats["canceled_bookings"] / all_stats["booking_count"]
    )
    all_stats["booking_pct"] = (
        all_stats["booking_count"] / all_stats["booking_count"].sum()
    )

    result = _merge_revenue_stats(all_stats, df[df["is_canceled"] == 0],
                                  "lead_time_group")
    result["cancel_rate"] = result["cancel_rate"].round(4)
    result["booking_pct"] = result["booking_pct"].round(4)
    result["avg_lead_time"] = result["avg_lead_time"].round(2)

    lt_order = ["0-7天", "8-30天", "31-90天", "91-180天", "180天以上"]
    result["lead_time_group"] = pd.Categorical(
        result["lead_time_group"], categories=lt_order, ordered=True
    )
    return result.sort_values("lead_time_group").reset_index(drop=True)


def calculate_family_behavior_summary(df):
    """按 is_family 统计家庭与非家庭客户的行为差异。"""
    df = add_stay_lead_features(df)
    df["family_label"] = df["is_family"].map({1: "家庭客户", 0: "非家庭客户"})

    all_stats = df.groupby("family_label").agg(
        booking_count=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
        avg_total_nights=("total_nights", "mean"),
    ).reset_index()
    all_stats["cancel_rate"] = (
        all_stats["canceled_bookings"] / all_stats["booking_count"]
    )

    result = _merge_revenue_stats(all_stats, df[df["is_canceled"] == 0],
                                  "family_label")
    result["cancel_rate"] = result["cancel_rate"].round(4)
    result["avg_total_nights"] = result["avg_total_nights"].round(2)
    return result.reset_index(drop=True)


def calculate_season_stay_summary(df):
    """按季节统计入住行为差异。"""
    df = add_stay_lead_features(df)
    all_stats = df.groupby("season").agg(
        booking_count=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
        avg_total_nights=("total_nights", "mean"),
    ).reset_index()
    all_stats["cancel_rate"] = (
        all_stats["canceled_bookings"] / all_stats["booking_count"]
    )

    result = _merge_revenue_stats(all_stats, df[df["is_canceled"] == 0], "season")
    result["cancel_rate"] = result["cancel_rate"].round(4)
    result["avg_total_nights"] = result["avg_total_nights"].round(2)

    season_order = ["春季", "夏季", "秋季", "冬季"]
    result["season"] = pd.Categorical(
        result["season"], categories=season_order, ordered=True
    )
    return result.sort_values("season").reset_index(drop=True)


def calculate_hotel_stay_summary(df):
    """按 hotel 类型统计入住行为差异。"""
    df = add_stay_lead_features(df)
    all_stats = df.groupby("hotel").agg(
        booking_count=("is_canceled", "count"),
        canceled_bookings=("is_canceled", "sum"),
        avg_total_nights=("total_nights", "mean"),
        avg_lead_time=("lead_time", "mean"),
    ).reset_index()
    all_stats["cancel_rate"] = (
        all_stats["canceled_bookings"] / all_stats["booking_count"]
    )

    result = _merge_revenue_stats(all_stats, df[df["is_canceled"] == 0], "hotel")
    result["cancel_rate"] = result["cancel_rate"].round(4)
    result["avg_total_nights"] = result["avg_total_nights"].round(2)
    result["avg_lead_time"] = result["avg_lead_time"].round(2)
    return result.reset_index(drop=True)
