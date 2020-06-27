"""
rm_gui.py

author: Dr. Lee Burchett

An application for creating a gui that managers of a Pinewood Derby can use
to set up and run a pinewood derby race.

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
import tkinter as tk
from race_event import Event, Heat, Racer
import argparse
import datetime
from tkinter import messagebox, filedialog
import os

description = "A Graphical Interface for setting up Pinewood Derby Races"

parser = argparse.ArgumentParser(description=description)
parser.add_argument('--event_file', help='A file with the event plan listed.',
                    default=None)
parser.add_argument('--save_action',
                    help="Define what to do when we close. Options are ask, overwrite, new_file, and no_save.",
                    default='ask')


def new_fname(old_name):
    now = datetime.datetime.now()
    try:
        fpath, basename = os.path.split(old_name)
    except TypeError:
        fpath = ""
        basename = "_plan.yaml"
    new_name = os.path.join(fpath, now.isoformat() + basename)
    idx = 0
    while os.path.isfile(new_name):
        new_name = os.path.join(fpath, now.isoformat() + '_' + str(idx) + basename)
        idx += 1
    return new_name


class RegistrationWindow:
    def __init__(self,
                 top: tk.Tk,
                 event_file: str = None):
        self.top = top

        self.in_file_name = event_file

        self.out_file_name = self.in_file_name

        self.event = Event(event_file=event_file, check_log_file=False)

        top.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.running = True

        self.create_menubar(top)

        self.racer_list = RacerList(self)

        self.heat_list = HeatList(self, self.racer_list)

        self.active_heat = None

        self.set_heat_pane()

        self.check_racer_pane()

    def create_menubar(self, top):
        menubar = tk.Menu(top)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open", command=self.open_event)
        filemenu.add_command(label="Save", command=self.save)
        filemenu.add_command(label="Save As", command=self.save_as)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.on_closing)

        menubar.add_cascade(label="File", menu=filemenu)

        top.config(menu=menubar)

    def open_event(self):
        self.in_file_name = filedialog.askopenfilename()
        self.event = Event(event_file=self.in_file_name, check_log_file=False)
        self.active_heat = None
        self.set_heat_pane()
        self.check_racer_pane()

    def save_as(self):
        self.out_file_name = filedialog.asksaveasfilename()
        self.save()

    def save(self):
        self.event.print_plan_yaml(self.out_file_name)

    def on_closing(self):
        self.running = False

    def mainloop(self):
        self.top.mainloop()
        return self.event, self.out_file_name

    def check_racer_pane(self):
        cur_idx = self.heat_list.get_selected_heat_index()
        if cur_idx != self.active_heat:
            self.active_heat = cur_idx
            self.racer_list.set_racers_from_heat(self.active_heat)
        if self.running:
            self.top.after(50, self.check_racer_pane)
        else:
            self.top.destroy()

    def set_heat_pane(self):
        self.heat_list.update_heat_list()

    def get_racer_by_index(self, index):
        heat_index = self.heat_list.get_selected_heat_index()
        if heat_index == -1:
            " This is the trickier part "
            for heat in self.event.heats:
                try:
                    racer = heat.racers[index]
                except IndexError:
                    index -= len(heat.racers)
                else:
                    return racer
        else:
            heat = self.event.heats[heat_index]
            return heat.racers[index]


class RacerDialog:
    def __init__(self,
                 parent: RegistrationWindow,
                 racer: Racer = None):
        self.top = parent.top
        self.event = parent.event
        self.parent = parent
        self._window = tk.Toplevel(parent.top)

        heat_idx = parent.heat_list.get_selected_heat_index()
        if heat_idx < 0:
            text = tk.Label(self._window, text="Please, select a heat before attempting to add a racer",
                            font=("Serif", 14))
            text.pack()
        else:
            self.heat = parent.event.heats[heat_idx]
            self.original_heat = self.heat
            if racer is None:  # Create a new racer
                racer = Racer(name="<Name>", rank="", heat_name=self.heat.name, heat_index=heat_idx)
                self.heat.add_racer(racer)
            self.racer = racer

            self.hidden_frame = tk.Frame(self._window)
            self.hidden_frame.pack(fill=tk.BOTH, expand=True)

            self.frame = tk.Frame(self._window)
            self.frame.pack(fill=tk.BOTH, expand=True)

            self.name_field = self.text_input("Name", 25, racer.name)
            self.rank_field = self.text_input("Rank", 25, racer.rank)

            self.car_weight = self.text_input("Car Weight", 15, "0.0")

            self.car_status = self.car_status_list(racer.car_status)

            text = tk.Label(self.frame, text="Notes")
            text.pack()
            self.notes = tk.Text(self.frame)
            self.notes.pack(expand=True, fill=tk.BOTH)

            bottom_frame = tk.Frame(self.frame)
            bottom_frame.pack(fill=tk.BOTH, expand=True)

            save = tk.Button(bottom_frame, text="Accept", command=self.accept)
            save.pack(side=tk.LEFT)

            option_frame = tk.Frame(bottom_frame)
            option_frame.pack(side=tk.LEFT, expand=True, fill=tk.X)
            heat_options = [heat.name for heat in self.event.heats[:-1]]
            self.heat_selector = self.option_input(option_frame,
                                                   "Select Heat",
                                                   heat_options)
            self.heat_selector.pack()

            cancel = tk.Button(bottom_frame, text="Cancel", command=self._window.destroy)
            cancel.pack(side=tk.RIGHT)

    def text_input(self, label, width, default):
        inner_frame = tk.Frame(self.frame)
        inner_frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(inner_frame, text=label, width=10)
        label.pack(side=tk.LEFT)

        entry = tk.Entry(inner_frame, width=width)
        entry.pack(side=tk.LEFT, pady=4, padx=4)
        entry.insert(0, default)

        return entry

    def option_input(self, parent, label, options):
        heat_string = tk.StringVar(parent)
        heat_string.set(label)
        option_menu = tk.OptionMenu(parent, heat_string, *options,
                                    command=self.set_heat)
        return option_menu

    def car_status_list(self, status_dict: dict):
        out_dict = status_dict.copy()

        idx = 0
        for key in status_dict.keys():
            if key == 'weight' or key == 'notes':
                continue
            frame = tk.Frame(self.frame)
            frame.pack(expand=True, anchor=tk.W)
            out_dict[key] = tk.IntVar(frame, value=status_dict[key])
            text = ' '.join(key.split('_'))
            gap = tk.Label(frame, width=9)
            gap.pack(side=tk.LEFT, expand=False)
            check_button = tk.Checkbutton(frame,
                                          text=text,
                                          variable=out_dict[key]
                                          )
            check_button.pack(padx=2, anchor=tk.W, side=tk.LEFT)
            idx += 1
        return out_dict

    def accept(self):
        self.racer.name = self.name_field.get()
        self.racer.rank = self.rank_field.get()
        try:
            self.racer.car_status['weight'] = float(self.car_weight.get())
        except ValueError:
            error_text = tk.Label(self.hidden_frame,
                                  text="Unable to convert the car weight to float.",
                                  fg='red',
                                  bg='black')
            return
        self.car_status['notes'] = self.notes.get(1.0, tk.END)
        for key in self.racer.car_status.keys():
            if key == 'notes' or key == 'weight':
                continue
            self.racer.car_status[key] = bool(self.car_status[key])

        if self.heat is not self.original_heat:
            self.original_heat.remove_racer(racer=self.racer)
            self.racer.heat_name = self.heat.name
            self.heat.add_racer(self.racer)

        heat_idx = self.event.heat_index(heat=self.original_heat)
        self.parent.racer_list.set_racers_from_heat(heat_idx)
        self._window.destroy()

    def set_heat(self, value):
        heat_idx = self.event.heat_index(heat_name=value)
        self.heat = self.event.heats[heat_idx]


class HeatDialog:
    def __init__(self,
                 parent: RegistrationWindow,
                 heat: Heat = None):
        self.top = parent.top
        self.parent = parent
        self.event = parent.event
        self._window = tk.Toplevel(self.top)

        if heat is None:
            heat = Heat(name="<Heat Name>")

        self.heat = heat
        self.hidden_frame = tk.Frame(self._window)
        self.hidden_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = tk.Frame(self._window)
        top_frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(top_frame, text="Heat Name")
        label.pack(side=tk.LEFT)
        self.name = tk.Entry(top_frame, width=50)
        self.name.pack(side=tk.LEFT)
        self.name.insert(0, heat.name)

        label = tk.Label(top_frame, text="Grade")
        label.pack(side=tk.LEFT)
        self.grade = tk.Entry(top_frame, width=2)
        self.grade.pack(side=tk.LEFT)
        self.grade.insert(0, str(heat.ability_rank))

        bottom_frame = tk.Frame(self._window)
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        button = tk.Button(bottom_frame, text="Accept", command=self.accept)
        button.pack(side=tk.LEFT)

        button = tk.Button(bottom_frame, text="Cancel", command=self._window.destroy)
        button.pack(side=tk.RIGHT)

    def add_error(self, message):
        label = tk.Label(self.hidden_frame, text=message, fg="red", bg="black")
        label.pack(fill=tk.BOTH, expand=True)

    def accept(self):
        name = self.name.get()
        grade = self.grade.get()
        self.heat.name = name
        self.heat.ability_rank = int(grade)

        for racer in self.heat.racers:
            racer.heat_name = name

        if self.event.heat_index(heat=self.heat) < 0:
            try:
                self.event.add_heat(self.heat)
            except ValueError:
                self.add_error("Unable to add a heat with this name. Is there another heat with the same name?")
                return

        self.event.sort_heats()

        self.parent.heat_list.update_heat_list()

        self._window.destroy()


class RacerList:
    def __init__(self, parent: RegistrationWindow):
        top = parent.top
        self.top = top
        self.parent = parent
        self._outer_frame = tk.Frame(top)
        self._outer_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        title = tk.Label(self._outer_frame, text="Racers", font=('Serif', 22))
        title.pack(expand=True, fill=tk.X)
        self.list_box = tk.Listbox(self._outer_frame, selectmode=tk.SINGLE,
                                   exportselection=False)
        self.list_box.pack(expand=True, fill=tk.BOTH)

        edit_button = tk.Button(self._outer_frame, text="Edit", font=('Serif', 16),
                                command=self.edit_selected_racer)
        edit_button.pack(fill=tk.X, pady=2)

        add_button = tk.Button(self._outer_frame, text="Add", font=('Serif', 16),
                               command=self.add_racer)
        add_button.pack(fill=tk.X, pady=2)

        delete_button = tk.Button(self._outer_frame, text="Delete", font=('Serif', 16),
                                  command=self.delete_selection)
        delete_button.pack(fill=tk.X, pady=16)

        self.set_racers_from_heat(-1)

    def add_racer(self):
        RacerDialog(self.parent)
        self.parent.check_racer_pane()

    def set_racers_from_heat(self, heat_idx):
        self.list_box.delete(0, tk.END)
        if heat_idx < 0:
            for heat in self.parent.event.heats[:-1]:
                self.add_racers_from_heat(heat)
        else:
            self.add_racers_from_heat(self.parent.event.heats[heat_idx])

    def add_racers_from_heat(self, heat: Heat):
        for racer in heat.racers:
            self.list_box.insert(tk.END, racer.name)

    def get_selected_racer_index(self):
        selected_value = self.list_box.curselection()
        if len(selected_value) > 0:
            return selected_value[0]
        else:
            return -1

    def delete_selection(self):
        racer_idx = self.get_selected_racer_index()
        if racer_idx >= 0:
            racer = self.parent.get_racer_by_index(racer_idx)
            heat_idx_a = self.parent.event.heat_index(heat_name=racer.heat_name)
            heat_idx_b = self.parent.heat_list.get_selected_heat_index()
            title = f"Delete {racer.name}"
            message = f"Do you want to permanently delete the racer {racer.name}?"
            if messagebox.askyesno(title, message):
                try:
                    self.parent.event.remove_racer(racer=racer)
                except ValueError:
                    print("Unable to remove racer.")
                    return
                else:
                    if heat_idx_a == heat_idx_b:
                        self.parent.racer_list.set_racers_from_heat(heat_idx_a)

    def edit_selected_racer(self):
        idx = self.get_selected_racer_index()
        if idx >= 0:
            racer = self.parent.get_racer_by_index(idx)
            RacerDialog(self.parent, racer=racer)


class HeatList:
    def __init__(self, parent: RegistrationWindow, racer_list: RacerList):
        top = parent.top
        self.parent = parent
        self.top = top
        self._outer_frame = tk.Frame(top)
        self._outer_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        title = tk.Label(self._outer_frame, text="Heats", font=('Serif', 22))
        title.pack(expand=True, fill=tk.X)

        self.list_box = tk.Listbox(self._outer_frame, selectmode=tk.SINGLE,
                                   exportselection=False)
        self.list_box.pack(expand=True, fill=tk.BOTH)

        edit_button = tk.Button(self._outer_frame, text="Edit", font=('Serif', 16),
                                command=self.edit_selected_heat)
        edit_button.pack(fill=tk.X, pady=2)

        add_button = tk.Button(self._outer_frame, text="Add", font=('Serif', 16),
                               command=self.add_heat)
        add_button.pack(fill=tk.X, pady=2)

        delete_button = tk.Button(self._outer_frame, text="Delete", font=('Serif', 16),
                                  command=self.delete_selection)
        delete_button.pack(fill=tk.X, pady=16)

        self.update_heat_list()

    def update_heat_list(self):
        self.list_box.delete(0, tk.END)
        self.list_box.insert(tk.END, "All Racers")
        for heat in self.parent.event.heats[:-1]:  # The last heat should stay hidden
            self.list_box.insert(tk.END, heat.name)

    def add_heat(self):
        HeatDialog(self.parent)
        self.parent.set_heat_pane()

    def get_selected_heat_index(self):
        selected_value = self.list_box.curselection()
        if len(selected_value) > 0:
            return selected_value[0] - 1
        else:
            return -1

    def delete_selection(self):
        idx = self.get_selected_heat_index()
        heat = self.parent.event.heats[idx]
        if idx >= 0:
            title = f"Delete {heat.name}"
            if len(heat.racers) > 1:
                message = f"Do you want to permanently delete the heat {heat.name} and the following racers:"
                for racer in heat.racers[:-1]:
                    message += " " + racer.name + ","
                message += " and " + heat.racers[-1].name + "?"
            if messagebox.askyesno(title, message):
                try:
                    self.parent.event.remove_heat(heat=self.parent.event.heats[idx])
                except ValueError:
                    print("Unable to remove heat.")
                    return
                else:
                    self.parent.heat_list.update_heat_list()

    def edit_selected_heat(self):
        idx = self.get_selected_heat_index()
        if idx >= 0:
            heat = self.parent.event.heats[idx]
            HeatDialog(self.parent, heat=heat)


class SaveWindow:
    def __init__(self,
                 parent: tk.Tk,
                 input_fname: str):
        self.parent = parent
        self.suggested_fname = new_fname(input_fname)
        self.overwrite_name = input_fname
        self.return_name = self.suggested_fname

        if messagebox.askyesno("Save?", "Do you need to save your work?"):
            self.running = True
        else:
            self.return_name = None
            self.running = False

        question = tk.Label(parent, text="What would you like to do with the changes you made?")
        question.pack(fill=tk.BOTH, expand=True)

        button = tk.Button(parent, text=f"Save as {self.suggested_fname}", command=self.use_suggested)
        button.pack(fill=tk.BOTH, expand=True, pady=5)

        button = tk.Button(parent, text=f"Select a filename", command=self.select_file)
        button.pack(fill=tk.BOTH, expand=True)

        button = tk.Button(parent, text=f"Overwrite {self.overwrite_name}", command=self.overwrite)
        button.pack(fill=tk.BOTH, expand=True, pady=5)

        button = tk.Button(parent, text=f"Do Not Save", command=self.dont_save)
        button.pack(fill=tk.BOTH, expand=True)

    def use_suggested(self):
        self.return_name = self.suggested_fname
        self.parent.destroy()

    def select_file(self):
        self.return_name = filedialog.asksaveasfilename(defaultextension=".yaml")
        self.parent.destroy()

    def overwrite(self):
        self.return_name = self.overwrite_name
        self.parent.destroy()

    def dont_save(self):
        self.return_name = None
        self.parent.destroy()

    def get_preference(self):
        if self.running:
            self.parent.mainloop()
        return self.return_name


if __name__ == "__main__":
    post_placements = True
    cli_args = parser.parse_args()

    main_window = RegistrationWindow(tk.Tk(),
                                     event_file=cli_args.event_file)

    event, file_name = main_window.mainloop()

    if cli_args.save_action == 'ask':
        save_window = SaveWindow(tk.Tk(), file_name)
        out_fname = save_window.get_preference()
    if cli_args.save_action == 'overwrite':
        out_fname = cli_args.event_file
    elif cli_args.save_action == 'new_file':
        out_fname = new_fname(cli_args.event_file)
    else:
        out_frame = None

    if out_fname is not None:
        event.print_plan_yaml(out_fname)
