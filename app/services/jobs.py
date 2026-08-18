

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    id: str
    name: str
    emoji: str
    reward: int
    xp: int
    cooldown: int
    required_level: int = 1


JOBS = {
    "worker": Job(
        id="worker",
        name="کارگر",
        emoji="👷",
        reward=100,
        xp=10,
        cooldown=30,
        required_level=1,
    ),
    "driver": Job(
        id="driver",
        name="راننده",
        emoji="🚗",
        reward=180,
        xp=18,
        cooldown=45,
        required_level=2,
    ),
    "programmer": Job(
        id="programmer",
        name="برنامه‌نویس",
        emoji="💻",
        reward=350,
        xp=35,
        cooldown=90,
        required_level=5,
    ),
}


def get_job(job_id: str) -> Job | None:
    return JOBS.get(job_id)


def get_all_jobs() -> dict[str, Job]:
    return JOBS