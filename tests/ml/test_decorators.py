import time

import torch
from torch.utils.tensorboard import SummaryWriter

from audiotools.ml.decorators import timer
from audiotools.ml.decorators import Tracker
from audiotools.ml.decorators import when


def test_all_decorators():
    rank = 0
    max_iters = 100

    writer = SummaryWriter("/tmp/logs")
    tracker = Tracker(writer, log_file="/tmp/log.txt")

    train_data = range(100)
    val_data = range(100)

    @tracker.log("train", "value", history=False)
    @tracker.track("train", max_iters, tracker.step)
    @timer()
    def train_loop():
        i = tracker.step
        time.sleep(0.01)
        return {
            "loss": torch.exp(torch.FloatTensor([-i / 100])),
            "mel": torch.exp(torch.FloatTensor([-i / 100])),
            "stft": torch.exp(torch.FloatTensor([-i / 100])),
            "waveform": torch.exp(torch.FloatTensor([-i / 100])),
            "not_scalar": torch.arange(10),
        }

    @tracker.track("val", len(val_data))
    @timer()
    def val_loop():
        i = tracker.step
        time.sleep(0.01)
        return {
            "loss": torch.exp(torch.FloatTensor([-i / 100])),
            "mel": torch.exp(torch.FloatTensor([-i / 100])),
            "stft": torch.exp(torch.FloatTensor([-i / 100])),
            "waveform": torch.exp(torch.FloatTensor([-i / 100])),
            "not_scalar": torch.arange(10),
            "string": "string",
        }

    @when(lambda: tracker.step % 1000 == 0 and rank == 0)
    @torch.no_grad()
    def save_samples():
        tracker.print("Saving samples to TensorBoard.")

    @when(lambda: tracker.step % 100 == 0 and rank == 0)
    def checkpoint():
        save_samples()
        if tracker.is_best("val", "mel"):
            tracker.print("Best model so far.")
        tracker.print("Saving to /runs/exp1")
        tracker.done("val", f"Iteration {tracker.step}")

    @when(lambda: tracker.step % 100 == 0)
    @tracker.log("val", "mean")
    @torch.no_grad()
    def validate():
        for _ in range(len(val_data)):
            output = val_loop()
        return output

    with tracker.live:
        for tracker.step in range(max_iters):
            validate()
            checkpoint()
            train_loop()

    state_dict = tracker.state_dict()
    tracker.load_state_dict(state_dict)

    # If train loop returned not a dict
    @tracker.track("train", max_iters, tracker.step)
    def train_loop_2():
        i = tracker.step
        time.sleep(0.01)

    with tracker.live:
        for tracker.step in range(max_iters):
            validate()
            checkpoint()
            train_loop_2()
