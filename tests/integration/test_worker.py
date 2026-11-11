from apps.api.db import db, now
from apps.api.auth.users import create_user
from worker.scout import scout_due


async def test_scout_tick_is_idempotent_and_respects_interval():
    u = create_user("w@x.io", "pw-pw-pw-pw", "web")
    db().execute("INSERT INTO saved_searches(user_id,q,category,skill,interval_min) VALUES (?,?,?,?,?)", (u["id"], "", "Web Development", "Celery", 240))
    t = now()
    first = await scout_due(t)
    assert list(first.values())[0] >= 0
    assert await scout_due(t + 60) == {}            # interval not elapsed: nothing runs
    again = await scout_due(t + 241 * 60)           # next tick: jobs already seen are not re-analysed
    assert all(v == 0 for v in again.values())
