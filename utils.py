import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import timedelta
import scipy.signal as signal

def compute_stats(df_ch1, df_ch2, df_ch3, df_ch4):
    """
    Compute statistics on the signal and noise for each channel
    """
    def stats(df):
        stats = {}
        stats['mean_signal'] = df['signal'].mean()
        stats['std_signal'] = df['signal'].std()
        stats['mean_noise'] = df['noise'].mean()
        stats['std_noise'] = df['noise'].std()
        return stats
    
    return stats(df_ch1), stats(df_ch2), stats(df_ch3), stats(df_ch4)

def low_pass_filters(b, a, df_ch1, df_ch2, df_ch3, df_ch4):
    
    def lpf(b, a, sig):
        return signal.filtfilt(b, a, sig)
    
    return lpf(b, a, df_ch1['signal'].values), lpf(b, a, df_ch2['signal'].values), lpf(b, a, df_ch3['signal'].values), lpf(b, a, df_ch4['signal'].values)

def flagging(filtered_signals, df_ch1, df_ch2, df_ch3, df_ch4, stats):
    
    def flag(filtered_signal, df, idx):
        filtered_signal[df['flag'] != 0] = None # stats[idx]['mean_signal']
            
        return filtered_signal
    
    return flag(filtered_signals[0], df_ch1, 0), flag(filtered_signals[1], df_ch2, 1), flag(filtered_signals[2], df_ch3, 2), flag(filtered_signals[3], df_ch4, 3)

def load_data(src_dir,name):
    """
    Load .h5 Alphasat data, located in src_dir
    """
    def read_hdf(src_dir,name,n_channel):
        df = pd.read_hdf(os.path.join(src_dir,"{}_ch{}.h5".format(name,n_channel)))
        df = df.set_index('time')
        return df
    
    return read_hdf(src_dir,name,1), read_hdf(src_dir,name,2), read_hdf(src_dir,name,3), read_hdf(src_dir,name,4)



def add_flags(df_event, df_ch1, df_ch2, df_ch3, df_ch4):
    """
    Add flag to the channel dataframes:
        - flag 0: no event
        - flag 1: rain event
        - flag 2: failure
    """
    def flag(df_event,df):
        df['flag'] = np.zeros_like(df['signal'],dtype=int)
        for i in range(0,len(df_event)):
            time_start = pd.to_datetime(df_event.loc[i]['DATE'], format='%Y-%m-%d') + pd.to_timedelta(df_event.loc[i]['TIME START'])
            time_stop = pd.to_datetime(df_event.loc[i]['DATE'], format='%Y-%m-%d') + pd.to_timedelta(df_event.loc[i]['TIME STOP']) 

            if df_event.loc[i]['EVENT'] == 'rain': # set flag 1 for rain
                idx = (df.index>=time_start) & (df.index <time_stop)
                df.loc[idx,'flag'] = 1
            if df_event.loc[i]['EVENT'] == 'failure': # set flag 2 for failure
                idx = (df.index>=time_start) & (df.index <time_stop)
                df.loc[idx,'flag'] = 2
        return df
    
    return flag(df_event,df_ch1), flag(df_event,df_ch2), flag(df_event,df_ch3), flag(df_event,df_ch4)
    
    
    
def plot_one_day_4ch(date, df_ch1, df_ch2, df_ch3, df_ch4, bool_save = False):
    """
    Plot time series for one day (midnight to midnight)
    """
    
    # Crop dataframe to the date of interest
    df_ch1 = df_ch1[(df_ch1.index>=date) & (df_ch1.index < (date+timedelta(days = 1)))]
    df_ch2 = df_ch2[(df_ch2.index>=date) & (df_ch2.index < (date+timedelta(days = 1)))]
    df_ch3 = df_ch3[(df_ch3.index>=date) & (df_ch3.index < (date+timedelta(days = 1)))]
    df_ch4 = df_ch4[(df_ch4.index>=date) & (df_ch4.index < (date+timedelta(days = 1)))]
    
    fig, axs = plt.subplots(2,2,figsize=(12,10))
    for i in range(0,4):
        if i==0:
            axs[i%2,i//2].set_title("ch1: x-polar 39.4 GHz")
            df = df_ch1
        elif i==1:
            axs[i%2,i//2].set_title("ch2: co-polar 39.4 GHz")
            df = df_ch2
        elif i==2:
            axs[i%2,i//2].set_title("ch3: x-polar 19.7 GHz")
            df = df_ch3
        elif i==3:
            axs[i%2,i//2].set_title("ch4: co-polar 19.7 GHz")
            df = df_ch4
            
        time = df.index
        signal = df['signal']
        noise = df['noise']
  
        axs[i%2,i//2].plot(time,signal)
        axs[i%2,i//2].plot(time,noise,color="gray")
        axs[i%2,i//2].grid()
        axs[i%2,i//2].set_ylim(-50,20)
        axs[i%2,i//2].set_ylabel("Power [dB]")
        axs[i%2,i//2].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        # Show rain events & determine start and stop times of rain event during the day
        idx_start = []
        idx_stop = []
        if df['flag'][0] == 1: #if rain at the start of the day
            idx_start.append(0)
        for idx in np.where(np.diff(df['flag'].values) == True)[0]: #find index of 0 to 1 transitions in flags
            idx_start.append(idx) 
        for idx in np.where(-np.diff(df['flag'].values) == True)[0]: #find index of 1 to 0 transitions in flags
            idx_stop.append(idx) 
        if df['flag'][-1] == 1: #if rain at the end of the day
            idx_stop.append(len(df['flag'])-1)
            
        for k in range(0,len(idx_start)):
            axs[i%2,i//2].axvspan(df.index[idx_start[k]],df.index[idx_stop[k]], color='red', alpha=0.25)
            
        # Show failure events
        idx_start = []
        idx_stop = []
        flag_failure = np.copy(df['flag'].values)
        flag_failure[flag_failure<=1] = 0
        flag_failure = flag_failure / 2
        if flag_failure[0] == 1: 
            idx_start.append(0)
        for idx in np.where(np.diff(flag_failure) == True)[0]: #find index of 0 to 2 transitions in flags
            idx_start.append(idx) 
        for idx in np.where(-np.diff(flag_failure) == True)[0]: #find index of 2 to 0 transitions in flags
            idx_stop.append(idx) 
        if flag_failure[-1] == 1: 
            idx_stop.append(len(df['flag'])-1)
            
        for k in range(0,len(idx_start)):
            axs[i%2,i//2].axvspan(df.index[idx_start[k]],df.index[idx_stop[k]], color='grey', alpha=0.25)
            
    fig.suptitle("Alphasat received data at LLN for "+ date.strftime('%Y-%m-%d'),fontsize=14)
    
    if bool_save:
        fig.savefig('figures/'+date.strftime('%Y_%m_%d')+'.png')
        
def plot_RAPIDS_outputs(rapids_data,title):
    """
    Plot RAPIDS attenuation from the rapids_data dataframe. The dataframe must contain a "PROBABILITY" and a "ATTENUATION" field.
    """
    plt.figure()
    for i in range(0,18):
        plt.semilogx(rapids_data["PROBABILITY"].values[i*26:(i+1)*26],rapids_data["ATTENUATION"].values[i*26:(i+1)*26],label="{}°".format((i+1)*5))
    plt.grid()
    plt.title(title)
    plt.xlim(1e-3,100)
    plt.legend()