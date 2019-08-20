import datetime
import time

import termcolor


# If possible avoid imports from this project because this progress_report could be moved
# to an independent module


class ProgressReport:
    def __init__(self, total_steps: int, unit: str = 'steps', extra_information: str = '',
                 frequency_of_reports: int = 1, steps_are_bytes: bool = False):
        self._frequency_of_reports: int = frequency_of_reports
        self._total_steps: int = total_steps
        self._unit: str = unit
        self._current_step: int = 0
        self._start_time: float = time.time()
        self._last_printed_report: float = 0
        self._extra_information: str = extra_information
        self._steps_are_bytes: int = steps_are_bytes
        progress_print('Progress Report - initialized - Total {}:'.format(self._steps_to_human_readable(total_steps)))

    def increment_step(self) -> None:
        self._current_step += 1

    def increment_and_print_if_needed(self) -> None:
        self.increment_step()
        self.print_report_if_needed()

    def increment_steps(self, steps: int) -> None:
        self._current_step += steps

    def increment_steps_and_print_if_needed(self, steps: int) -> None:
        self.increment_steps(steps)
        self.print_report_if_needed()

    def print_report_if_needed(self) -> None:
        if (time.time() - self._last_printed_report) > self._frequency_of_reports:
            elapsed_time = time.time() - self._start_time
            speed = self._current_step / elapsed_time
            percentage_complete = (self._current_step / self._total_steps) * 100
            total_expected_time = (self._total_steps * elapsed_time) / self._current_step
            remaining_time = total_expected_time - elapsed_time
            eta = time.time() + remaining_time

            progress_print('PROGRESS: {}'.format(self._extra_information))
            progress_print('Processed {} of {}. Elapsed time: {}. Remaining time: {}. ETA: {}.'.format(
                self._steps_to_human_readable(self._current_step),
                self._steps_to_human_readable(self._total_steps),
                self._seconds_to_human_readable(elapsed_time),
                self._seconds_to_human_readable(remaining_time),
                datetime.datetime.fromtimestamp(eta).replace(tzinfo=datetime.timezone.utc).strftime(
                    '%a %Y-%m-%d %H:%M:%S UTC')))

            speed_per_minute = speed * 60

            progress_print('Speed: {}/minute Percentage: {:.2f}%'.format(
                self._steps_to_human_readable(speed_per_minute, format_output='{:.2f}'), percentage_complete))
            print()

            self._last_printed_report = time.time()

    def _steps_to_human_readable(self, steps: float, format_output: str = '{}') -> str:
        if self._steps_are_bytes:
            return '{}'.format(self._bytes_to_human_readable(int(steps)))
        else:
            return (format_output + ' {}').format(steps, self._unit)

    @staticmethod
    def _seconds_to_human_readable(seconds: float) -> str:
        minutes = seconds / 60

        if minutes < 1:
            return '{:.2f} secs'.format(seconds)

        hours = minutes / 60
        if hours < 1:
            return '{:.2f} mins'.format(minutes)

        days = hours / 24
        if days < 1:
            return '{:.2f} hours'.format(hours)

        return '{:.2f} days'.format(days)

    @staticmethod
    def _bytes_to_human_readable(num: int) -> str:
        if num is None:
            return 'Unknown'

        for unit in ['', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB']:
            if abs(num) < 1024.0:
                return '{:.2f} {}'.format(num, unit)
            num /= 1024.0
        return '%d %s' % (num, 'YB')


def progress_print(string: str) -> None:
    print(termcolor.colored(string, 'green', attrs=['bold']))
