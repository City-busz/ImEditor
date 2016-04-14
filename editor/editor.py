# -*- coding: utf-8 -*-
#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from PIL import Image, ImageDraw
from os import path

from interface import dialog
from filters import base
from editor.image import ImageObject
from editor.tools import get_coords

def img_open(func):
    def inner(self, *args, **kwargs):
        if len(self.images) > 0:
            return func(self, *args, **kwargs)
    return inner

class Editor(object):
    def __init__(self):
        super(Editor, self).__init__()
        self.images = list()
        self.MAX_HIST = 10

        self.task = 'select'
        self.selection = list()
        self.selected_img = None

    def set_win(self, win):
        self.win = win

    @img_open
    def close_image(self, index):
        self.images[index].close_all_img()
        self.images = self.images[:index] + self.images[index+1:]
        self.select(None, None)

    def add_image(self, *args):
        self.images.append(ImageObject(*args))

    def get_img(self):
        page_num = self.win.notebook.get_current_page()
        img = self.images[page_num].get_current_img()
        return img

    @img_open
    def apply_filter(self, action, parameter, func, value=None):
        func = eval(func)
        img = self.get_img()
        if value is None:
            new_img = func(img)
        else:
            new_img = func(img, value)
        self.do_change(new_img)

    def do_change(self, new_img):
        page_num = self.win.notebook.get_current_page()
        self.win.update_image(new_img)
        self.images[page_num].forget_img()
        self.images[page_num].add_img(new_img)
        self.images[page_num].increment_index()
        self.images[page_num].set_saved(False)
        if self.images[page_num].get_n_img() > self.MAX_HIST:
            self.images[page_num].remove_first_img()
            self.images[page_num].decrement_index()

    @img_open
    def filter_with_params(self, action, parameter, params):
        func = params[0]
        title = params[1]
        limits = params[2]
        params_dialog = dialog.params_dialog(self.win, title, limits)
        value = params_dialog.get_values()
        if value is not None:
            self.apply_filter(None, None, func, value)

    @img_open
    def history(self, action, parameter, num):
        page_num = self.win.notebook.get_current_page()
        if self.images[page_num].get_n_img() >= 2:
            index_img = self.images[page_num].get_index()
            if num == -1: # Undo:
                if index_img >= 1:
                    self.images[page_num].decrement_index()
                    new_img = self.images[page_num].get_current_img()
                    self.win.update_image(new_img)
            else: # Redo:
                if index_img + 1 < self.images[page_num].get_n_img():
                    self.images[page_num].increment_index()
                    new_img = self.images[page_num].get_current_img()
                    self.win.update_image(new_img)

    def select(self, action, parameter):
        if self.task != 'select':
            self.win.root.set_cursor(self.win.default_cursor)
            self.task = 'select'
            page_num = self.win.notebook.get_current_page()
            tmp_img = self.images[page_num].get_tmp_img()
            if tmp_img is not None:
                self.do_change(tmp_img)
                self.win.update_image(tmp_img)
                self.images[page_num].set_tmp_img(None)

    @img_open
    def draw(self, action, parameter):
        if self.task != 'draw-brush':
            self.task = 'draw-brush'
            self.win.root.set_cursor(self.win.draw_cursor)

    def press_task(self, widget, event):
        page_num = self.win.notebook.get_current_page()
        new_img = self.get_img().copy()
        tab = self.win.notebook.get_nth_page(page_num)
        x, y = get_coords(new_img, tab.get_allocation(), event)
        if self.task == 'draw-brush':
            self.move_task(None, event)
        elif self.task == 'select':
            self.selection.clear()
            self.selection.append(x)
            self.selection.append(y)
            self.win.update_image(new_img)
        elif self.task == 'paste':
            new_img = self.get_img().copy()
            x = x - (self.selected_img.width / 2)
            y = y - (self.selected_img.height / 2)
            new_img.paste(self.selected_img, (round(x), round(y)))
            self.win.update_image(new_img)
            self.images[page_num].set_tmp_img(new_img)

    def move_task(self, widget, event, shape='ellipse', size=5, color='black'):
        page_num = self.win.notebook.get_current_page()
        new_img = self.images[page_num].get_tmp_img().copy()
        tab = self.win.notebook.get_nth_page(page_num)
        x, y = get_coords(new_img, tab.get_allocation(), event)
        if self.task == 'select':
            draw = ImageDraw.Draw(new_img)
            x1 = self.selection[0]
            y1 = self.selection[1]
            draw.rectangle([x1, y1, x, y], outline=color)
            self.win.update_image(new_img)
        elif self.task == 'draw-brush':
            draw = ImageDraw.Draw(new_img)
            if shape == 'rectangle':
                draw.rectangle([x-size, y-size, x+size, y+size], color)
            elif shape == 'ellipse':
                draw.ellipse([x-size, y-size, x+size, y+size], color)
            self.win.update_image(new_img)
            self.images[page_num].set_tmp_img(new_img)
        elif self.task == 'paste':
            new_img = self.get_img().copy()
            x = x - (self.selected_img.width / 2)
            y = y - (self.selected_img.height / 2)
            new_img.paste(self.selected_img, (round(x), round(y)))
            self.win.update_image(new_img)
            self.images[page_num].set_tmp_img(new_img)

    def release_task(self, widget, event):
        page_num = self.win.notebook.get_current_page()
        img = self.images[page_num].get_tmp_img()
        tab = self.win.notebook.get_nth_page(page_num)
        x, y = get_coords(img, tab.get_allocation(), event)
        if self.task == 'draw-brush':
            img = self.images[page_num].get_tmp_img()
            self.images[page_num].set_tmp_img(None)
            self.do_change(img)
        elif self.task == 'select':
            self.selection.append(x)
            self.selection.append(y)

    def copy(self, action, parameter):
        if self.selection != list():
            img = self.get_img()
            self.selected_img = img.crop(tuple(self.selection))

    def paste(self, action, parameter):
        self.win.root.set_cursor(self.win.move_cursor)
        self.task = 'paste'
        new_img = self.get_img().copy()
        new_img.paste(self.selected_img, (0, 0))
        self.win.update_image(new_img)

    def cut(self, action, parameter):
        if self.selection != list():
            self.copy(None, None)
            blank_img = Image.new('RGB', self.selected_img.size, 'white')
            img = self.get_img().copy()
            img.paste(blank_img, tuple(self.selection[:2]))
            self.win.update_image(img)
            self.do_change(img)

    @img_open
    def file_save(self, action, parameter):
        page_num = self.win.notebook.get_current_page()
        if self.images[page_num].get_is_new_image():
            self.file_save_as(None, None)
        else:
            img = self.images[page_num].get_current_img()
            self.images[page_num].set_saved(True)
            img.save(self.images[page_num].get_filename())

    @img_open
    def file_save_as(self, action, parameter):
        page_num = self.win.notebook.get_current_page()

        dialog = Gtk.FileChooserDialog('Choisissez un fichier', self.win,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            img = self.images[page_num].get_current_img()
            img.save(filename)
            self.images[page_num].set_filename(filename)
            page_num = self.win.notebook.get_current_page()
            self.win.notebook.get_nth_page(page_num).get_tab_label().set_label(path.basename(filename))
            self.images[page_num].set_saved(True)
        dialog.destroy()

    @img_open
    def properties(self, action, parameter):
        page_num = self.win.notebook.get_current_page()
        img = self.images[page_num].get_current_img()
        dialog = Gtk.MessageDialog(self.win, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK, 'Propriétés de l\'image')
        message = '<b>Taille : </b>' + str(img.width) + 'x' + str(img.height) + ' <b>Mode : </b>' + img.mode
        dialog.format_secondary_markup(message)
        dialog.run()
        dialog.destroy()
