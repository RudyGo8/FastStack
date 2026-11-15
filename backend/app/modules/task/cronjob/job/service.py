from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.core.ap_scheduler import SchedulerUtil
from app.core.base_schema import AuthSchema, PageResultSchema
from app.core.exceptions import CustomException
from app.utils.common_util import search_to_dict

from .crud import JobCRUD
from .schema import (
    JobOutSchema,
    JobQueryParam,
    SchedulerJobModifySchema,
    SchedulerJobSchema,
    SchedulerStatusSchema,
)


class JobService:
    """调度器监控模块服务层"""

    def __init__(self, auth: AuthSchema, db: AsyncSession) -> None:
        self.auth = auth
        self.db = db

    async def get_job_log_detail(self, id: int) -> JobOutSchema:
        obj = await JobCRUD(self.auth, self.db).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="执行日志不存在")
        return JobOutSchema.model_validate(obj)

    async def get_job_log_list(
        self,
        search: JobQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[JobOutSchema]:
        if order_by is None:
            order_by = [{"created_time": "desc"}]
        obj_list = await JobCRUD(self.auth, self.db).get_obj_list_crud(search=search_to_dict(search, {}), order_by=order_by)
        return [JobOutSchema.model_validate(obj) for obj in obj_list]

    async def get_job_log_page(
        self,
        page_no: int,
        page_size: int,
        search: JobQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> PageResultSchema[JobOutSchema]:
        offset = (page_no - 1) * page_size
        ob = order_by or [{"created_time": "desc"}]
        return await JobCRUD(self.auth, self.db).page(
            offset=offset,
            limit=page_size,
            order_by=ob,
            search=search_to_dict(search, {}),
            out_schema=JobOutSchema,
        )

    async def delete_job_log(self, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        await JobCRUD(self.auth, self.db).delete_obj_crud(ids=ids)

    async def clear_job_log(self) -> None:
        await JobCRUD(self.auth, self.db).clear_obj_crud()

    # APScheduler 状态常量: 0=停止, 1=运行中, 2=暂停
    _SCHEDULER_STATE_MAP: dict[int, str] = {0: "停止", 1: "运行中", 2: "暂停"}

    @staticmethod
    def get_scheduler_status() -> SchedulerStatusSchema:
        state = SchedulerUtil.get_scheduler_state()
        is_running = SchedulerUtil.is_running()
        jobs = SchedulerUtil.get_jobs()
        # 可观测性（t15）：把"已注册但当前不可执行"的任务显式打出并计数，
        # 运维不必逐个点开才知道开关调整/处理器改名后哪些任务静默失效
        unschedulable = SchedulerUtil.log_unschedulable_jobs(context="调度器状态查询")
        return SchedulerStatusSchema(
            status=JobService._SCHEDULER_STATE_MAP.get(state, "未知"),
            is_running=is_running,
            job_count=len(jobs),
            code_exec_enabled=settings.SCHEDULER_ALLOW_CODE_EXEC,
            unschedulable_count=len(unschedulable),
        )

    @staticmethod
    def get_scheduler_jobs() -> list[SchedulerJobSchema]:
        jobs = SchedulerUtil.get_jobs()
        items: list[SchedulerJobSchema] = []
        for job in jobs:
            schedulable, reason = SchedulerUtil.describe_schedulability(SchedulerUtil.job_code_block(job))
            items.append(
                SchedulerJobSchema(
                    id=job.id,
                    name=job.name,
                    trigger=str(job.trigger),
                    # pending/未排程任务没有 next_run_time 属性（APScheduler 只在真正排程后设置），必须 getattr 兜底
                    next_run_time=str(job.next_run_time) if getattr(job, "next_run_time", None) else None,
                    status=SchedulerUtil.get_job_status(job_id=job.id),
                    schedulable=schedulable,
                    unschedulable_reason=None if schedulable else reason,
                ),
            )
        return items

    # ─── 调度器与任务运维（controller 唯一入口，禁止直调 SchedulerUtil）───

    @staticmethod
    def _ensure_job_exists(job_id: str) -> None:
        if not SchedulerUtil.get_job(job_id=job_id):
            raise CustomException(msg=f"任务 {job_id} 不存在或已从调度器移除")

    @staticmethod
    async def start_scheduler() -> None:
        await SchedulerUtil.start()

    @staticmethod
    def pause_scheduler() -> None:
        SchedulerUtil.pause()

    @staticmethod
    def resume_scheduler() -> None:
        SchedulerUtil.resume()

    @staticmethod
    async def shutdown_scheduler() -> None:
        await SchedulerUtil.shutdown()

    @staticmethod
    def clear_scheduler_jobs() -> None:
        SchedulerUtil.clear_jobs()

    @staticmethod
    def get_scheduler_console() -> str:
        return SchedulerUtil.print_jobs()

    @staticmethod
    def pause_job(job_id: str) -> None:
        JobService._ensure_job_exists(job_id=job_id)
        SchedulerUtil.pause_job(job_id=job_id)

    @staticmethod
    def resume_job(job_id: str) -> None:
        JobService._ensure_job_exists(job_id=job_id)
        SchedulerUtil.resume_job(job_id=job_id)

    @staticmethod
    def run_job_now(job_id: str) -> None:
        JobService._ensure_job_exists(job_id=job_id)
        SchedulerUtil.run_job_now(job_id=job_id)

    @staticmethod
    def modify_job(job_id: str, data: SchedulerJobModifySchema) -> None:
        JobService._ensure_job_exists(job_id=job_id)
        changes = data.to_changes()
        if not changes:
            raise CustomException(msg="没有需要修改的任务属性")
        SchedulerUtil.modify_job(job_id=job_id, **changes)

    @staticmethod
    def remove_job(job_id: str) -> None:
        JobService._ensure_job_exists(job_id=job_id)
        SchedulerUtil.remove_job(job_id=job_id)
