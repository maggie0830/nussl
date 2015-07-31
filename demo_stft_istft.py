# In this demo two sound sources are superimposed synthesize a mixture. 
# A mask is generated by thresholding the spectrogram of one of 
# the two sources and used to separate the source from the mixture. 
# Separated sources are then transformed back to the time domain.

import matplotlib.pyplot as plt
import numpy as np
from scikits.audiolab import wavread
from scikits.audiolab import play
from f_stft import f_stft
from f_istft import f_istft


# Load the audio files
s1, fs, enc = wavread('K0140.wav'); play(s1,fs)
s2, fs, enc = wavread('K0149.wav'); play(s2,fs)

Ls=np.array([len(s1),len(s2)]); Ls=Ls.min();
s1=np.mat(s1[0:Ls]); s2=np.mat(s2[0:Ls]);
ts=np.mat(np.arange(Ls)/float(fs))

x=s1+s2;

# Generate spectrograms
L=2048;
win='Hamming'
ovp=0.5*L
nfft=L
mkplot=1
fmax=5000;

plt.figure(1);  plt.title('Source 1');
S1,Ps1,F,T = f_stft(s1,L,win,ovp,nfft,fs,mkplot,fmax); 

plt.figure(2);  plt.title('Source 2');
S2,Ps2,F,T = f_stft(s2,L,win,ovp,nfft,fs,mkplot,fmax);

plt.figure(3);  plt.title('Mixture');
X,Px,F,T = f_stft(x,L,win,ovp,nfft,fs,mkplot,fmax);


# Make a mask
Ps1=Ps1/Ps1.max();
M=Ps1>=0.0001;

plt.figure(4)
TT=np.tile(T,(len(F),1))
FF=np.tile(F.T,(len(T),1)).T
plt.pcolormesh(TT,FF,M)
plt.xlabel('Time')
plt.ylabel('Frequency')
plt.ylim(0,fmax)
plt.show()


# Separate by masking
SM1=M*X
SM2=(1-M)*X

plt.figure(5)
plt.subplot(2,1,1)
SP1=10*np.log10(np.abs(Px))*M
plt.pcolormesh(TT,FF,SP1)
plt.xlabel('Time')
plt.ylabel('Frequency')
plt.ylim(0,fmax)
plt.show()

plt.subplot(2,1,2)
SP2=10*np.log10(np.abs(Px))*(1-M)
plt.pcolormesh(TT,FF,SP2)
plt.xlabel('Time')
plt.ylabel('Frequency')
plt.ylim(0,fmax)
plt.show()

# Convert to time series
sm1,t1 = f_istft(SM1,L,win,ovp,nfft,fs)
sm2,t2 = f_istft(SM2,L,win,ovp,nfft,fs)

# plot and play the separated time signals
play(sm1,fs)
play(sm2,fs)

plt.figure(7)
plt.subplot(2,1,1)
plt.title('Time-domain Audio Signal')
plt.plot(t1,sm1,'b-')
plt.plot(ts.T,s1.T,'r-')
plt.xlabel('t(sec)')
plt.ylabel('s_1(t)')
plt.legend(['estimated','original'])
plt.show()

plt.subplot(2,1,2)
plt.title('Time-domain Audio Signal')
plt.plot(t2,sm2,'b-')
plt.plot(ts.T,s2.T,'r-')
plt.xlabel('t(sec)')
plt.ylabel('s_2(t)')
plt.legend(['estimated','original'])
plt.show()






