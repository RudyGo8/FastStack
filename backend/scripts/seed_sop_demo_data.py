#!/usr/bin/env python3
"""
S&OP 样例数据种子脚本：从 Excel 解析演示数据灌入 sopfast_mysql 库。
用于开发环境让前端页面有数据可展示。

用法: cd backend && uv run python scripts/seed_sop_demo_data.py
"""

import re
import sys
from datetime import date, datetime
from pathlib import Path

import openpyxl
from sqlalchemy import text

# 确保可以 import app 模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.sop.database import SessionLocal, init_sop_tables
from app.modules.sop.models.db_sop import (
    SopActivationDaily,
    SopForecastMonthly,
    SopSalesDaily,
    SopSourceSnapshot,
    SopSpu,
)

EXCEL_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "business" / "S&OP基础数据及报表.xlsx"
SPU_CODE = "C706"
SPU_NAME = "AI 眼镜（样例）"
BATCH_ID = f"seed-demo-{datetime.now():%Y%m%d%H%M%S}"
SNAPSHOT_AT = datetime.now()

CHANNELS = ["国内电商", "海外电商", "线下门店", "经销商", "运营商", "行业客户"]


def parse_month(month_str: str) -> str:
    """'2020年10月' → '2020-10-01'"""
    m = re.match(r"(\d{4})年(\d{1,2})月", month_str)
    if not m:
        return ""
    return f"{m.group(1)}-{int(m.group(2)):02d}-01"


def seed_spu(db):
    existing = db.query(SopSpu).filter(SopSpu.spu_code == SPU_CODE).first()
    if existing:
        print(f"  SPU {SPU_CODE} 已存在，跳过创建")
        return
    spu = SopSpu(
        spu_code=SPU_CODE,
        spu_name=SPU_NAME,
        product_line="AR/AI 智能硬件",
        brand="DemoBrand",
        category="消费电子",
        lifecycle_stage="growth",
        source_system="seed-demo",
        is_active=True,
    )
    db.add(spu)
    db.flush()
    print(f"  ✅ 创建 SPU: {SPU_CODE} {SPU_NAME}")


def seed_historical_data(db):
    """报表1-走势图 → sop_sales_daily + sop_activation_daily"""
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb["报表1-走势图"]

    sales_count = 0
    activation_count = 0

    for row in ws.iter_rows(min_row=3, values_only=True):
        month_label = str(row[0] or "").strip()
        business_date_str = parse_month(month_label)
        if not business_date_str:
            continue
        business_date = date.fromisoformat(business_date_str)
        outbound = int(row[1]) if row[1] else 0
        activation = int(row[2]) if row[2] else 0

        if outbound > 0:
            db.add(SopSalesDaily(
                spu_code=SPU_CODE,
                business_date=business_date,
                region="ALL",
                channel="ALL",
                order_qty=outbound,
                outbound_qty=outbound,
                source_system="seed-demo",
                source_table="sop_demo_sales",
                batch_id=BATCH_ID,
                snapshot_at=SNAPSHOT_AT,
            ))
            sales_count += 1

        if activation > 0:
            db.add(SopActivationDaily(
                spu_code=SPU_CODE,
                business_date=business_date,
                region="ALL",
                channel="ALL",
                activation_qty=activation,
                source_system="seed-demo",
                source_table="sop_demo_activation",
                batch_id=BATCH_ID,
                snapshot_at=SNAPSHOT_AT,
            ))
            activation_count += 1

    db.flush()
    print(f"  ✅ 历史数据: {sales_count} 条出库 + {activation_count} 条激活 (60个月)")
    return sales_count, activation_count


def seed_channel_forecasts(db):
    """报表2-分渠道提报预测对比 → sop_forecast_monthly (submit + ai_baseline)"""
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws = wb["报表2-分渠道提报预测对比"]

    # 读取表头月份 (第5行)
    rows = list(ws.iter_rows(values_only=True))
    header_row_idx = None
    for i, row in enumerate(rows):
        if row[0] == "渠道" and row[1] and "月" in str(row[1]):
            header_row_idx = i
            break
    if header_row_idx is None:
        print("  ❌ 未找到渠道预测表头")
        return 0

    months = [parse_month(str(m)) for m in rows[header_row_idx][1:7] if m]

    # 读取"一、分渠道提报预测数量"区块
    submit_data = {}
    section_start = header_row_idx + 1
    for row in rows[section_start:section_start + 6]:
        channel = str(row[0] or "").strip()
        if channel in CHANNELS:
            submit_data[channel] = [int(v) if v else 0 for v in row[1:7]]

    # 读取"二、AI预测基准"区块
    ai_data = {}
    ai_section_start = None
    for i, row in enumerate(rows[section_start + 7:], start=section_start + 7):
        if row[0] == "渠道" and row[1] and "月" in str(row[1]):
            ai_section_start = i
            break

    if ai_section_start:
        for row in rows[ai_section_start + 1:ai_section_start + 7]:
            channel = str(row[0] or "").strip()
            if channel in CHANNELS:
                ai_data[channel] = [int(v) if v else 0 for v in row[1:7]]

    count = 0
    for channel in CHANNELS:
        for i, month_str in enumerate(months):
            if not month_str:
                continue
            forecast_month = date.fromisoformat(month_str)

            # 提报预测
            submit_qty = submit_data.get(channel, [0] * 6)[i]
            if submit_qty:
                db.add(SopForecastMonthly(
                    spu_code=SPU_CODE,
                    forecast_month=forecast_month,
                    region="ALL",
                    channel=channel,
                    forecast_type="sales_submission",
                    forecast_qty=submit_qty,
                    version="current",
                    source_system="seed-demo",
                    source_table="sop_demo_forecast_submit",
                    batch_id=BATCH_ID,
                    snapshot_at=SNAPSHOT_AT,
                ))
                count += 1

            # AI 基准
            ai_qty = ai_data.get(channel, [0] * 6)[i]
            if ai_qty:
                db.add(SopForecastMonthly(
                    spu_code=SPU_CODE,
                    forecast_month=forecast_month,
                    region="ALL",
                    channel=channel,
                    forecast_type="ai_baseline",
                    forecast_qty=ai_qty,
                    version="current",
                    source_system="seed-demo",
                    source_table="sop_demo_forecast_ai",
                    batch_id=BATCH_ID,
                    snapshot_at=SNAPSHOT_AT,
                ))
                count += 1

    db.flush()
    print(f"  ✅ 渠道预测: {count} 条 (6渠道 × 6月 × 2类型)")
    return count


def seed_source_snapshots(db, sales_count, activation_count, forecast_count):
    """创建数据源快照记录"""
    snapshots = [
        ("sales", "sop_demo_sales", sales_count),
        ("activation", "sop_demo_activation", activation_count),
        ("forecast", "sop_demo_forecast", forecast_count),
    ]
    for domain, table, count in snapshots:
        existing = db.query(SopSourceSnapshot).filter(
            SopSourceSnapshot.domain == domain,
            SopSourceSnapshot.batch_id == BATCH_ID,
        ).first()
        if existing:
            continue
        db.add(SopSourceSnapshot(
            domain=domain,
            source_system="seed-demo",
            source_table=table,
            batch_id=BATCH_ID,
            snapshot_at=SNAPSHOT_AT,
            max_business_date=date(2026, 3, 1),
            record_count=count,
            status="completed",
            details_json={"description": "样例演示数据，来自 S&OP基础数据及报表.xlsx"},
        ))
    db.flush()
    print(f"  ✅ 数据源快照: {len(snapshots)} 条")


def main():
    if not EXCEL_PATH.exists():
        print(f"❌ Excel 文件不存在: {EXCEL_PATH}")
        sys.exit(1)

    print("📦 S&OP 样例数据种子")
    print(f"   Excel: {EXCEL_PATH}")
    print(f"   SPU: {SPU_CODE} {SPU_NAME}")
    print(f"   Batch: {BATCH_ID}")
    print()

    # 初始化表结构
    init_sop_tables()

    db = SessionLocal()
    try:
        print("[1/4] 创建 SPU 主数据...")
        seed_spu(db)

        print("[2/4] 导入历史出库/激活数据...")
        sales_count, activation_count = seed_historical_data(db)

        print("[3/4] 导入分渠道预测数据...")
        forecast_count = seed_channel_forecasts(db)

        print("[4/4] 创建数据源快照...")
        seed_source_snapshots(db, sales_count, activation_count, forecast_count)

        db.commit()
        print()
        print("✅ 全部完成！前端刷新即可看到样例数据。")
        print(f"   总计: {sales_count + activation_count + forecast_count} 条业务数据")

    except Exception as e:
        db.rollback()
        print(f"\n❌ 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
