#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
import scipy.fftpack as spfft
from scipy.signal import hamming, hann, blackman
import os.path
import librosa

import Constants


def plot_stft(signal, file_name, title=None, win_length=None, hop_length=None,
              window_type=None, sample_rate=None, n_fft_bins=None,
              freq_max=None, show_interactive_plot=False):
    """ Plots a stft of signal with the given window attributes
    REWRITE AND ADD A BIT MORE DETAIL. AN EXAMPLE OF HOW YOU WOULD CALL IT WOULD BE GOOD

    Parameters:
        signal (np.array):
        file_name (str):
        num_ffts (Optional[int]): min number of desired freq. samples in (-pi,pi]. MUST be >= L. Defaults to
         int(2 ** np.ceil(np.log2(win_length)))
        freq_max (int): Max frequency to display
        window_attributes (Optional[WindowAttributes]): Contains all info about windowing for stft.
        win_length (Optional[int]): length of one window (in # of samples)
        window_type (Optional[WindowType]): window type
        win_overlap (Optional[int]): number of overlapping samples between adjacent windows
        sample_rate (int): sampling rate of the signal
        show_interactive_plot (Optional[bool]): Flag indicating if plot should be shown when function is run.
         Defaults to False

    Note:
         Either stft_params or all of [win_length, window_type, window_overlap, and num_ffts] must be provided.

    """
    sample_rate = Constants.DEFAULT_SAMPLE_RATE if sample_rate is None else sample_rate
    freq_max = Constants.MAX_FREQUENCY if freq_max is None else freq_max

    if title is None:
        title = os.path.basename(file_name)
        title = os.path.splitext(title)[0]
        title = 'Spectrogram of {}'.format(title)

    required = [win_length, hop_length, window_type]
    if any([r is None for r in required]):
        defaults = StftParams(sample_rate)

        win_length = defaults.window_length if win_length is None else win_length
        hop_length = defaults.hop_length if hop_length is None else hop_length
        window_type = defaults.window_type if window_type is None else window_type

    (stft, psd, freqs, time) = e_stft_plus(signal, win_length, hop_length, window_type, sample_rate, n_fft_bins)

    plt.close('all')

    # TODO: remove transposes!
    time_tile = np.tile(time, (len(freqs), 1))
    freq_tile = np.tile(freqs.T, (len(time), 1)).T
    sp = librosa.logamplitude(np.abs(stft) ** 2, ref_power=np.max)
    plt.pcolormesh(time_tile, freq_tile, sp)

    plt.axis('tight')
    plt.xlabel('Time (sec)')
    plt.ylabel('Frequency (Hz)')
    plt.title(title)
    plt.ylim(freqs[0], freq_max)

    plt.savefig(file_name)

    if show_interactive_plot:
        plt.interactive('True')
        plt.show()


def e_stft(signal, window_length, hop_length, window_type, n_fft_bins=None, remove_reflection=True):
    """
    This function computes a short time fourier transform (STFT) of a 1D numpy array input signal.
    This will zero pad the signal by half a hop_length at the beginning to reduce the window
    tapering effect from the first window. It also will zero pad at the end to get an integer number of hops.
    By default, this function removes the FFT data that is a reflection from over Nyquist. There is an option
    to suppress this behavior and have this function include data from above Nyquist, but since the
    inverse STFT function, e_istft(), expects data without the reflection, the onus is on the user to remember
    to set the reconstruct_reflection flag in e_istft() input.

    Args:
        signal: 1D numpy array containing audio data. (REAL?COMPLEX?INTEGER?)
        window_length: (int) number of samples per window
        hop_length: (int) number of samples between the start of adjacent windows, or "hop"
        window_type: (string) type of window to use. Using WindowType object is recommended.
        n_fft_bins: (int) (Optional) number of fft bins per time window.
        If not specified, defaults to next highest power of 2 above window_length
        remove_reflection: (bool) (Optional) if True, this will remove reflected STFT data above the Nyquist point.
        If not specified, defaults to True.

    Returns:
        2D  numpy array with complex STFT data.
        Data is of shape (num_time_blocks, num_fft_bins). These numbers are determined by length of the input signal,
        on internal zero padding (explained at top), and n_fft_bins/remove_reflection input (see example below).

    Examples:
        ::
        # Set up sine wave parameters
        sr = nussl.Constants.DEFAULT_SAMPLE_RATE # 44.1kHz
        n_sec = 3 # seconds
        duration = n_sec * sr
        freq = 300 # Hz

        # Make sine wave array
        x = np.linspace(0, freq * 2 * np.pi, duration)
        x = np.sin(x)

        # Set up e_stft() parameters
        win_type = nussl.WindowType.HANN
        win_length = 2048
        hop_length = win_length / 2

        # Run e_stft()
        stft = nussl.e_stft(x, win_length, hop_length, win_type)
        # stft has shape (win_length // 2 + 1 , duration / hop_length)

        # Get reflection
        stft_with_reflection = nussl.e_stft(x, win_length, hop_length, win_type, remove_reflection=False)
        # stft_with_reflection has shape (win_length, duration / hop_length)

        # Change number of fft bins per hop
        num_bins = 4096
        stft_more_bins = e_stft(x, win_length, hop_length, win_type, n_fft_bins=num_bins)
        # stft_more_bins has shape (num_bins // 2 + 1, duration / hop_length)
    """
    if n_fft_bins is None:
        n_fft_bins = int(2 ** np.ceil(np.log2(window_length)))

    orig_signal_length = len(signal)

    # zero-pad the vector at the beginning and end to reduce the window tapering effect
    if window_length % 2 == 0:
        zero_pad1 = np.zeros(window_length / 2)
    else:
        zero_pad1 = np.zeros((window_length - 1) / 2)
    signal = np.concatenate((zero_pad1, signal, zero_pad1))

    # another zero pad if not integer multiple of hop_length
    zero_pad2_len = 0
    if orig_signal_length % hop_length != 0:
        zero_pad2_len = hop_length - (orig_signal_length % hop_length)
        signal = np.concatenate((signal, np.zeros(zero_pad2_len)))

    window = make_window(window_type, window_length)

    # figure out size of output stft
    num_blocks = int(((len(signal) - window_length) / hop_length + 1))
    stft_bins = n_fft_bins / 2 + 1 if remove_reflection else n_fft_bins  # only want just over half of each fft

    # this is where we do the stft calculation
    stft = np.zeros((num_blocks, stft_bins), dtype=complex)
    for hop in range(num_blocks):
        start = hop * hop_length
        end = start + window_length
        unwindowed_signal = signal[start:end]
        windowed_signal = np.multiply(unwindowed_signal, window)
        fft = spfft.fft(windowed_signal, n=n_fft_bins)
        stft[hop,] = fft[0:stft_bins]

    # reshape the 2d array, so it's how we expect it.
    stft = stft.T
    if remove_reflection:
        first = int(len(zero_pad1) / hop_length)
        last = stft.shape[1] - int((len(zero_pad1) + zero_pad2_len) / hop_length)
        stft = stft[:, first: last]

    return stft


def e_istft(stft, window_length, hop_length, window_type, reconstruct_reflection=True, remove_padding=False):
    """
    Computes an inverse short time fourier transform (STFT) from a 2D numpy array of complex values. By default
    this function assumes input STFT has no reflection above Nyquist and will rebuild it, but the
    reconstruct_reflection flag overrides that behavior.

    Args:
        stft: complex valued 2D numpy array containing STFT data
        window_length: (int) number of samples per window
        hop_length: (int) number of samples between the start of adjacent windows, or "hop"
        window_type: (deprecated)
        reconstruct_reflection: (bool) (Optional) if True, this will recreate the removed reflection
        data above the Nyquist. If False, this assumes that the input STFT is complete. Default is True.
        remove_padding: (bool) (Optional) if True, this function will remove the first and
        last (window_length - hop_length) number of samples. Defaults to False.

    Returns:
        1D numpy array containing an audio signal representing the original signal used to make stft

    Examples:
        ::
        # Set up sine wave parameters
        sr = nussl.Constants.DEFAULT_SAMPLE_RATE # 44.1kHz
        n_sec = 3 # seconds
        duration = n_sec * sr
        freq = 300 # Hz

        # Make sine wave array
        x = np.linspace(0, freq * 2 * np.pi, duration)
        x = np.sin(x)

        # Set up e_stft() parameters
        win_type = nussl.WindowType.HANN
        win_length = 2048
        hop_length = win_length / 2

        # Get an stft
        stft = nussl.e_stft(x, win_length, hop_length, win_type)

        calculated_signal = nussl.e_istft(stft, win_length, hop_length)
    """
    n_hops = stft.shape[1]
    signal_length = (n_hops - 1) * hop_length + window_length
    signal = np.zeros(signal_length)

    # Add reflection back
    if reconstruct_reflection:
        reflection = stft[-2:0:-1, :]
        reflection = reflection.conj()
        stft = np.vstack((stft, reflection))

    for n in range(n_hops):
        start = n * hop_length
        end = start + window_length
        signal[start:end] = signal[start:end] + np.real(spfft.ifft(stft[:, n]))

    # remove zero-padding
    if remove_padding:
        start = window_length - hop_length
        stop = signal_length - (window_length - hop_length)
        signal = signal[start:stop]

    return signal


def e_stft_plus(signal, window_length, hop_length, window_type, sample_rate, n_fft_bins=None):
    """
    Does a short time fourier transform (STFT) of the signal (by calling e_stft() ), but also calculates
    the power spectral density (PSD), frequency and time vectors for the calculated STFT.
    :param signal:
    :param window_length:
    :param hop_length:
    :param window_type:
    :param sample_rate:
    :param n_fft_bins:
    :return:

    MAKE MORE LIKE THE AWESOME e_stft DOCUMENTATION
    """
    if n_fft_bins is None:
        n_fft_bins = window_length

    stft = e_stft(signal, window_length, hop_length, window_type, n_fft_bins)
    frequency_vector = (sample_rate / 2) * np.linspace(0, 1, (n_fft_bins / 2) + 1)

    time_vector = np.array(range(stft.shape[1]))
    hop_in_secs = hop_length / (1.0 * sample_rate)
    time_vector = np.multiply(hop_in_secs, time_vector)

    window = make_window(window_type, window_length)
    win_dot = np.dot(window, window.T)
    psd = np.zeros_like(stft, dtype=float)
    for i in range(psd.shape[1]):
        psd[:, i] = (1 / float(sample_rate)) * ((abs(stft[:, i]) ** 2) / float(win_dot))

    return stft, psd, frequency_vector, time_vector


def make_window(window_type, length):
    """Returns an np array of type window_type

    Parameters:
        window_type (WindowType): Type of window to create, window_type object
        length (int): length of window
    Returns:
         window (np.array): np array of window_type
    """

    # Generate samples of a normalized window
    if window_type == WindowType.RECTANGULAR:
        return np.ones(length)
    elif window_type == WindowType.HANN:
        return hann(length, False)
    elif window_type == WindowType.BLACKMAN:
        return blackman(length, False)
    elif window_type == WindowType.HAMMING:
        # return np.hamming(length)
        return hamming(length, False)
    else:
        return None


class WindowType:
    RECTANGULAR = 'rectangular'
    HAMMING = 'hamming'
    HANN = 'hann'
    BLACKMAN = 'blackman'
    DEFAULT = HAMMING

    all_types = [RECTANGULAR, HAMMING, HANN, BLACKMAN]

    def __init__(self):
        pass


class StftParams(object):
    """
    The StftParams class is a container for information needed to run an STFT or iSTFT.
    This is meant as a convenience and does not actually perform any calculations within. It should
    get "decomposed" by the time e_stft() or e_istft() are called, so that every attribute in this
    object is a parameter to one of those functions.

    Every class that inherits from the SeparationBase class has an StftParms object, and this
    is the only way that a top level user has access to the STFT parameter settings that
    all of the separation algorithms are built upon.
    This object will get passed around instead of each of these individual attributes.

    ARE THESE PARAMETERS OBVIOUS? HOW WILL THE DEVELOPER KNOW WHAT PARAMETERS ARE HERE AND WHAT VALUES  ARE ALLOWED?
    """

    def __init__(self, sample_rate, window_length=None, hop_length=None, window_type=None, n_fft_bins=None):
        self.sample_rate = sample_rate

        # default to 40ms windows
        default_win_len = int(2 ** (np.ceil(np.log2(Constants.DEFAULT_WIN_LEN_PARAM * sample_rate))))
        self._window_length = default_win_len if window_length is None else window_length
        self._hop_length = self._window_length / 2 if hop_length is None else hop_length
        self.window_type = WindowType.DEFAULT if window_type is None else window_type
        self._n_fft_bins = self._window_length if n_fft_bins is None else n_fft_bins

        self._hop_length_needs_update = True
        self._n_fft_bins_needs_update = True

        if hop_length is not None:
            self._hop_length_needs_update = False

        if n_fft_bins is not None:
            self._n_fft_bins_needs_update = False

    @property
    def window_length(self):
        return self._window_length

    @window_length.setter
    def window_length(self, value):
        """
        Length of window ? WINDOW FOR WHAT? WHAT USES THIS?  in samples. If window_overlap or num_fft are not set manually,
        then changing this will update them to hop_length = window_length / 2, and
        and num_fft = window_length
        :param value:
        :return:
        """
        self._window_length = value

        if self._n_fft_bins_needs_update:
            self._n_fft_bins = value

        if self._hop_length_needs_update:
            self._hop_length = value / 2

    @property
    def hop_length(self):
        return self._hop_length

    @hop_length.setter
    def hop_length(self, value):
        self._hop_length_needs_update = False
        self._hop_length = value

    @property
    def n_fft_bins(self):
        return self._n_fft_bins

    @n_fft_bins.setter
    def n_fft_bins(self, value):
        """
        Number of FFT bins per stft window.
        By default the number of FFT bins is equal to window_length (value of window_length),
        but if this is set manually then when e_stft takes a window of length
        WHAT HAPPENS IF THIS VALUE IS BELOW THE LENGTH OF THE WINDOW??.
        :param value:
        :return:
        """
        self._n_fft_bins_needs_update = False
        self._n_fft_bins = value

    @property
    def window_overlap(self):
        return self.window_length - self.hop_length
