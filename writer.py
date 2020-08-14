# !/usr/bin/env python

##
##    A basic text writer
##    Copyright (C) 2016  Wayne Warren
##
##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License
##    along with this program. If not, see <http://www.gnu.org/licenses/>


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject
from gi.repository import Pango as pango

import shelve

#import pango


GObject.threads_init() #

# import subprocess                           #temp

class Writer(object):
    def __init__(self):
        self.width = 600
        self.height = 300
        # Gtk.rc_parse("test.rc")
        self.milliseconds = 50  # 1000 - 1 second
        self.time_mag = self.milliseconds
        self.edit_text = False
        # self.thread = GObject.timeout_add(100, self.text_edit, "nothing")#miliseconds, func
        self.thread = 0  # None
        self.path = ""
        self.file_text = ""
        self.start_filetxt_len = 0
        # for word by word
        self.words = []
        self.play_words = True  # set in config
        self.words_index = 0

        # font
        self.font = None
        self.font_dialog = Gtk.FontSelectionDialog("Font Selection Dialog")
        self.font_dialog.connect("destroy", self.font_dialog_destroyed)  # just hides the dialog
        self.font_dialog.get_ok_button().connect("clicked", self.font_selection_ok)  # button of dialog connect
        
        self.font_dialog.get_cancel_button().connect("clicked", self.font_dialog_destroyed)
        self.thread_removed = False
        
        # WINDOW
        self.win = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.win.set_title("Text writer")
        self.win.set_size_request(self.width, self.height)
        self.win.set_border_width(10)
        self.win.set_position(Gtk.WindowPosition.CENTER)
        self.win.connect("destroy", self.die)

        # bookmarks combobox
        self.combobox = Gtk.ComboBoxText()
        self.liststore = Gtk.ListStore(str)
        self.combobox.set_model(self.liststore)
        self.combobox.connect("changed", self.changed_cb)

        # file selection widget
        self.file_widget = Gtk.FileChooserDialog("Select File", action=Gtk.FileChooserAction.OPEN, buttons=(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        ########### menu bar
        # file
        self.file_open = Gtk.MenuItem.new_with_label('Open')
        self.file_open.connect('activate', self.set_path)
        self.file_quit = Gtk.MenuItem.new_with_label('Quit')
        self.file_quit.connect('activate', self.die)
        
        self.file_menu = Gtk.Menu.new()
        self.file_menu.append(self.file_open)
        self.file_menu.append(self.file_quit)

        self.file_main = Gtk.MenuItem.new_with_label('File')
        self.file_main.set_submenu(self.file_menu)
        # - end

        # edit
        self.edit_charmode = Gtk.MenuItem.new_with_label('Character Mode')
        self.edit_charmode.connect('activate', self.enable_char_mode)
        self.edit_font = Gtk.MenuItem.new_with_label('Font')
        self.edit_font.connect('activate', self.select_font)

        self.edit_menu = Gtk.Menu.new()
        self.edit_menu.append(self.edit_charmode)
        self.edit_menu.append(self.edit_font)

        self.edit_main = Gtk.MenuItem.new_with_label('Edit')
        self.edit_main.set_submenu(self.edit_menu)
        
        # - end

        # bookmarks
        self.bm_open = Gtk.MenuItem.new_with_label('Open')
        self.bm_open.connect('activate', self.open_pos)
        self.bm_save = Gtk.MenuItem.new_with_label('Save')
        self.bm_save.connect('activate', self.save_pos)

        self.bm_menu = Gtk.Menu.new()
        self.bm_menu.append(self.bm_open)
        self.bm_menu.append(self.bm_save)

        self.bm_main = Gtk.MenuItem.new_with_label('Bookmark')
        self.bm_main.set_submenu(self.bm_menu)
        # -end subs
        self.menu = Gtk.MenuBar.new()
        self.menu.append(self.file_main)
        self.menu.append(self.edit_main)
        self.menu.append(self.bm_main)
        ########### end menu

        # status bar, show path and mode
        self.status_bar = Gtk.Statusbar()
        self.context_id = self.status_bar.get_context_id("Statusbar")
        self.status_bar.show()

        # text box, text entry 
        self.scrolled_window_res = Gtk.ScrolledWindow()
        self.scrolled_window_res.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        # self.scrolled_window_res.set_size_request(self.width, self.height)
        self.text_view_writer = Gtk.TextView()
        self.text_view_writer.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view_writer.set_justification(Gtk.Justification.LEFT)  #
        # self.text_view_writer.set_right_margin(10)#
        self.text_view_writer.set_left_margin(10)  #
        self.text_view_writer.set_editable(False)  #
        self.text_buffer = self.text_view_writer.get_buffer()
        self.scrolled_window_res.add(self.text_view_writer)
        self.text_box = Gtk.HBox(homogeneous=False)
        self.text_box.pack_start(self.scrolled_window_res, expand=True, fill=True, padding=0)

        ## mid panel              #setat, min, max,     step,        pg inc,pg size
        self.adj1 = Gtk.Adjustment(50.0, 10.0, 1100.0, 10.0, 10.0, 10.0)  # edit in options menu
        self.adj1.connect("value_changed", self.adj_changed)
        self.horizontal_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.adj1)

        # self.horizontal_scale.set_size_request(200, 50)
        #self.horizontal_scale.set_update_policy(Gtk.UPDATE_CONTINUOUS)
        self.horizontal_scale.set_digits(1)
        self.horizontal_scale.set_value_pos(Gtk.PositionType.BOTTOM)
        self.horizontal_scale.set_draw_value(True)
        self.mid_box = Gtk.HBox(homogeneous=False)
        self.mid_box.pack_start(self.horizontal_scale, True, True, 0)

        ## bottom
        self.lower_ok_button = Gtk.Button(" Play ")  # ; self.lower_ok_button.set_name("rc_button")#test
        self.lower_ok_button.set_sensitive(0)
        self.lower_ok_button.connect("clicked", self.play, "play")

        self.lower_pause_button = Gtk.Button(" Pause ")
        self.lower_pause_button.set_sensitive(0)
        self.lower_pause_button.connect("clicked", self.pause, "pausing")

        self.lower_clear_button = Gtk.Button(" Clear ")
        self.lower_clear_button.set_sensitive(0)
        self.lower_clear_button.connect("clicked", self.clear, "clearing")

        self.lower_box = Gtk.HBox()
        self.lower_box.pack_start(self.lower_ok_button, expand=False, fill=False,padding=0)
        self.lower_box.pack_start(self.lower_pause_button, expand=False, fill=False,padding=0)
        self.lower_box.pack_start(self.lower_clear_button, expand=False, fill=False,padding=0)

        # all
        self.big_box = Gtk.VBox(homogeneous=False, spacing=10)
        self.big_box.pack_start(self.menu, expand=False, fill=False, padding=0 )

        self.big_box.pack_start(self.text_box, expand=True, fill=True,padding=0)
        self.big_box.pack_start(self.mid_box, expand=False, fill=False,padding=0)
        self.big_box.pack_start(self.lower_box, expand=False, fill=False,padding=0)
        self.big_box.pack_start(self.status_bar, expand=False, fill=False,padding=0)
        self.big_box.pack_start(self.combobox, expand=False, fill=False,padding=0)

        self.win.add(self.big_box)
        self.win.show_all()

        self.combobox.hide()

    # add message to status bar
    def add_message(self, widget, data):
        msg = "test"

        self.status_bar.push(self.context_id, data)
        return

    # menu toggle char mode / word mode
    def enable_char_mode(self, widget, data=None):
        self.clear(self, "clearing from mode change in edit menu")

        if widget.get_active():
            print("char toggled on")
            self.play_words = False
        else:
            print("char toggled off")
            self.play_words = True

    # bookmark chosen from combo box
    def changed_cb(self, comb, data=None):

        book = shelve.open('bookmarks.db', writeback=True)

        name = self.combobox.get_active_text()  # for fname
        file_name = book[name]["path"]

        # file io here for if file existed, often it will be 'None' because the default active text is empty
        if (file_name != None):
            if (len(file_name) > 0):  # the path is checked by the file widget
                with open(file_name) as text_f:
                    linelist = text_f.readlines()

                self.build_words(linelist)  # for if use wants word by word display, not char
                text_f.close()

                if (self.play_words == True):
                    prev_text = " ".join(self.words[0:  book[name]["word_location"]])  # spaces needed
                    self.words_index = book[name]["word_location"]
                    self.words = self.words[self.words_index:]

                    # fill previously shown txt
                    end_iter = self.text_buffer.get_end_iter()
                    #iter, text, len, default_editable
                    self.text_buffer.insert_interactive(end_iter, prev_text,len(prev_text), True)

                    # so text doesnt disappear.(iter, within_margin, use_align, xalign, yalign
                    self.text_view_writer.scroll_to_iter(end_iter, 0.0, True, 0, 0)

                    # show info
                    self.add_message(self, file_name)

                else:
                    prev_text = "".join(linelist)

                    # cut from bookmark location
                    prev_text = prev_text[0:book[name]["char_location"]]

                    # fill previously shown txt
                    end_iter = self.text_buffer.get_end_iter()
                    self.text_buffer.insert_interactive(end_iter, prev_text, True)

                    # so text doesnt disappear
                    self.text_view_writer.scroll_to_iter(end_iter, 0.0)

                    # now class var file_text will be made from shelve loc
                    self.file_text = "".join(linelist)
                    self.file_text = self.file_text[book[name]["char_location"]:]

                    # show info
                    self.add_message(self, file_name)

        self.combobox.hide()

        # so save_pos knows
        self.path = file_name

        # begin thread after updating buffer
        self.edit_text = True

    def die(self, widget, data=None):
        """close"""
        Gtk.main_quit()

    def main(self):
        Gtk.main()

    def stopping_thread(self):
        print("done threading")

    def text_edit(self, data="test"):
        # put elem 0 in the text buffer then remove it


        if self.edit_text:

            if (self.play_words == False):

                if len(self.file_text) > 0:  # it will shrink fast

                    end_iter = self.text_buffer.get_end_iter()

                    self.text_buffer.insert_interactive(end_iter, self.file_text[0], True)

                    # so text doesnt disappear
                    self.text_view_writer.scroll_to_iter(end_iter, 0.0)

                    self.file_text = self.file_text[1:]

                else:
                    print("Reached end of text file")
                    self.lower_pause_button.set_sensitive(0)
                    self.edit_text = False
                    GObject.source_remove(self.thread)
                    self.thread_removed = True
                    return False  # done, filetext will now be an empty str

            if (self.play_words == True):

                if len(self.words) > 0:  # it will shrink fast

                    # subprocess.Popen(["spd-say", "-t", "female3", self.words[0]])

                    end_iter = self.text_buffer.get_end_iter()
                                                                                # might replce len with -1
                    self.text_buffer.insert_interactive(end_iter, self.words[0], len(self.words[0]), True)  # self.words[0] + " "

                    # so text doesnt disappear
                    #iter, within_margin, use_align, xalign, yalign
                    self.text_view_writer.scroll_to_iter(end_iter, 0.0, True, 0,0)
                    self.words = self.words[1:]

                    # for bookmarking
                    self.words_index += 1

                else:
                    print("Reached end of text file")
                    self.lower_pause_button.set_sensitive(0)
                    self.edit_text = False
                    GObject.source_remove(self.thread)
                    self.thread_removed = True
                    return False  # done, filetext will now be an empty str



        else:
            print("passing")

        return True

    def pause(self, widget, data=None):
        # button disable
        self.lower_pause_button.set_sensitive(0)
        self.lower_ok_button.set_sensitive(1)

        # remove thread, check incase clear() is used first
        if (self.thread_removed == False):
            GObject.source_remove(self.thread)
            self.thread_removed = True

    def play(self, widget, data=None):
        # button disable
        self.lower_pause_button.set_sensitive(1)
        self.lower_ok_button.set_sensitive(0)
        self.lower_clear_button.set_sensitive(1)

        # start a new thread
        self.thread = GObject.timeout_add(self.milliseconds, self.text_edit, "nothing")  # miliseconds, func
        self.thread_removed = False  # so it can be removed properly in pause()

        # for thread
        self.edit_text = True

    def adj_changed(self, adj):

        self.pause(self.lower_pause_button, "adjustment")
        print(adj.get_value())
        self.milliseconds = int(adj.get_value())
        # self.play(self.lower_ok_button,"y")

    def clear(self, widget, data=None):
        self.add_message(self, " ")
        print(data)
        self.pause(self.lower_pause_button, "clear")
        self.path = ""
        self.words = []
        start = self.text_buffer.get_start_iter()
        end = self.text_buffer.get_end_iter()
        self.text_buffer.delete(start, end)

        self.lower_ok_button.set_sensitive(0)
        self.lower_clear_button.set_sensitive(0)
        self.lower_pause_button.set_sensitive(0)
        # self.adj1.set_sensitive(0)

    # for file open
    def set_path(self, widget, data=None):
        """sets self.path invoked in __init___"""
        self.response = self.file_widget.run()
        self.clear(self, "clearing before open file dialog")

        if self.response == Gtk.ResponseType.OK:
            print("Selected filepath: %s" % self.file_widget.get_filename())
            self.path = self.file_widget.get_filename()
            self.add_message(self, self.path)
            self.file_widget.hide()
            self.lower_ok_button.set_sensitive(1)
            # self.lower_clear_button.set_sensitive(1)

            # file io here for if file existed
            if len(self.path) > 0:  # the path is checked by the file widget
                with open(self.path) as text_file:
                    self.file_linelist = text_file.readlines()
                text_file.close()

            self.build_words(self.file_linelist)  # for if use wants word by word display, not char

            # file text as string.
            self.file_text = "".join(self.file_linelist)
            self.start_filetxt_len = len(self.file_text)

        # need cancel response
        if self.response == Gtk.ResponseType.CANCEL:
            self.file_widget.hide()

        # prevent freeze
        if self.response == Gtk.ResponseType.DELETE_EVENT:
            print("closing...")
            self.file_widget.hide()

    def save_pos(self, widget, data=None):

        bmark = shelve.open('bookmarks.db', writeback=True)

        name = self.get_short_name(self.path)

        # check if key is already there
        if (name in list(bmark.keys())):
            # loc = len(self.file_text) #
            if (self.play_words == True):
                loc = self.words_index
                bmark[name]["word_location"] = loc
                bmark.close()
            else:
                loc = self.start_filetxt_len - len(self.file_text)  # original str len - current str len
                bmark[name]["char_location"] = loc  ##
                bmark.close()

        # if no main key is present make a new entry            
        else:
            if (self.play_words == True):
                loc = self.words_index
                bmark[name] = {"word_location": loc, "char_location": 0, "path": self.path}
                bmark.close()
            else:  # only create char loc
                loc = self.start_filetxt_len - len(self.file_text)
                bmark[name] = {"word_location": 0, "char_location": loc, "path": self.path}
                bmark.close()

    def get_short_name(self, path):
        name = path
        if ("/" in name):
            sl_dex = name.rfind("/") + 1
            name = name[sl_dex:]
            return name
        else:
            return name

    # for opening a bookmarked location in text 
    def open_pos(self, widget, data=None):

        self.clear(self, "test")
        self.liststore.clear()

        self.lower_ok_button.set_sensitive(1)

        bookm = shelve.open('bookmarks.db', writeback=True)
        # loc = self.bookmarks[fname]["location"]
        #print(bookm)
        if (list(bookm.keys())):
            index = 0
            for name in list(bookm.keys()):
                if ("/" in name):
                    name = self.get_short_name(name)

                # self.combobox.append_text(name)
                if (self.play_words == True):
                    if (bookm[name]["word_location"] > 0):
                        self.liststore.append([name])
                else:
                    if (bookm[name]["char_location"] > 0):
                        self.liststore.append([name])

            self.combobox.show()

        bookm.close()

    def build_words(self, text):

        for row in text:
            temp_row = row.split(" ")
            for word in temp_row:
                # if ("\n" not in word):
                word += " "
                self.words += [word]

                # print self.words

    ### font related
    def font_dialog_destroyed(self, data=None):
        self.font_dialog.hide()

    def font_selection_ok(self, data=None):
        self.font = self.font_dialog.get_font_name()
        font_desc = Pango.FontDescription(self.font)
        self.text_view_writer.modify_font(font_desc)
        print(self.font)
        self.font_dialog.hide()

    def select_font(self, widget, data=None):

        # self.font = self.font_dialog.get_font_name()
        print("selecting font")
        self.pause(self.lower_pause_button, "x")
        self.font_dialog.show()


if __name__ == "__main__":
    retype = Writer()
    retype.main()
