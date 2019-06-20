import time


class ProgressReport:
    def __init__(self, total_steps, extra_information="", frequency_of_reports=1):
        self._frequency_of_reports = frequency_of_reports
        self._total_steps = total_steps
        self._current_step = 0
        self._start_time = time.time()
        self._steps_to_next_print_report = 0
        self._last_printed_report = 0
        self._extra_information = extra_information
        print("*********** Progress Report - initialized - total_steps:", total_steps)

    def increment_step(self):
        self._current_step += 1

    def print_report_if_needed(self):
        if (time.time() - self._last_printed_report) > self._frequency_of_reports:
            elapsed_time = time.time() - self._start_time
            speed = self._current_step / elapsed_time
            percentage_complete = (self._current_step / self._total_steps) * 100
            total_expected_time = (self._total_steps * elapsed_time) / self._current_step
            remaining_time = total_expected_time - elapsed_time

            print("========== PROGRESS: {}".format(self._extra_information))
            print("Processing {} of {}. Elapsed time: {:.2f} minutes. Remaining time: {:.2f} minutes.".format(self._current_step,
                                                                                                 self._total_steps,
                                                                                                 elapsed_time / 60,
                                                                                                 remaining_time / 60))

            print("Steps per minute: {:.2f} Percentage: {:.2f}%".format(speed*60, percentage_complete))
            print()

            self._last_printed_report = time.time()

            return remaining_time

    def increment_and_print_if_needed(self):
        self.increment_step()
        self.print_report_if_needed()