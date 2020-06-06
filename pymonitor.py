import os, sys, time, subprocess

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class AppFileSystemHandler(FileSystemEventHandler):
    def __init__(self, fn):
        super().__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            self.restart()


process = None
command = ['echo', 'ok']


def kill_process():
    global process
    if process:
        process.kill()
        process.wait()
        process = None


def start_process():
    global process
    print("start process", command)
    process = subprocess.Popen(command,
                               stdin=sys.stdin,
                               stdout=sys.stdout,
                               stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()


def start_watch(path, callback):
    observer = Observer()
    observer.schedule(AppFileSystemHandler(restart_process),
                      path,
                      recursive=True)
    observer.start()
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        exit(0)
    if argv[0] != 'python3':
        argv.insert(0, 'python3')
    command = argv
    path = os.path.abspath('.')
    start_watch(path, None)
