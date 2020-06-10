import pyaudio
import audioop
import time
import datetime
import numpy as np
import speech_recognition as sr


class FramesRecorder:
    def __init__(self, audio_format=pyaudio.paInt16, channels=1, rate=44100, chunk=1024):
        self.audio_format = audio_format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk

        self._start = False

    def start(self):
        self._start = True

    def stop(self):
        self._start = False

    def record(self, frames):
        p = pyaudio.PyAudio()
        stream = p.open(format=self.audio_format,
                        channels=self.channels,
                        rate=self.rate,
                        input=True,
                        frames_per_buffer=self.chunk)

        self.start()
        while self._start:
            data = stream.read(self.chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        print('done recording')

    def play(self, frames):
        p = pyaudio.PyAudio()
        stream = p.open(format=self.audio_format,
                        channels=self.channels,
                        rate=self.rate,
                        input=True,
                        frames_per_buffer=self.chunk)

        stream.write(b''.join(frames))

        stream.stop_stream()
        stream.close()
        p.terminate()


class SplitDetector:
    def __init__(self, min_duration=5, format_width=2, sample_steps=4, filter_limit=0.1,
                 kernel_width=3, rate=44100, chunk=1024):
        self.min_duration   = min_duration
        self.format_width   = format_width
        self.sample_steps   = sample_steps
        self.filter_limit   = filter_limit
        self.kernel_width   = kernel_width
        self.rate           = rate
        self.chunk          = chunk

        self._start = False

    def start(self):
        self._start = True

    def stop(self):
        self._start = False

    def detect(self, frames, positions, recognize):
        pointer ,frames_size = 0, 0

        self.start()
        while self._start:
            time.sleep(0.1)

            volumes = [
                audioop.rms(data, self.format_width)
                for data in frames[pointer::self.sample_steps]]

            clock = time.time()
            begin, end = self.find_positon(volumes)
            if begin < end:
                begin = begin * self.sample_steps + pointer
                end = (end + 1) * self.sample_steps + pointer
                positions.append((begin, end))
                recognize(frames, begin, end)
                pointer = end
            elif len(frames) == frames_size and pointer < frames_size:
                begin, end = pointer, frames_size
                positions.append((begin, end))
                recognize(frames, begin, end)
                pointer = end
            time.sleep(1 if time.time() - clock < 1 else 0)
            frames_size = len(frames)

        print('done detecting')

    def find_positon(self, volumes):
        if len(volumes) < 5: return 0, 0

        volume_array = np.array(volumes)
        volume_array = volume_array / max(volume_array.max(), 100)

        kernel = np.ones((self.kernel_width, ))
        kernel_thresh = self.kernel_width - 1
        filtered = np.convolve(volume_array < self.filter_limit, kernel, mode='same')
        statues = np.convolve(filtered > kernel_thresh, [-1, 1], mode='same')

        min_limit = int(self.rate / self.chunk * self.min_duration / self.sample_steps)
        begin, end = 0, 0
        for i, position in enumerate(np.where(statues != 0)[0]):
            if i == 0 and statues[position] > 0:
                begin = position
            elif statues[position] < 0 and (position - begin) > min_limit:
                end = position
                break
        return begin, end

    def position2duration(self, position):
        return self.chunk / self.rate * position


class Speech2Text:
    def __init__(self, rate=44100, width=2, chunk=1024):
        self.rate = rate
        self.width = width
        self.chunk = chunk

        self._recognize = sr.Recognizer().recognize_google
        self.language = 'en_US'

    def set_language(self, language):
        self.language = language

    def recognize(self, frames, begin, end):
        result = ''
        frame_data = b''.join(frames[begin:end])
        audio_data = sr.AudioData(frame_data, self.rate, self.width)
        try:
            result = self._recognize(audio_data, language=self.language)
        except sr.UnknownValueError:
            result = '###'
        return self.position2time(begin), self.position2time(end), result

    def position2time(self, position):
        return str(datetime.timedelta(seconds=position * self.chunk / self.rate))


if __name__ == "__main__":
    from threading import Thread

    frames      = []
    positions   = []

    recognizer = Speech2Text()
    recognizer.set_language('zh')

    recorder = FramesRecorder()
    detector = SplitDetector()

    record_t = Thread(target=recorder.record, args=(frames, ))
    detect_t = Thread(
        target=detector.detect,
        args=(frames, positions, recognizer.recognize))

    record_t.start()
    detect_t.start()

    time.sleep(60 * 3)
    recorder.stop()

    record_t.join()
    detector.stop()
    detect_t.join()
