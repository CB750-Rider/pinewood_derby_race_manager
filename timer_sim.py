"""
timer_sim.py

simulates the timer hardware for debugging of the pinewood applications.

Copyright [2019] [Lee R. Burchett]

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import sys
import socket
import numpy as np
import select
import time
import tkinter as tk
from queue import Queue
from threading import Thread, Lock
from typing import Iterable

infile = "lane_hosts.csv"
ready_msg = "<Ready to Race.>".encode('utf-8')
go_msg = "<GO!>".encode('utf-8')
reset_msg = "<Reset recieved.>".encode('utf-8')
time_prefix = "<Track count:".encode('utf-8')
time_suffix = ">".encode('utf-8')
stringlen = 64
race_ready = False
running_race = True
mutex = Lock()


class Lane:
    def __init__(self, idx):
        self.number = idx + 1
        self.index = idx
        self.reporting = None
        self.connection = None
        self.address = None
        self.queue = Queue(maxsize=2)
        self.host = ''
        self.port = ''
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.check_button = None
        self.drop_button = None

    def add_lane_to_window(self, parent: tk.Widget):
        self.reporting = tk.BooleanVar()
        self.reporting.set(True)
        frame = tk.Frame(parent)
        frame.pack()
        self.check_button = tk.Checkbutton(frame, text="Lane {}".format(self.number)
                                           , variable=self.reporting)
        self.check_button.pack(side=tk.LEFT)
        self.drop_button = tk.Button(frame, text="Drop", command=self.drop_connection)
        self.drop_button.pack(side=tk.RIGHT)

    def drop_connection(self):
        if self.drop_button['text'] == 'Drop':
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()
            self.drop_button['text'] = 'Connect'
        else:
            self.start_socket()

    def start_socket(self):
        Thread(target=self._await_connection, daemon=True).start()

    def _await_connection(self):
        print("Setting up connection to {}:{}".format(self.host, self.port))
        while True:
            try:
                self._socket.bind((self.host, self.port))
            except OSError:
                print(f"Unable to connect to {self.host}:{self.port}. It is probably already in use. Retry in 5 seconds.")
                time.sleep(5.0)
            else:
                break
        self._socket.listen(2)
        print("Awaiting connection on {}:{}".format(self.host, self.port))
        new_conn, new_addr = self._socket.accept()
        mutex.acquire()
        self.queue.put(new_conn)
        self.queue.put(new_addr)
        print("Connection from {} established.".format(self.host))
        self.queue.task_done()
        mutex.release()

    def close_socket(self):
        try:
            self.connection.close()
        except AttributeError:
            pass

    def get_connections(self):
        if self.queue.full():
            self.connection = self.queue.get()
            self.address = self.queue.get()
        return self.connection, self.address

    def shutdown_connection(self):
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except AttributeError:
            pass

    def close_connection(self):
        try:
            self.connection.close()
        except AttributeError:
            pass


class MainWindow:
    def __init__(self, lanes: Iterable[Lane]):
        self.window = tk.Tk()
        for lane in lanes:
            lane.add_lane_to_window(self.window)
            lane.start_socket()

        self.reset_button = tk.Button(self.window, text="Reset", command=not_ready)
        self.reset_button.pack()
        self.racing_button = tk.Button(self.window, text="Racing", command=self.toggle_racing)
        self.racing_button.pack()
        self.window.protocol("WM_DELETE_WINDOW", close_manager)
        self.window.update()

    def toggle_racing(self):
        global running_race
        if self.racing_button.config('text')[-1] == "Racing":
            self.racing_button.config(text="On Hold")
            running_race = False
        else:
            self.racing_button.config(text="Racing")
            running_race = True

    def update(self):
        self.window.update()
        self.window.update_idletasks()

    def activate_reset_button(self):
        self.reset_button.configure(command=race_reset)
        self.update()

    def deactivate_reset_button(self):
        self.reset_button.configure(command=not_ready)
        self.update()


def make_str(race_number):
    new_times = 12.0 + np.random.randn(4) / 10.0
    time_str = ["{:5.3f}".format(x) for x in new_times]
    time_str.insert(0, "{:5}".format(race_number))
    return ','.join(time_str), race_number + 1


def set_host_and_port(lanes: Iterable[Lane], infile: str):
    with open(infile) as fp:
        for line in fp:
            laneNumber, hostAddress, hostPort = line.split(',')
            li = int(laneNumber) - 1
            lanes[li].host = hostAddress
            lanes[li].port = int(hostPort)
    return lanes


def race_reset():
    global race_ready, the_lanes
    for lane in the_lanes:
        lane.connection.sendall(reset_msg)
        lane.connection.sendall(ready_msg)
    race_ready = True


def time_msg():
    """Normally distributed random numbers around 4 seconds"""
    racer_time = np.random.randn() * 0.1 + 4.0
    "Convert to counts"
    print("Time = {}".format(racer_time))
    racer_time = np.array(racer_time * 2000.0).astype(np.int32)
    print("Counts = {}".format(racer_time))
    time_message = "{}".format(racer_time).encode('utf-8')
    return time_message


def not_ready():
    print("The connections are not ready yet!")


def run_race(lanes):
    for lane in lanes:
        lane.connection.sendall(go_msg)
    time.sleep(3)
    for idx, lane in enumerate(lanes):
        if lane.reporting.get():
            lane.connection.sendall(time_prefix + time_msg() + time_suffix)
        time.sleep(np.random.rand() / 2.0)


def close_manager():
    global end_program, the_lanes
    end_program = True
    for lane in the_lanes:
        lane.shutdown_connection()
    raise SystemExit


def get_connections():
    global the_lanes
    connections = []
    for lane in the_lanes:
        ca = lane.get_connections()
        if ca[0] is None:
            return None
        else:
            connections.append(ca[0])
    return connections


if __name__ == "__main__":
    #    global infile,host,port,race_ready
    the_lanes = [Lane(x) for x in range(4)]
    end_program = False
    prompt_reset = True

    if len(sys.argv) == 1:
        print("Using the hosts in {}.".format(infile))
        print("Pass a file name if you would like to use a different file.")
    elif len(sys.argv) == 2:
        infile = sys.argv[1]
    else:
        infile = sys.argv[1]
        print("Only the first argument is used")

    set_host_and_port(the_lanes, infile)

    window = MainWindow(the_lanes)

    while not end_program:

        conn = get_connections()

        if conn is not None:
            window.activate_reset_button()
            if not race_ready:
                ready_sockets, writy_sockets, _ = select.select(conn, conn, [], 5.0)
                for rs in ready_sockets:
                    data = rs.recv(64).decode('utf-8')
                    if 'reset' in data:
                        race_reset()

            if len(writy_sockets) < 4:
                print("A socket disconnected. We should restart")
                for lane in the_lanes:
                    lane.close_socket()
                connections_ready = False

            if race_ready and running_race:
                print("Running Race in 2 seconds.")
                time.sleep(2)
                run_race(the_lanes)
                race_ready = False

        window.update()


