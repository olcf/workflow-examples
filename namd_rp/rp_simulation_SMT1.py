#!/usr/bin/env python3

__author__    = 'RADICAL-Cybertools Team'
__email__     = 'info@radical-cybertools.org'
__copyright__ = 'Copyright 2023, The RADICAL-Cybertools Team'
__license__   = 'MIT'

import os

import radical.pilot as rp
import radical.utils as ru
import sys

report = ru.Reporter(name='radical.pilot')
report.title('Getting Started (RP version %s)' % rp.version)


N_NODES = 1

PILOT_DESCRIPTION = {
    'resource' : 'ornl.frontier',
    'project'  : 'STF006',
    'nodes'    : N_NODES,
    'cores'    : 48*N_NODES,
    'gpus'     : 8*N_NODES,
    'runtime'  : 10,
    'sandbox'  : '/lustre/orion/stf006/scratch/dilipa/rp/'
}

os.environ['RADICAL_SMT'] = '1'


#Application specific 
rootdir='/lustre/orion/stf006/scratch/dilipa/FreshBuild/namd/NAM31A1'
exe=rootdir+'/NAMD_3.1alpha1_Linux-x86_64-multicore-HIP/namd3'
#
prelaunch_cmd=[ "module load PrgEnv-gnu",\
                "module load rocm/5.7.0",\
                "module load cray-fftw",\
                "module load craype-accel-amd-gfx90a"
               ]

#List all task directories

ncases = 7
cwd = os.getcwd()+'/'  
taskDirs=['G0.0254','G0.1292','G0.2971','G0.5000','G0.7029','G0.8708','G0.9746']

# For dynamics with NAMD (MultiCore HIP build)
# We will assign 7 cores and closest GPU to NAMD

ranks=1
cores=7
gpus=1
cpus=1

def main():
    session = rp.Session()
    try:
        pmgr = rp.PilotManager(session=session)
        
        pilot = pmgr.submit_pilots(rp.PilotDescription(PILOT_DESCRIPTION))

        client_sandbox = ru.Url(pilot.client_sandbox).path + '/' + session.uid
        pilot_sandbox  = ru.Url(pilot.pilot_sandbox).path

        print('client sandbox: %s' % client_sandbox)
        print('pilot  sandbox: %s' % pilot_sandbox)

        report.header('submit pilot')
        tmgr = rp.TaskManager(session=session)
        tmgr.add_pilots(pilot) 
        tds = []

        for task_i in taskDirs: 
            td = rp.TaskDescription()
            td.ranks            = ranks 
            td.cores_per_rank   = cores
            td.gpus_per_rank    = gpus

            print("ranks = "+str(td.ranks))
            print("cores_per_rank = "+str(td.cores_per_rank))
            print("gpus_per_rank = "+str(td.gpus_per_rank))
            print()        

            td.pre_launch  = prelaunch_cmd +['pwd','cd '+cwd+task_i]

            # For each instance of the ensemble run, we assign only 5 Cores for actual execution
            # Out of 7 cores, we assign 1 core for CPU management and 1 for GPU management
            # using the remaining 5 for the NAMD job

            td.executable = exe + " +p5 +setcpuaffinity +devices 0 "+cwd+task_i+'/'+"prod.namd > prod.log"

            #Print exe for sanity check
            
            print(td.executable)

            tds.append(td)
            report.progress()


        report.progress_done()

        tasksSub=tmgr.submit_tasks(tds)
        tmgr.wait_tasks()

        for task in tasksSub:
           print('%s: %s' % (task.uid, task.state))

        report.header('finalize')


    finally:
        session.close(download=True)


if __name__ == '__main__':

    os.environ['RADICAL_PROFILE'] = 'TRUE'
    # for test purposes
    os.environ['RADICAL_LOG_LVL'] = 'DEBUG'

    main()

