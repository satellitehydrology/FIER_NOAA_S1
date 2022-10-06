import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.colors
import requests
import datetime as dt
import pandas as pd
import copy
#from scipy import interpolate
class  expFitHydrology:
    def __init__(self):
        pass
    def calParameter(self,x,yR):
        x=np.array(x).reshape([-1,1])
        yR=np.array(yR).reshape([-1,1])
        a0=0.1
        b0=0.1
        c0=-0.1
        d0=0.1

        addV=100
        c0_cat=[]
        addV_cat=[]
        dataSize=x.size
        A=np.zeros([dataSize,3])
        A[:,0:1]=1
        #x_d=np.arange(-4,-0.1,0.1)

        while sum(abs(addV))>0.0000001:
            A[:,1:2]=x*np.exp(c0*x+d0)
            A[:,2:3]=exp(c0*x+d0)
            
            w=yR-(b0+exp(c0*x+d0))
            addV=inv(A.T.dot(A)).dot(A.T.dot(w))
            
            #a0=a0+addV[0]/dataSize
            b0=b0+addV[0]/dataSize
            c0=c0+addV[1]/dataSize
            d0=d0+addV[2]/dataSize
            #print([b0,c0,d0])
        self.x=x
        self.yR=yR
        self.result=np.concatenate([b0,c0,d0])
    def importParameter(self,result):
        self.result=result
    def __str__(self): 
        return str(self.result)
    def __repr__(self): 
        return str(self.result)
    def __call__(self, x_d):
        return self.result[0]+exp(self.result[1]*x_d+self.result[2])


def synGenerate(eof_result,eof_mean,modalList,hist_q_stack,dry_mean,dry_std):
    modeN=eof_result.dims['mode']
    syn_sar=copy.deepcopy(eof_mean)
    
    for ct_mode in range(modeN):
        sm=eof_result[dict(mode=ct_mode)]
        site = str(sm.hydro_site.data.tolist())
        hydro_single = hist_q_stack[site]
        in_model = np.poly1d(modalList[ct_mode])
        #hydro_single=40000
        est_tpc = in_model(hydro_single)
        print(est_tpc)
        syn_sar = syn_sar + sm.spatial_modes*est_tpc
    syn_sar.name= 'intensity'  
    return syn_sar
def getHydro(xr_RSM,doi,in_run_type):
    siteList=list(set(xr_RSM.hydro_site.data.tolist()))
    siteList=[ str(i) for i in siteList]
    hist_q_stack={}  
    for site in siteList:
        exp_fct = requests.get('https://nwmdata.nohrsc.noaa.gov/latest/forecasts/'+in_run_type+'/streamflow?&station_id='+str(site)).json()
        fct_datetime = pd.to_datetime(pd.DataFrame(exp_fct[0]['data'])['forecast-time'])
        doi_indx0 = fct_datetime >= (dt.datetime.strptime(doi,'%Y-%m-%d'))
        doi_indx1 = (fct_datetime < (dt.datetime.strptime(doi,'%Y-%m-%d'))+dt.timedelta(days=1))
        doi_indx = doi_indx0 & doi_indx1
        doi_fct_datetime = fct_datetime[doi_indx]
        doi_fct_q = (pd.DataFrame(exp_fct[0]['data'])['value'][doi_indx]*0.0283168).mean()
        hist_q_stack[site]=doi_fct_q
    return hist_q_stack
def getTPCF(xr_RSM,model_path):
    modeN=xr_RSM.dims['mode']
    modePath=[model_path+'/'+str(i)+'.npy' for i in range(modeN)]
    modalList=[np.load(i) for i in modePath]
    return modalList
def run_fier(AOI_str, doi, in_run_type,thSelect):

    # Path to read ncecesary data
    model_path = 'AOI/'+AOI_str+'/model/'
    RSM_folder = 'AOI/'+AOI_str+'/RSM/'

    # forecast_q_path = 'AOI/'+AOI_str+'/hydrodata/mid_fct_2019_2021_0024.nc'
    

    xr_RSM=xr.open_dataset(RSM_folder+'RSM_hydro.nc')
    eof_mean = xr.open_dataarray(RSM_folder+'RSM_MEAN.nc')
    dry_mean=xr.open_dataarray(RSM_folder+'dry_MEAN.nc')
    dry_std=xr.open_dataarray(RSM_folder+'dry_STD.nc')
    
    if in_run_type=='archive':
        hist_q_stack=xr.load_dataarray('AOI/'+AOI_str+'/Q/Q.nc').sel(time=str(doi))
        siteN=hist_q_stack.site.data.tolist()
        QList=hist_q_stack.data.tolist()
        hist_q_stack={}
        for i in range(len(siteN)):
            hist_q_stack[str(siteN[i])]=QList[i]
    else:
        hist_q_stack=getHydro(xr_RSM,doi,in_run_type)
    modelList=getTPCF(xr_RSM,model_path)
    
    
    syn_wf_fct=synGenerate(xr_RSM,eof_mean,modelList,hist_q_stack,dry_mean,dry_std)
    #syn_wf_fct = syn_wf_fct.to_dataset()
    syn_wf_fct=(syn_wf_fct-dry_mean)/dry_std

    xr_RSM.close()
    eof_mean.close()
    dry_std.close()
    # Create image
    folder_name = 'Output'

    
    syn_wf_fct.data[syn_wf_fct.data<=thSelect]=-3
    syn_wf_fct.data[syn_wf_fct.data>thSelect]=-1
    fig = plt.figure()
    plt.imshow(syn_wf_fct.data, cmap=matplotlib.colors.ListedColormap(['blue', 'gray']), vmin=-3, vmax=-1,interpolation='none')
    plt.axis('off')
    plt.savefig(folder_name +'/water_fraction.png', bbox_inches='tight', dpi=300, pad_inches = 0)
    plt.close()

    bounds = [[syn_wf_fct.lat.values.min(), syn_wf_fct.lon.values.min()],
    [syn_wf_fct.lat.values.max(), syn_wf_fct.lon.values.max()]]

    out_file = xr.Dataset(
            {
                "Water Fraction Map": (
                    syn_wf_fct.dims,
                    syn_wf_fct.data
                                ),
            },
            coords = syn_wf_fct.coords,
        )

    out_file.to_netcdf(folder_name +'/output.nc')


    return bounds
