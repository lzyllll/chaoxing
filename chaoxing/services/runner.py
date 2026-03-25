# -*- coding: utf-8 -*-
import enum
import threading
import time
import traceback
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from queue import PriorityQueue, ShutDown
from threading import RLock
from typing import Any, Callable

from tqdm import tqdm

from chaoxing.core.base import Account, Chaoxing, StudyResult
from chaoxing.core.exceptions import InputFormatError, LoginError
from chaoxing.core.logger import logger
from chaoxing.processors.live import Live
from chaoxing.processors.live_process import LiveProcessor
from chaoxing.services.answer import Tiku
from chaoxing.services.notification import Notification


class ChapterResult(enum.Enum):
    SUCCESS = 0
    ERROR = 1
    NOT_OPEN = 2
    PENDING = 3


PromptFunc = Callable[[str], str]


def log_error(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except BaseException as e:
            logger.error(f"Error in thread {threading.current_thread().name}: {e}")
            traceback.print_exception(type(e), e, e.__traceback__)
            raise

    return wrapper


def sanitize_common_config(common_config: dict[str, Any]) -> dict[str, Any]:
    common_config = dict(common_config)
    common_config["speed"] = min(2.0, max(1.0, common_config.get("speed", 1.0)))
    common_config["jobs"] = int(common_config.get("jobs") or 4)
    common_config["notopen_action"] = common_config.get("notopen_action", "retry")
    return common_config


def sanitize_tiku_config(tiku_config: dict[str, Any]) -> dict[str, Any]:
    payload = dict(tiku_config)
    for key in ("delay", "cover_rate"):
        if key not in payload:
            continue
        try:
            payload[key] = float(payload[key])
        except (TypeError, ValueError):
            if key == "delay":
                payload[key] = 0.0
            elif key == "cover_rate":
                payload[key] = 0.8
    return payload


def init_chaoxing(
    common_config: dict[str, Any],
    tiku_config: dict[str, Any],
    prompt: PromptFunc = input,
    **kwargs: Any,
) -> Chaoxing:
    """初始化超星实例。"""
    tiku_config = sanitize_tiku_config(tiku_config)
    username = common_config.get("username", "")
    password = common_config.get("password", "")
    use_cookies = common_config.get("use_cookies", False)

    if (not username or not password) and not use_cookies:
        username = prompt("请输入你的手机号, 按回车确认\n手机号:")
        password = prompt("请输入你的密码, 按回车确认\n密码:")

    account = Account(username, password)

    tiku = Tiku()
    tiku.config_set(tiku_config)
    tiku = tiku.get_tiku_from_config()
    tiku.init_tiku()

    provider = tiku_config.get("provider", "")
    if provider in ["AI", "SiliconFlow"]:
        check_connection = tiku_config.get("check_llm_connection", "true").lower() == "true"
        if check_connection:
            logger.info(f"正在验证大模型配置 (provider={provider})...")
            if not tiku.check_llm_connection():
                logger.error("大模型连接检查失败")
                choice = prompt("大模型连接检查失败，无法准确答题，是否继续运行？(Y/n): ").strip().lower()
                if choice not in ("", "y", "yes"):
                    raise RuntimeError("用户取消运行")
                logger.info("用户选择继续运行...")

    query_delay = tiku_config.get("delay", 0)
    runtime_kwargs = dict(kwargs)
    runtime_kwargs.setdefault("query_delay", query_delay)
    return Chaoxing(account=account, tiku=tiku, **runtime_kwargs)


def process_job(
    chaoxing: Chaoxing,
    course: dict[str, Any],
    point: dict[str, Any],
    job: dict[str, Any],
    job_info: dict[str, Any],
    speed: float,
) -> StudyResult:
    """处理单个任务点。"""
    chaoxing.emit_event(
        "job_started",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "chapterId": point.get("id"),
            "chapterTitle": point.get("title"),
            "jobId": job.get("jobid"),
            "jobName": job.get("name"),
            "jobType": job.get("type"),
        },
    )

    if job["type"] == "video":
        logger.trace(f"识别到视频任务, 任务章节: {course['title']} 任务ID: {job['jobid']}")
        chaoxing.emit_log("info", f"开始处理视频任务：{job.get('name')}", {"jobId": job.get("jobid")})
        video_result = chaoxing.study_video(
            course,
            job,
            job_info,
            _speed=speed,
            _type="Video",
            _chapter_title=point.get("title", ""),
        )
        if video_result.is_failure():
            logger.warning("当前任务非视频任务, 正在尝试音频任务解码")
            video_result = chaoxing.study_video(
                course,
                job,
                job_info,
                _speed=speed,
                _type="Audio",
                _chapter_title=point.get("title", ""),
            )
        if video_result.is_failure():
            logger.warning(
                f"出现异常任务 -> 任务章节: {course['title']} 任务ID: {job['jobid']}, 已跳过"
            )
            chaoxing.emit_log("warning", f"视频任务处理失败：{job.get('name')}", {"jobId": job.get("jobid")})
            chaoxing.emit_event(
                "job_failed",
                {
                    "courseId": course.get("courseId"),
                    "courseTitle": course.get("title"),
                    "chapterId": point.get("id"),
                    "chapterTitle": point.get("title"),
                    "jobId": job.get("jobid"),
                    "jobName": job.get("name"),
                    "jobType": job.get("type"),
                },
            )
        else:
            chaoxing.emit_event(
                "job_completed",
                {
                    "courseId": course.get("courseId"),
                    "courseTitle": course.get("title"),
                    "chapterId": point.get("id"),
                    "chapterTitle": point.get("title"),
                    "jobId": job.get("jobid"),
                    "jobName": job.get("name"),
                    "jobType": job.get("type"),
                },
            )
        return video_result

    if job["type"] == "document":
        logger.trace(f"识别到文档任务, 任务章节: {course['title']} 任务ID: {job['jobid']}")
        result = chaoxing.study_document(course, job)
        chaoxing.emit_event(
            "job_completed" if result.is_success() else "job_failed",
            {
                "courseId": course.get("courseId"),
                "courseTitle": course.get("title"),
                "chapterId": point.get("id"),
                "chapterTitle": point.get("title"),
                "jobId": job.get("jobid"),
                "jobName": job.get("name"),
                "jobType": job.get("type"),
            },
        )
        return result

    if job["type"] == "workid":
        logger.trace(f"识别到章节检测任务, 任务章节: {course['title']}")
        result = chaoxing.study_work(course, job, job_info, _chapter_title=point.get("title", ""))
        chaoxing.emit_event(
            "job_completed" if result.is_success() else "job_failed",
            {
                "courseId": course.get("courseId"),
                "courseTitle": course.get("title"),
                "chapterId": point.get("id"),
                "chapterTitle": point.get("title"),
                "jobId": job.get("jobid"),
                "jobName": job.get("name"),
                "jobType": job.get("type"),
            },
        )
        return result

    if job["type"] == "read":
        logger.trace(f"识别到阅读任务, 任务章节: {course['title']}")
        result = chaoxing.study_read(course, job, job_info)
        chaoxing.emit_event(
            "job_completed" if result.is_success() else "job_failed",
            {
                "courseId": course.get("courseId"),
                "courseTitle": course.get("title"),
                "chapterId": point.get("id"),
                "chapterTitle": point.get("title"),
                "jobId": job.get("jobid"),
                "jobName": job.get("name"),
                "jobType": job.get("type"),
            },
        )
        return result

    if job["type"] == "live":
        logger.trace(f"识别到直播任务, 任务章节: {course['title']} 任务ID: {job['jobid']}")
        try:
            defaults = {
                "userid": chaoxing.get_uid(),
                "clazzId": course.get("clazzId"),
                "knowledgeid": job_info.get("knowledgeid"),
            }
            live = Live(
                attachment=job,
                defaults=defaults,
                course_id=course.get("courseId"),
                session=chaoxing.session,
            )
            thread = threading.Thread(
                target=LiveProcessor.run_live,
                args=(live, speed),
                daemon=True,
            )
            thread.start()
            thread.join()
            chaoxing.emit_event(
                "job_completed",
                {
                    "courseId": course.get("courseId"),
                    "courseTitle": course.get("title"),
                    "chapterId": point.get("id"),
                    "chapterTitle": point.get("title"),
                    "jobId": job.get("jobid"),
                    "jobName": job.get("name"),
                    "jobType": job.get("type"),
                },
            )
            return StudyResult.SUCCESS
        except Exception as e:
            logger.error(f"处理直播任务时出错: {str(e)}")
            chaoxing.emit_log("error", f"直播任务处理失败：{e}", {"jobId": job.get("jobid")})
            chaoxing.emit_event(
                "job_failed",
                {
                    "courseId": course.get("courseId"),
                    "courseTitle": course.get("title"),
                    "chapterId": point.get("id"),
                    "chapterTitle": point.get("title"),
                    "jobId": job.get("jobid"),
                    "jobName": job.get("name"),
                    "jobType": job.get("type"),
                },
            )
            return StudyResult.ERROR

    logger.error(f"未知任务类型: {job['type']}")
    chaoxing.emit_log("error", f"未知任务类型：{job.get('type')}", {"jobId": job.get("jobid")})
    return StudyResult.ERROR


@dataclass(order=True)
class ChapterTask:
    index: int
    point: dict[str, Any]
    result: ChapterResult = ChapterResult.PENDING
    tries: int = 0


class JobProcessor:
    def __init__(
        self,
        chaoxing: Chaoxing,
        course: dict[str, Any],
        tasks: list[ChapterTask],
        config: dict[str, Any],
    ):
        self.chaoxing = chaoxing
        self.course = course
        self.speed = config["speed"]
        self.max_tries = 5
        self.tasks = tasks
        self.failed_tasks: list[ChapterTask] = []
        self.task_queue: PriorityQueue[ChapterTask] = PriorityQueue()
        self.retry_queue: PriorityQueue[ChapterTask] = PriorityQueue()
        self.wait_queue: PriorityQueue[ChapterTask] = PriorityQueue()
        self.threads: list[threading.Thread] = []
        self.worker_num = config["jobs"]
        self.config = config

    def run(self) -> None:
        for task in self.tasks:
            self.task_queue.put(task)

        for _ in range(self.worker_num):
            thread = threading.Thread(target=self.worker_thread, daemon=True)
            self.threads.append(thread)
            thread.start()

        threading.Thread(target=self.retry_thread, daemon=True).start()

        self.task_queue.join()
        time.sleep(0.5)
        self.task_queue.shutdown()

    @log_error
    def worker_thread(self) -> None:
        tqdm.set_lock(tqdm.get_lock())
        while True:
            try:
                task = self.task_queue.get()
            except ShutDown:
                logger.info("Queue shut down")
                return

            task.result = process_chapter(self.chaoxing, self.course, task.point, self.speed)

            match task.result:
                case ChapterResult.SUCCESS:
                    logger.debug("Task success: {}", task.point["title"])
                    self.task_queue.task_done()
                    logger.debug(f"unfinished task: {self.task_queue.unfinished_tasks}")

                case ChapterResult.NOT_OPEN:
                    if self.config["notopen_action"] == "continue":
                        logger.warning("章节未开启: {}, 正在跳过", task.point["title"])
                        self.task_queue.task_done()
                        continue

                    if task.tries >= self.max_tries:
                        logger.error(
                            "章节未开启: {} 可能由于上一章节的章节检测未完成, 也可能由于该章节因为时效已关闭，"
                            "请手动检查完成并提交再重试。或者在配置中配置(自动跳过关闭章节/开启题库并启用提交)",
                            task.point["title"],
                        )
                        self.task_queue.task_done()
                        continue

                    self.retry_queue.put(task)

                case ChapterResult.ERROR:
                    task.tries += 1
                    logger.warning(
                        "Retrying task {} ({}/{} attempts)",
                        task.point["title"],
                        task.tries,
                        self.max_tries,
                    )
                    if task.tries >= self.max_tries:
                        logger.error("Max retries reached for task: {}", task.point["title"])
                        self.failed_tasks.append(task)
                        self.task_queue.task_done()
                        continue
                    self.retry_queue.put(task)

                case _:
                    logger.error("Invalid task state {} for task {}", task.result, task.point["title"])
                    self.failed_tasks.append(task)
                    self.task_queue.task_done()

    @log_error
    def retry_thread(self) -> None:
        try:
            while True:
                task = self.retry_queue.get()
                self.task_queue.put(task)
                self.task_queue.task_done()
                time.sleep(1)
        except ShutDown:
            pass


def process_chapter(
    chaoxing: Chaoxing,
    course: dict[str, Any],
    point: dict[str, Any],
    speed: float,
) -> ChapterResult:
    """处理单个章节。"""
    logger.info(f'当前章节: {point["title"]}')
    chaoxing.emit_event(
        "chapter_started",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "chapterId": point.get("id"),
            "chapterTitle": point.get("title"),
            "hasFinished": point.get("has_finished", False),
        },
    )
    chaoxing.emit_log("info", f"开始处理章节：{point.get('title')}")
    if point["has_finished"]:
        logger.info(f'章节：{point["title"]} 已完成所有任务点')
        chaoxing.emit_event(
            "chapter_completed",
            {
                "courseId": course.get("courseId"),
                "courseTitle": course.get("title"),
                "chapterId": point.get("id"),
                "chapterTitle": point.get("title"),
                "alreadyFinished": True,
            },
        )
        return ChapterResult.SUCCESS

    chaoxing.rate_limiter.limit_rate(random_time=True, random_min=0, random_max=0.2)
    jobs, job_info = chaoxing.get_job_list(course, point)

    if job_info.get("notOpen", False):
        chaoxing.emit_event(
            "chapter_not_open",
            {
                "courseId": course.get("courseId"),
                "courseTitle": course.get("title"),
                "chapterId": point.get("id"),
                "chapterTitle": point.get("title"),
            },
        )
        return ChapterResult.NOT_OPEN

    job_results: list[StudyResult] = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for result in executor.map(
            lambda job: process_job(chaoxing, course, point, job, job_info, speed),
            jobs,
        ):
            job_results.append(result)

    for result in job_results:
        if result.is_failure():
            chaoxing.emit_event(
                "chapter_failed",
                {
                    "courseId": course.get("courseId"),
                    "courseTitle": course.get("title"),
                    "chapterId": point.get("id"),
                    "chapterTitle": point.get("title"),
                },
            )
            return ChapterResult.ERROR

    chaoxing.emit_event(
        "chapter_completed",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "chapterId": point.get("id"),
            "chapterTitle": point.get("title"),
            "alreadyFinished": False,
        },
    )
    return ChapterResult.SUCCESS


def process_course(
    chaoxing: Chaoxing,
    course: dict[str, Any],
    config: dict[str, Any],
    *,
    point_list: dict[str, Any] | None = None,
) -> None:
    """处理单个课程。"""
    logger.info(f"开始学习课程: {course['title']}")
    chaoxing.emit_event(
        "course_started",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "clazzId": course.get("clazzId"),
        },
    )
    chaoxing.emit_log("info", f"开始学习课程：{course.get('title')}")
    point_list = point_list or chaoxing.get_course_point(course["courseId"], course["clazzId"], course["cpi"])

    old_format_sizeof = tqdm.format_sizeof
    tqdm.format_sizeof = format_time
    tqdm.set_lock(RLock())

    tasks: list[ChapterTask] = []
    for index, point in enumerate(point_list["points"]):
        tasks.append(ChapterTask(point=point, index=index))
    chaoxing.emit_event(
        "course_points_loaded",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "totalPoints": len(tasks),
        },
    )
    chaoxing.emit_event(
        "course_chapters_loaded",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "chapters": [
                {
                    "chapterId": point.get("id"),
                    "chapterTitle": point.get("title"),
                    "hasFinished": point.get("has_finished", False),
                }
                for point in point_list["points"]
            ],
        },
    )

    processor = JobProcessor(chaoxing, course, tasks, config)
    processor.run()
    tqdm.format_sizeof = old_format_sizeof
    if processor.failed_tasks:
        failed_titles = [task.point.get("title", "") for task in processor.failed_tasks]
        chaoxing.emit_event(
            "course_failed",
            {
                "courseId": course.get("courseId"),
                "courseTitle": course.get("title"),
                "failedChapters": failed_titles,
            },
        )
        raise RuntimeError(f"课程 {course.get('title')} 存在失败章节：{'、'.join(failed_titles)}")
    chaoxing.emit_event(
        "course_completed",
        {
            "courseId": course.get("courseId"),
            "courseTitle": course.get("title"),
            "totalPoints": len(tasks),
        },
    )


def filter_courses(
    all_course: list[dict[str, Any]],
    course_list: list[str] | None,
    prompt: PromptFunc = input,
) -> list[dict[str, Any]]:
    """过滤要学习的课程。"""
    if not course_list:
        print("*" * 10 + "课程列表" + "*" * 10)
        for course in all_course:
            print(f"ID: {course['courseId']} 课程名: {course['title']}")
        print("*" * 28)
        try:
            course_list = prompt(
                "请输入想要学习的课程列表,以逗号分隔,例: 2151141,189191,198198\n"
            ).split(",")
        except Exception as e:
            raise InputFormatError("输入格式错误") from e

    course_task: list[dict[str, Any]] = []
    course_ids: list[str] = []
    for course in all_course:
        if course["courseId"] in course_list and course["courseId"] not in course_ids:
            course_task.append(course)
            course_ids.append(course["courseId"])

    if not course_task:
        course_task = all_course

    return course_task


def format_time(num, suffix="", divisor=""):
    total_time = round(num)
    sec = total_time % 60
    mins = (total_time % 3600) // 60
    hrs = total_time // 3600

    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{sec:02d}"

    return f"{mins:02d}:{sec:02d}"


def run_study(
    common_config: dict[str, Any],
    tiku_config: dict[str, Any],
    notification_config: dict[str, Any],
    prompt: PromptFunc = input,
) -> None:
    """运行完整刷课流程。"""
    common_config = sanitize_common_config(common_config)
    notification = Notification()

    try:
        chaoxing = init_chaoxing(common_config, tiku_config, prompt=prompt)

        notification.config_set(notification_config)
        notification = notification.get_notification_from_config()
        notification.init_notification()

        login_state = chaoxing.login(login_with_cookies=common_config.get("use_cookies", False))
        if not login_state["status"]:
            raise LoginError(login_state["msg"])

        all_course = chaoxing.get_course_list()
        course_task = filter_courses(all_course, common_config.get("course_list"), prompt=prompt)

        logger.info(f"课程列表过滤完毕, 当前课程任务数量: {len(course_task)}")
        for course in course_task:
            process_course(chaoxing, course, common_config)

        logger.info("所有课程学习任务已完成")
        notification.send("chaoxing : 所有课程学习任务已完成")
    except BaseException as e:
        try:
            notification.send(f"chaoxing : 出现错误 {type(e).__name__}: {e}\n{traceback.format_exc()}")
        except Exception:
            pass
        raise
