import time

# If possible avoid imports from this project because this progress_report could be moved
# to an independent module


class ProgressReport:
    def __init__(self, total_steps, extra_information="", frequency_of_reports=1, steps_are_bytes=False):
        self._frequency_of_reports = frequency_of_reports
        self._total_steps = total_steps
        self._current_step = 0
        self._start_time = time.time()
        self._steps_to_next_print_report = 0
        self._last_printed_report = 0
        self._extra_information = extra_information
        self._steps_are_bytes = steps_are_bytes
        print("*********** Progress Report - initialized - Total steps:", self._steps_to_human_readable(total_steps))

    def increment_step(self):
        self._current_step += 1

    def increment_and_print_if_needed(self):
        self.increment_step()
        self.print_report_if_needed()

    def increment_steps(self, steps):
        self._current_step += steps

    def increment_steps_and_print_if_needed(self, steps):
        self.increment_steps(steps)
        self.print_report_if_needed()

    def print_report_if_needed(self):
        if (time.time() - self._last_printed_report) > self._frequency_of_reports:
            elapsed_time = time.time() - self._start_time
            speed = self._current_step / elapsed_time
            percentage_complete = (self._current_step / self._total_steps) * 100
            total_expected_time = (self._total_steps * elapsed_time) / self._current_step
            remaining_time = total_expected_time - elapsed_time

            print("========== PROGRESS: {}".format(self._extra_information))
            print("Processing {} of {}. Elapsed time: {}. Remaining time: {}.".format(self._steps_to_human_readable(self._current_step),
                                                                                      self._steps_to_human_readable(self._total_steps),
                                                                                      self._seconds_to_human_readable(elapsed_time),
                                                                                      self._seconds_to_human_readable(remaining_time)))

            speed_per_minute = speed*60

            print("Speed minute: {}/s Percentage: {:.2f}%".format(self._steps_to_human_readable(speed_per_minute), percentage_complete))
            print()

            self._last_printed_report = time.time()

            return remaining_time

    def _steps_to_human_readable(self, steps):
        if self._steps_are_bytes:
            return "{}".format(self._bytes_to_human_readable(steps))
        else:
            return "{:.2f} steps".format(steps)

    @staticmethod
    def _seconds_to_human_readable(seconds):
        minutes = seconds / 60

        if minutes < 1:
            return "{:.2f} secs".format(seconds)

        hours = minutes / 60
        if hours < 1:
            return "{:.2f} mins".format(minutes)

        days = hours / 24
        if days == 0:
            return "{:.2f} hours".format(hours)

        return "{:.2f} days".format(days)


    @staticmethod
    def _bytes_to_human_readable(num):
        if num is None:
            return "Unknown"

        for unit in ['','KB','MB','GB','TB','PB','EB','ZB']:
            if abs(num) < 1024.0:
                return "{:.2f} {}".format(num, unit)
            num /= 1024.0
        return "%d %s" % (num, 'YB')
