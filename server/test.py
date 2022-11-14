from flask import Flask
from pkg_resources import iter_entry_points
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
def keep_alive():
    with app.app_context():
        sse.publish("\n\n", type="keepalive")


#print(dict((ep.name, ep) for ep in iter_entry_points('apscheduler.triggers')))
sched = BackgroundScheduler(daemon=True)
sched.start()
sched.add_job(keep_alive, 'interval', seconds=50)
