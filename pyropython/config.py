# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 09:49:36 2018

@author: tstopi
"""
import sys
import yaml as y
from pandas import read_csv
from numpy import array,newaxis,squeeze
from scipy import signal
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern,WhiteKernel,RBF

class Config:
    num_jobs    = 1
    max_iter    = 50 
    num_points  = 100
    num_initial = 100
    raw_data    = {}
    exp_data    = {}
    simulation  = {}
    experiment  = {}
    objective_func = "RMSE"
    data_weights = None
    fname       = None
    fds_command = None
    optimizer_opts = {"base_estimator":       "ET",
                      "acq_func":             "gp_hedge",
                      "acq_optimizer":        "auto",
                      "n_initial_points":      100,
                      "acq_optimizer_kwargs":  {"n_points": 10000, "n_restarts_optimizer": 5,
                                              "n_jobs": 1},
                      "acq_func_kwargs":       {"xi": 0.01, "kappa": 1.96}
                      };
    filtering_options= {}

    def  __init__(self, fname):
        self.parse_input(fname)
        self._proc_input()
        self.fname = fname

    def _proc_input(self):
        for key in self.simulation:
            if not key in self.experiment:
                sys.exit("No experimental data for variable %s" % key)
        for key in self.experiment:
            if not key in self.simulation:
                sys.exit("No simulation data for variable %s" % key)
        for key,(fname,dname,conversion_factor) in self.experiment.items():
            tmp=read_csv(fname,header=1,encoding = "latin-1",index_col=False)
            tmp.columns = [colname.split('(')[0].strip() for colname in tmp.columns]
            tmp=tmp.dropna(axis=1,how='any')
            dat = self.filter(array(tmp['Time']),array(tmp[dname]))
            self.raw_data[key]=(array(tmp['Time']),array(tmp[dname]*conversion_factor))
            self.exp_data[key]=(array(tmp['Time']),array(dat*conversion_factor))
        if self.data_weights:
            if set(self.data_weights) != set(self.simulation):
                print("Need to define weights for all variables in 'experiment' and 'simulation':")
                print(set(self.data_weights).symmetric_difference(set(self.simulation)))
                sys.exit(0)
        if not self.data_weights:
            self.data_weights={}
            for key in self.experiment:
                self.data_weights[key]=1.0


    def parse_input(self,fname):
        lines=open(fname,"r").read()
        # extract config block
        # bloc starts with #start_config
        # and ends with #end_config
        try:
            start = lines.index("#start_config")
            end = lines.index("#end_config")
        except: 
            sys.exit("Error reading config.")
        config = y.load(lines[start:end])
        # check sanity of input
        if not 'variables' in config:
            sys.exit("Need to define independent variables and bounds.")
        if not 'simulation' in config:
            sys.exit("Need to define datafiles.") 
        if not 'experiment' in config:
            sys.exit("Need to define target variables.") 
        self.simulation = config['simulation']
        self.experiment = config['experiment']
        self.variables  = list(config['variables'].items())
        self.max_iter=config.get("max_iter",50)
        self.num_jobs=config.get("num_jobs",-1)
        self.num_points=config.get("num_points",1)
        self.num_initial=config.get("num_initial",1) 
        self.optimizer_opts["n_initial_points"]=self.num_initial
        self.optimizer_opts["acq_optimizer_kwargs"]["n_jobs"]=1
        self.optimizer_opts["acq_optimizer_kwargs"]["n_restarts_optimizer"]=self.num_jobs
        self.fds_command=config.get("fds_command","fds") 
        self.optimizer_opts=config.get("optimizer",self.optimizer_opts)
        obj = config.get("objective",None)
        if obj:
            self.objective_func = obj.get("objective_func","RMSE")
            self.data_weights   = obj.get("data_weights",None)
        self._proc_input()

    
    def filter(self, x,y):
        kernel =  1.0*Matern(length_scale=20.0, length_scale_bounds=(1e-1, 1000.0),nu=2.5) \
                  + WhiteKernel(noise_level=5.0, noise_level_bounds=(1e-1, 1000.0))
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=0,alpha=0.0)
        gp.fit(x[:,newaxis],y[:,newaxis])
        return squeeze(gp.predict(x[:,newaxis]))

if __name__=="__main__":
    fname=sys.argv[1]
    cfg = Config(fname)
    print(cfg.num_jobs)
    print(len(cfg.exp_data))
