"""S&OP 自动化夜间快照调度器 (Nightly Snapshot Scheduler).

负责在每天夜间（如 23:00 / 00:00，数据 T-1 业务切日点）自动触发全量活跃 SPU
的不可变会前数据快照固化任务。
"""

import asyncio
from datetime import date, datetime, timedelta

from app.modules.sop.database import SessionLocal
from app.modules.sop.domain.snapshot_service import SopSnapshotService
from app.modules.sop.utils.log import get_logger

logger = get_logger(__name__)

_scheduler_task: asyncio.Task | None = None
_scheduler_running: bool = False


async def run_nightly_snapshot_job() -> None:
    """执行单次夜间快照作业（数据截至昨天 T-1）."""
    logger.info("start_nightly_snapshot_job")
    db = SessionLocal()
    try:
        service = SopSnapshotService(db)
        yesterday = date.today() - timedelta(days=1)
        version = f"SNAP_{yesterday.strftime('%Y%m%d')}_T1"
        res = service.generate_nightly_snapshots(as_of_date=yesterday, report_version=version)
        logger.info(
            "finish_nightly_snapshot_job",
            as_of_date=str(yesterday),
            report_version=version,
            count=res.generated_count,
        )
    except Exception as exc:
        logger.error("nightly_snapshot_job_failed", error=str(exc))
    finally:
        db.close()


async def snapshot_scheduler_loop(target_hour: int = 23, target_minute: int = 0) -> None:
    """定时循环：每日在指定时间执行夜间快照."""
    global _scheduler_running
    _scheduler_running = True
    logger.info("snapshot_scheduler_loop_started", target_hour=target_hour, target_minute=target_minute)

    while _scheduler_running:
        try:
            now = datetime.now()
            # 计算下一次运行时间
            target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)

            sleep_seconds = (target_time - now).total_seconds()
            logger.info("snapshot_scheduler_next_run", target_time=str(target_time), wait_seconds=int(sleep_seconds))

            # 分段 sleep，便于响应退出信号
            while sleep_seconds > 0 and _scheduler_running:
                chunk = min(sleep_seconds, 60.0)
                await asyncio.sleep(chunk)
                sleep_seconds -= chunk

            if _scheduler_running:
                await run_nightly_snapshot_job()
        except asyncio.CancelledError:
            logger.info("snapshot_scheduler_loop_cancelled")
            break
        except Exception as exc:
            logger.error("snapshot_scheduler_error", error=str(exc))
            await asyncio.sleep(60.0)

    _scheduler_running = False
    logger.info("snapshot_scheduler_loop_stopped")


def start_snapshot_scheduler(target_hour: int = 23, target_minute: int = 0) -> None:
    """启动夜间快照调度后台任务."""
    global _scheduler_task
    try:
        loop = asyncio.get_running_loop()
        if _scheduler_task is None or _scheduler_task.done():
            _scheduler_task = loop.create_task(snapshot_scheduler_loop(target_hour, target_minute))
    except RuntimeError:
        # 非 async 上下文时，可在后台线程中运行
        pass


def stop_snapshot_scheduler() -> None:
    """停止夜间快照调度器."""
    global _scheduler_running, _scheduler_task
    _scheduler_running = False
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
