#!/usr/bin/env python3

__author__    = 'Henry Monge-Camacho'
__email__     = 'mongecamachj@ornl.gov'

import os
import radical.pilot as rp
import radical.utils as ru
from setup_tasks_example import *
import sys
from datetime import datetime
import queue

os.environ['RADICAL_PROFILE'] = 'TRUE'
os.environ['RADICAL_LOG_LVL'] = 'DEBUG'

report = ru.Reporter(name='radical.pilot')
report.title('Getting Started (RP version %s)' % rp.version)

N_NODES = 1

PILOT_DESCRIPTION = {
    'resource' : 'ornl.frontier',
    'project'  : 'STF006',
    'nodes'    : N_NODES,
    'cores'    : 48*N_NODES,
    'gpus'     : 8*N_NODES,
    'runtime'  : 20,
}


# Define paths
os.environ['RADICAL_SMT'] = '1'
session = rp.Session()

#Create the tasks to run

ensemble_path=os.path.abspath(os.getcwd()) #Path were data and output files will be stored, modify as you wish.
#make_ensemble_tasks(LatticeExtentInSpace,LatticeExtentInTime,Configurations,session.uid,ensemble_path)
tasks,priorities=make_ensemble_tasks(4,8,5,session.uid,ensemble_path)

def main():
    try:
        pmgr = rp.PilotManager(session=session)
        
        pilot = pmgr.submit_pilots(rp.PilotDescription(PILOT_DESCRIPTION))
        client_sandbox = ru.Url(pilot.client_sandbox).path + '/' + session.uid
        pilot_sandbox  = ru.Url(pilot.pilot_sandbox).path

        print('client sandbox: %s' % client_sandbox)
        print('pilot  sandbox: %s' % pilot_sandbox)
        
        tmgr = rp.TaskManager(session=session)
        pilot.wait(rp.PMGR_ACTIVE)
        tmgr.add_pilots(pilot)

        #No dependencies? Turn on next 4 lines
        #sub_tasks = tmgr.submit_tasks(tasks) 
        #tmgr.wait_tasks()
        #for task in sub_tasks:
        #   print('%s: %s' % (task.uid, task.state))

        #Dependencies Turn on next line
        launch_tasks(tmgr,tasks,PILOT_DESCRIPTION,priorities)
    
        report.progress_done()
        report.header('finalize')

    finally:
        print(datetime.now().strftime("%H:%M:%S"))
        session.close(download=True)


if __name__ == '__main__':

    os.environ['RADICAL_PROFILE'] = 'TRUE'
    # for test purposes
    os.environ['RADICAL_LOG_LVL'] = 'DEBUG'

    main()

