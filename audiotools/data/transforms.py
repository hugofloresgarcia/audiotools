from collections import defaultdict
from contextlib import contextmanager
from inspect import signature
from typing import List

import numpy as np
import torch
from flatten_dict import flatten
from flatten_dict import unflatten
from numpy.random import RandomState

from ..core import AudioSignal
from ..core import util

tt = torch.tensor


class BaseTransform:
    def __init__(self, keys: list = [], name: str = None, prob: float = 1.0):
        # Get keys from the _transform signature.
        tfm_keys = list(signature(self._transform).parameters.keys())

        # Filter out signal and kwargs keys.
        ignore_keys = ["signal", "kwargs"]
        tfm_keys = [k for k in tfm_keys if k not in ignore_keys]

        # Combine keys specified by the child class, the keys found in
        # _transform signature, and the mask key.
        self.keys = keys + tfm_keys + ["mask"]

        self.prob = prob

        if name is None:
            name = self.__class__.__name__
        self.name = name

    def prepare(self, batch: dict):
        sub_batch = batch[self.name]

        for k in self.keys:
            assert k in sub_batch.keys(), f"{k} not in batch"

        return sub_batch

    def _transform(self, signal):
        return signal

    def _instantiate(self, state: RandomState, signal: AudioSignal = None):
        return {}

    @staticmethod
    def apply_mask(batch, mask):
        masked_batch = {k: v[mask] for k, v in flatten(batch).items()}
        return unflatten(masked_batch)

    def transform(self, signal, **kwargs):
        tfm_kwargs = self.prepare(kwargs)
        mask = tfm_kwargs["mask"]

        if torch.any(mask):
            tfm_kwargs = self.apply_mask(tfm_kwargs, mask)
            tfm_kwargs = {k: v for k, v in tfm_kwargs.items() if k != "mask"}
            signal[mask] = self._transform(signal[mask], **tfm_kwargs)

        return signal

    def __call__(self, *args, **kwargs):
        return self.transform(*args, **kwargs)

    def instantiate(
        self,
        state: RandomState,
        signal: AudioSignal = None,
    ):
        state = util.random_state(state)

        # Not all instantiates need the signal. Check if signal
        # is needed before passing it in, so that the end-user
        # doesn't need to have variables they're not using flowing
        # into their function.
        needs_signal = "signal" in set(signature(self._instantiate).parameters.keys())
        kwargs = {}
        if needs_signal:
            kwargs = {"signal": signal}

        # Instantiate the parameters for the transform.
        params = self._instantiate(state, **kwargs)
        for k in list(params.keys()):
            v = params[k]
            if isinstance(v, (AudioSignal, torch.Tensor, dict)):
                params[k] = v
            else:
                params[k] = tt(v)
        mask = state.rand() <= self.prob
        params[f"mask"] = tt(mask)

        # Put the params into a nested dictionary that will be
        # used later when calling the transform. This is to avoid
        # collisions in the dictionary.
        params = {self.name: params}

        return params

    def batch_instantiate(
        self,
        states: list,
        signal: AudioSignal = None,
    ):
        kwargs = []
        for state in states:
            kwargs.append(self.instantiate(state, signal))
        kwargs = util.collate(kwargs)
        return kwargs


class Compose(BaseTransform):
    def __init__(self, transforms: list, name: str = None, prob: float = 1.0):
        for i, tfm in enumerate(transforms):
            tfm.name = f"{i}.{tfm.name}"

        keys = [tfm.name for tfm in transforms]
        super().__init__(keys=keys, name=name, prob=prob)

        self.transforms = transforms
        self.transforms_to_apply = keys

    @contextmanager
    def filter(self, *names):
        old_transforms = self.transforms_to_apply
        self.transforms_to_apply = names
        yield
        self.transforms_to_apply = old_transforms

    def _transform(self, signal, **kwargs):
        for transform in self.transforms:
            if any([x in transform.name for x in self.transforms_to_apply]):
                signal = transform(signal, **kwargs)
        return signal

    def _instantiate(self, state: RandomState, signal: AudioSignal = None):
        parameters = {}
        for transform in self.transforms:
            parameters.update(transform.instantiate(state, signal=signal))
        return parameters

    def __getitem__(self, idx):
        return self.transforms[idx]

    def __len__(self):
        return len(self.transforms)

    def __iter__(self):
        for transform in self.transforms:
            yield transform


class Choose(Compose):
    # Class logic is the same as Compose, but instead of applying all
    # the transforms in sequence, it applies just a single transform,
    # which is picked deterministically by summing all of the `seed`
    # integers (which could be just one or a batch of integers), and then
    # using the sum as a seed to build a RandomState object that it then
    # calls `choice` on, with probabilities `self.weights``.
    def __init__(
        self,
        transforms: list,
        weights: list = None,
        max_seed: int = 1000,
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(transforms, name=name, prob=prob)

        if weights is None:
            _len = len(self.transforms)
            weights = [1 / _len for _ in range(_len)]
        self.weights = np.array(weights)
        self.max_seed = max_seed

    def _transform(self, signal, seed, **kwargs):
        state = seed.sum().item()
        state = util.random_state(state)
        idx = list(range(len(self.transforms)))
        idx = state.choice(idx, p=self.weights)
        return self.transforms[idx](signal, **kwargs)

    def _instantiate(self, state: RandomState, signal: AudioSignal = None):
        parameters = super()._instantiate(state, signal)
        parameters["seed"] = state.randint(self.max_seed)
        return parameters


class ClippingDistortion(BaseTransform):
    def __init__(
        self,
        perc: tuple = ("uniform", 0.0, 0.1),
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)

        self.perc = perc

    def _instantiate(self, state: RandomState):
        return {"perc": util.sample_from_dist(self.perc, state)}

    def _transform(self, signal, perc):
        return signal.clip_distortion(perc)


class Equalizer(BaseTransform):
    def __init__(
        self,
        eq_amount: tuple = ("const", 1.0),
        n_bands: int = 6,
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)

        self.eq_amount = eq_amount
        self.n_bands = n_bands

    def _instantiate(self, state: RandomState):
        eq_amount = util.sample_from_dist(self.eq_amount, state)
        eq = -eq_amount * state.rand(self.n_bands)
        return {"eq": eq}

    def _transform(self, signal, eq):
        return signal.equalizer(eq)


class Quantization(BaseTransform):
    def __init__(
        self,
        channels: tuple = ("choice", [8, 32, 128, 256, 1024]),
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)

        self.channels = channels

    def _instantiate(self, state: RandomState):
        return {"channels": util.sample_from_dist(self.channels, state)}

    def _transform(self, signal, channels):
        return signal.quantization(channels)


class MuLawQuantization(BaseTransform):
    def __init__(
        self,
        channels: tuple = ("choice", [8, 32, 128, 256, 1024]),
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)

        self.channels = channels

    def _instantiate(self, state: RandomState):
        return {"channels": util.sample_from_dist(self.channels, state)}

    def _transform(self, signal, channels):
        return signal.mulaw_quantization(channels)


class BackgroundNoise(BaseTransform):
    def __init__(
        self,
        snr: tuple = ("uniform", 10.0, 30.0),
        csv_files: List[str] = None,
        eq_amount: tuple = ("const", 1.0),
        n_bands: int = 3,
        name: str = None,
        prob: float = 1.0,
    ):
        """
        min and max refer to SNR.
        """
        super().__init__(name=name, prob=prob)

        self.snr = snr
        self.eq_amount = eq_amount
        self.n_bands = n_bands
        self.audio_files = util.read_csv(csv_files)

    def _instantiate(self, state: RandomState, signal: AudioSignal = None):
        eq_amount = util.sample_from_dist(self.eq_amount, state)
        eq = -eq_amount * state.rand(self.n_bands)
        snr = util.sample_from_dist(self.snr, state)

        bg_path = util.choose_from_list_of_lists(state, self.audio_files)["path"]

        # Get properties of input signal to use when creating
        # background signal.
        duration = signal.signal_duration
        sample_rate = signal.sample_rate
        is_mono = signal.num_channels == 1

        bg_signal = AudioSignal.excerpt(
            bg_path, duration=duration, state=state
        ).resample(sample_rate)
        if is_mono:
            bg_signal = bg_signal.to_mono()

        return {"eq": eq, "bg_signal": bg_signal, "snr": snr}

    def _transform(self, signal, bg_signal, snr, eq):
        # Clone bg_signal so that transform can be repeatedly applied
        # to different signals with the same effect.
        return signal.mix(bg_signal.clone(), snr, eq)


class RoomImpulseResponse(BaseTransform):
    def __init__(
        self,
        drr: tuple = ("uniform", 0.0, 30.0),
        csv_files: List[str] = None,
        eq_amount: tuple = ("const", 1.0),
        n_bands: int = 6,
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)

        self.drr = drr
        self.eq_amount = eq_amount
        self.n_bands = n_bands
        self.audio_files = util.read_csv(csv_files)

    def _instantiate(self, state: RandomState, signal: AudioSignal = None):
        eq_amount = util.sample_from_dist(self.eq_amount, state)
        eq = -eq_amount * state.rand(self.n_bands)
        drr = util.sample_from_dist(self.drr, state)

        ir_path = util.choose_from_list_of_lists(state, self.audio_files)["path"]

        # Get properties of input signal to use when creating
        # background signal.
        sample_rate = signal.sample_rate
        is_mono = signal.num_channels == 1

        ir_signal = (
            AudioSignal(ir_path, duration=1.0)
            .resample(sample_rate)
            .zero_pad_to(sample_rate)
        )
        if is_mono:
            ir_signal = ir_signal.to_mono()

        return {"eq": eq, "ir_signal": ir_signal, "drr": drr}

    def _transform(self, signal, ir_signal, drr, eq):
        # Clone ir_signal so that transform can be repeatedly applied
        # to different signals with the same effect.
        return signal.apply_ir(ir_signal.clone(), drr, eq)


class VolumeChange(BaseTransform):
    def __init__(
        self,
        db: tuple = ("uniform", -12.0, 0.0),
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)
        self.db = db

    def _instantiate(self, state: RandomState):
        return {"db": util.sample_from_dist(self.db, state)}

    def _transform(self, signal, db):
        return signal.volume_change(db)


class VolumeNorm(BaseTransform):
    def __init__(
        self,
        db: float = -24,
        name: str = None,
        prob: float = 1.0,
    ):
        super().__init__(name=name, prob=prob)

        self.db = db

    def _instantiate(self, state: RandomState, signal: AudioSignal = None):
        return {"loudness": signal.metadata["file_loudness"]}

    def _transform(self, signal, loudness):
        db_change = self.db - loudness
        return signal.volume_change(db_change)


class Silence(BaseTransform):
    def __init__(self, name: str = None, prob: float = 0.1):
        super().__init__(name=name, prob=prob)

    def _transform(self, signal):
        _loudness = signal._loudness
        signal = AudioSignal(
            torch.zeros_like(signal.audio_data),
            sample_rate=signal.sample_rate,
            stft_params=signal.stft_params,
        )
        # So that the amound of noise added is as if it wasn't silenced.
        # TODO: improve this hack
        signal._loudness = _loudness

        return signal


class LowPass(BaseTransform):
    def __init__(
        self,
        cutoff: tuple = ("choice", [4000, 8000, 16000]),
        name: str = None,
        prob: float = 1,
    ):
        super().__init__(name=name, prob=prob)

        self.cutoff = cutoff

    def _instantiate(self, state: RandomState):
        return {"cutoff": util.sample_from_dist(self.cutoff, state)}

    def _transform(self, signal, cutoff):
        return signal.low_pass(cutoff)


class HighPass(BaseTransform):
    def __init__(
        self,
        cutoff: tuple = ("choice", [50, 100, 250, 500, 1000]),
        name: str = None,
        prob: float = 1,
    ):
        super().__init__(name=name, prob=prob)

        self.cutoff = cutoff

    def _instantiate(self, state: RandomState):
        return {"cutoff": util.sample_from_dist(self.cutoff, state)}

    def _transform(self, signal, cutoff):
        return signal.high_pass(cutoff)


class RescaleAudio(BaseTransform):
    def __init__(self, val: float = 1.0, name: str = None, prob: float = 1):
        super().__init__(name=name, prob=prob)

        self.val = val

    def _transform(self, signal):
        return signal.ensure_max_of_audio(self.val)