"""Worker thread lấy job từ bảng extractions (queued) và chạy handler."""
import logging
import threading
from typing import Callable

from ..storage.extraction_repository import ExtractionRepository

log = logging.getLogger(__name__)


class JobRunner:
    def __init__(self, repo: ExtractionRepository, handler: Callable[[str], None],
                 worker_count: int, poll_seconds: float):
        self.repo = repo
        self.handler = handler
        self.worker_count = worker_count
        self.poll_seconds = poll_seconds
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._started = False

    def start(self) -> None:
        """Đưa job running dở (service tắt giữa chừng) về queued rồi chạy các daemon thread."""
        if self._started:
            return
        self._started = True
        requeued = self.repo.requeue_running()
        log.info("Đã requeue %d job đang running dở", requeued)
        for i in range(self.worker_count):
            t = threading.Thread(target=self._loop, name=f"ocr-worker-{i}", daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self, timeout: float = 10) -> None:
        """Báo dừng và chờ các thread kết thúc."""
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout)
        self._threads = []
        self._started = False

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                job_id = self.repo.claim_next()
            except Exception:
                # Lỗi DB tạm thời: ghi log rồi chờ poll tiếp, không để thread chết
                log.exception("claim_next lỗi")
                self._stop_event.wait(self.poll_seconds)
                continue
            if job_id is None:
                self._stop_event.wait(self.poll_seconds)
                continue
            self._run_one(job_id)

    def _run_one(self, job_id: str) -> None:
        try:
            self.handler(job_id)
        except Exception as e:
            log.exception("Job %s lỗi", job_id)
            try:
                self.repo.mark_failed(job_id, f"{type(e).__name__}: {e}")
            except Exception:
                log.exception("mark_failed lỗi cho job %s", job_id)
