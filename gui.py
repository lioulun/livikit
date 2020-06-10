#! /usr/bin/env python3
from kivy.app import App
from kivy.uix.stacklayout import StackLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle

from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from core import FramesRecorder
from core import SplitDetector
from core import Speech2Text

from threading import Thread
import os


ROOT_DIR  = os.path.dirname(os.path.abspath(__file__))
FONT_NAME = os.path.join(ROOT_DIR, 'WenQuanWeiMiHei-1.ttf')


class LivikitControl(BoxLayout):
    def __init__(self, **kwargs):
        super(LivikitControl, self).__init__(**kwargs)

        self.size_hint_y = None
        self.height = 35

        self.start = Button(text='start', size_hint_x=None, width=70)
        self.add_widget(self.start)

        self.stop = Button(text='stop', size_hint_x=None, width=70)
        self.add_widget(self.stop)

        self.save = Button(text='', size_hint_x=None, width=70)
        self.add_widget(self.save)

        self.path = TextInput(text='save', multiline=False, font_name=FONT_NAME)
        self.add_widget(self.path)

        self.stop.disabled = True
        self.save.disabled = True


class LivikitLines(ScrollView):
    def __init__(self, **kwargs):
        super(LivikitLines, self).__init__(**kwargs)

        self.do_scroll_y = True

        self.layout = StackLayout(orientation='lr-tb', size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        self.add_widget(self.layout)

        self.add_info('Time', 'Text')

    def add_info(self, text1, text2):
        line = BoxLayout(size_hint_y=None, height=35)

        line.add_widget(Label(text=text1, size_hint_x=None, width=210))
        line.add_widget(Label(text=text2))

        self.layout.add_widget(line)

    def add_item(self, begin, end, text):
        line = BoxLayout(size_hint_y=None, height=63)

        time_part = BoxLayout(orientation='vertical')
        time_part.size_hint_x = None
        time_part.width = 210
        time_part.add_widget(self.new_label_time('begin', begin))
        time_part.add_widget(self.new_label_time('  end', end))
        line.add_widget(time_part)

        line.add_widget(TextInput(text=text, font_name=FONT_NAME))

        self.layout.add_widget(line)

    def new_label_time(self, label, text):
        pair = BoxLayout()
        pair.add_widget(Label(text=label, size_hint_x=None, width=49))
        pair.add_widget(TextInput(text=text, multiline=False, halign='center'))
        return pair


class LivikitMain(BoxLayout):
    def __init__(self, **kwargs):
        super(LivikitMain, self).__init__(**kwargs)

        self.orientation = 'vertical'
        self.head = LivikitControl()
        self.body = LivikitLines()

        self.add_widget(self.head)
        self.add_widget(self.body)

        self.head.start.bind(on_press=self.click_start)
        self.head.stop.bind(on_press=self.click_stop)
        self.head.save.bind(on_press=self.click_save)

        self.audio_frames    = []
        self.audio_positions = []
        self.lines           = []

        self.recorder   = FramesRecorder()
        self.detector   = SplitDetector()
        self.recognizer = Speech2Text()

        self.recognizer.set_language('zh')

    def add_recognized(self, frames, begin, end):
        begin_time, end_time, text = self.recognizer.recognize(frames, begin, end)
        self.body.add_item(begin_time, end_time, text)
        line = '[{},{}] {}'.format(begin_time, end_time, text)
        self.lines.append(line)
        print(line)

    def click_start(self, instance):
        instance.disabled = True

        self.audio_frames.clear()
        self.audio_positions.clear()
        self.lines.clear()
        record_t = Thread(target=self.recorder.record, args=(self.audio_frames, ))
        detect_t = Thread(
            target=self.detector.detect,
            args=(
                self.audio_frames,
                self.audio_positions,
                self.add_recognized))

        record_t.start()
        detect_t.start()

        self.head.stop.disabled = False

    def click_stop(self, instance):
        instance.disabled = True

        self.recorder.stop()
        self.detector.stop()

        self.head.start.disabled = False
        self.head.save.disabled = False

    def click_save(self, instance):
        if self.head.path.text:
            with open(self.head.path.text, 'w') as f:
                f.write('\n'.join(self.lines))

    def on_size(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.7019, 0.7019, 0.7019, 1)
            Rectangle(pos=self.pos, size=self.size)


class LivikitApp(App):
    def build(self):
        return LivikitMain()


if __name__ == "__main__":
    LivikitApp().run()
