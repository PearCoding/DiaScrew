#!/bin/python
import sys
import os
import tkinter as tk
from PIL import Image
from PIL import ImageTk
import json
import argparse


class Entry:
    def __init__(self, image_path: str, title: str, duration: int):
        self.image    = Image.open(image_path)
        self.name     = os.path.basename(image_path)
        self.title    = title
        self.duration = duration
        self.image_tk = None


class State:
    def __init__(self, config: dict):
        self.entries  = []
        self.current  = 0
        self.config   = config
        self.image_duration = config.get("duration", {}).get("image", 5)
        self.title_duration = config.get("duration", {}).get("title", 2)

    def addDirectory(self, dir: str):
        for f in os.listdir(dir):
            full_path = os.path.join(dir, f)

            if not os.path.isfile(full_path):
                continue

            _, ext = os.path.splitext(full_path)

            if ext in Image.registered_extensions().keys():
                self.addEntry(full_path)

    def addEntry(self, path: str):
        try:
            name  = os.path.basename(path)
            title = self.config.get("titles", {}).get(name, '')

            # Special extra for our RenderingCompetition (Saarland University CG)
            if not title and self.config.get("rctitle", False):
                fullname, _ = os.path.splitext(name)
                tokens = fullname.split("_")
                competition = tokens[0]
                if not competition.startswith("rc"):
                    return
                names = " ".join(tokens[1:])
                names = names.replace("web", "").replace("Web", "").replace("WEB", "").strip()
                year1 = competition[2:4]
                year2 = competition[4:]
                title = f"20{year1} - 20{year2}: {names}"

            self.entries.append(Entry(path, title, self.image_duration))
            print(f"Added {path}")
        except:
            print(f"Failed to add {path}")

    def randomize(self):
        import random
        random.shuffle(self.entries)

    def next(self):
        self.current += 1
        if self.current >= len(self.entries):
            self.current = 0

    def previous(self):
        self.current -= 1
        if self.current < 0:
            self.current = len(self.entries) - 1

    @property
    def current_entry(self) -> Entry | None:
        if len(self.entries) == 0:
            return None
        else:
            return self.entries[self.current]

    @property
    def current_duration(self) -> int:
        if len(self.entries) == 0:
            return 1
        else:
            return self.entries[self.current].duration


class Window:
    def __init__(self, state: State):
        self.state = state
        self.image_timer = None
        self.title_timer = None
        self.current_image_id = None
        self.current_title_id = None
        self.current_rectangle_id = None

        self.tk = tk.Tk()
        self.tk.attributes('-zoomed', True)
        self.tk.minsize(100, 100)
        self.tk.wm_title("Diascrew")

        self.canvas = tk.Canvas(self.tk)
        self.canvas.pack(expand=True, fill="both", anchor = "center")

        self.fullscreen_state = False
        self.tk.focus_set()
        self.tk.bind("<F11>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)
        self.tk.bind("<Left>", self.handle_previous)
        self.tk.bind("<Right>", self.handle_next)
        self.tk.bind('<Configure>', self._resize_event)

    def toggle_fullscreen(self, event=None):
        self.fullscreen_state = not self.fullscreen_state
        self.tk.attributes("-fullscreen", self.fullscreen_state)
        return "break"

    def end_fullscreen(self, event=None):
        self.fullscreen_state = False
        self.tk.attributes("-fullscreen", False)
        return "break"
    
    def handle_image(self):
        self.image_timer = None

        e = self.state.current_entry
        if e is None:
            return
        
        self.state.next()
        self._show(e)

    def handle_next(self, event=None):
        self.state.next()

        e = self.state.current_entry
        if e is None:
            return
        
        self._show(e)

    def handle_previous(self, event=None):
        self.state.previous()

        e = self.state.current_entry
        if e is None:
            return
        
        self._show(e)

    def show_title(self, text:str):
        self.canvas.delete("titles")

        x = int(0.5*self.canvas.winfo_width())
        y = int(0.9*self.canvas.winfo_height())
        fontsize = 36

        self.current_rectangle_id = self.canvas.create_rectangle(0, y-fontsize+5, self.canvas.winfo_width(), y+fontsize+5, 
                                                                 fill="black", outline="", stipple="gray75", tags=("titles"))
        self.current_title_id = self.canvas.create_text(x, y,
                                                        text=text, fill="white", font=("Purisa", fontsize),
                                                        justify="center", anchor="center", tags=("titles"))
        
    def hide_title(self):
        self.title_timer = None
        self.canvas.delete("titles")

    @staticmethod
    def computeFittingSize(maxWidth, maxHeight, width, height):
        innerAspectRatio = width / height
        outerAspectRatio = maxWidth / maxHeight

        resizeFactor = (maxWidth / width) if innerAspectRatio >= outerAspectRatio else (maxHeight / height)

        return (int(width * resizeFactor), int(height * resizeFactor))
    
    def _build_image(self, image: Image):
        width  = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        # Initial no width & height is given, just stick to the basic
        if width <= 1 or height <= 1:
            self.current_image = ImageTk.PhotoImage(image)    
        else:
            nw, nh = Window.computeFittingSize(width, height, image.width, image.height)
            self.current_image = ImageTk.PhotoImage(image.resize((nw, nh)))
        return self.current_image
    
    def _show(self, e:Entry):
        # print(f"Displaying {e.name}")
        self.canvas.delete("images")
        self.current_image_id = self.canvas.create_image(self.canvas.winfo_width()//2,self.canvas.winfo_height()//2,
                                                         image=self._build_image(e.image), anchor="center", tags=("images"))

        title = e.title if e.title else ""
        if not title:
            self.hide_title()
        else:
            self.show_title(title)
            if self.title_timer is not None:
                self.tk.after_cancel(self.title_timer)
            self.title_timer = self.tk.after(self.state.title_duration * 1000, self.hide_title)

        if self.image_timer is not None:
            self.tk.after_cancel(self.image_timer)
        self.image_timer = self.tk.after(e.duration * 1000, self.handle_image)

    def _resize_event(self, event):
        e = self.state.current_entry
        if e is None:
            return
        self._show(e)
        

if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(prog='diascrew', description='Basic diashow')

    parser.add_argument('config_file', default="config.json", nargs='?', help="Config file")
    parser.add_argument('-f', '--fullscreen', help="Start in fullscreen", action='store_true')
    parser.add_argument('--randomize', help="Randomize entries", action='store_true')

    args = parser.parse_args()

    # Config
    with open(args.config_file, "r") as f:
        config = json.load(f)
    root_path = os.path.dirname(args.config_file)

    # State
    state = State(config)
    for e in config.get("images", []):
        if not os.path.isabs(e):
            e = os.path.abspath(os.path.join(root_path, e))

        if os.path.isdir(e):
            state.addDirectory(e)
        else:
            state.addEntry(e)

    if len(state.entries) == 0:
        print("No images found to display")
        sys.exit(-1)

    if args.randomize:
        state.randomize()

    # Window
    w = Window(state)

    if args.fullscreen:
        w.toggle_fullscreen()

    w.handle_image()
    w.tk.mainloop()
