import os
import radical.pilot as rp
import radical.utils as ru
import sys
from datetime import datetime
import numpy as np
from xml_input import *
import queue


tasks_finished_queue = queue.Queue()

def task_state_cb(task, state):
    if state not in rp.FINAL:
        # ignore all non-finished state transitions
        return
    tasks_finished_queue.put([task.uid, task.state])
# register callback that will track for task states


def time_str_to_sec(tstr):
    tmins=[3600.0,60.0,1.0]
    st=[float(i)*j for i,j in zip(tstr.split(":"),tmins)]
    return sum(st)

def check_resources(cpus,gpus,tmgr):
    u_cpus,u_gpus,time=0,0,0
    resources={'cpu':0,'gpu':0}
    for k in tmgr.get_tasks():
        if k.state!='DONE':
            td=k.description
            u_cpus+=td.ranks*td.cores_per_rank
            u_gpus+=td.ranks*td.gpus_per_rank
    return cpus-u_cpus,gpus-u_gpus


def make_config_input_files(L,T,nSources,ensemble_path='./test'):

    pos_x=np.random.randint(0,L,[nSources,3])
    pos_t=np.random.randint(0,T,nSources)

    params={'NL':str(L),'NT':str(T)}

    for edir in ['prop','stdout','src','spec','xml']:
        if not os.path.exists(ensemble_path+'/'+edir):
            os.makedirs(ensemble_path+'/'+edir)

    input_files=[]
    for cfg in range(nSources):
        for edir in ['prop','stdout','spec','xml']:
            if not os.path.exists(ensemble_path+'/'+edir+'/'+str(cfg)):
                os.makedirs(ensemble_path+'/'+edir+'/'+str(cfg))

        params.update({'X':pos_x[cfg][0],'Y':pos_x[cfg][1],'Z':pos_x[cfg][2],'T':pos_t[cfg]})

        params['SRC_NAME']='src_x%(X)sy%(Y)sz%(Z)st%(T)s'%params

        xml_path=ensemble_path+'/xml/'+str(cfg)+'/'

        stages=[]
        #stage 0 source
        xml_text=head
        xml_text+=shell_source%params

        params['OBJ_ID']=params['SRC_NAME']
        params['OBJ_TYPE']='LatticePropagator'
        params['LIME_FILE']=ensemble_path+'/src/'+params['SRC_NAME']+'.lime'

        xml_text+=qio_write_erase%params
        xml_text+=tail%params
        stages+=[[xml_path+params['OBJ_ID']+'.ini.xml',xml_text]]
        f=open(xml_path+params['OBJ_ID']+'.ini.xml','w')
        f.write(xml_text)

        #stage 1 propagator
        xml_text=head
        xml_text+=qio_read%params

        params['PROP_NAME']=params['SRC_NAME'].replace('src','prop')
        params['SMEARED_PROP']=params['PROP_NAME'].replace('prop','prop_sh')
        xml_text+=prop_test%params
        xml_text+=shell_sink%params

        params['OBJ_ID']=params['PROP_NAME']
        params['OBJ_TYPE']='LatticePropagator'
        params['LIME_FILE']=ensemble_path+'/prop/'+str(cfg)+'/'+params['OBJ_ID']+'.lime'
        xml_text+=qio_write_erase%params

        params['OBJ_ID']=params['SMEARED_PROP']
        params['OBJ_TYPE']='LatticePropagator'
        params['LIME_FILE']=ensemble_path+'/prop/'+str(cfg)+'/'+params['OBJ_ID']+'.lime'
        xml_text+=qio_write_erase%params

        xml_text+=tail%params
        stages+=[[xml_path+params['OBJ_ID']+'.ini.xml',xml_text]]
        f=open(xml_path+params['OBJ_ID']+'.ini.xml','w')
        f.write(xml_text)


        #stage 2 spectrum
        xml_text=head

        params['UP_QUARK']=params['SMEARED_PROP']
        params['DN_QUARK']=params['SMEARED_PROP']
        params['STRANGE_QUARK']=params['SMEARED_PROP']
        params['SPEC_NAME']=params['PROP_NAME'].replace('prop','spec')

        params['OBJ_ID']=params['PROP_NAME']
        params['OBJ_TYPE']='LatticePropagator'
        params['LIME_FILE']=ensemble_path+'/prop/'+str(cfg)+'/'+params['OBJ_ID']+'.lime'
        xml_text+=qio_read%params

        params['OBJ_ID']=params['SMEARED_PROP']
        params['OBJ_TYPE']='LatticePropagator'
        params['LIME_FILE']=ensemble_path+'/prop/'+str(cfg)+'/'+params['OBJ_ID']+'.lime'
        xml_text+=qio_read%params

        xml_text+=hadron_spectrum%params
        xml_text+=tail%params
        stages+=[[xml_path+params['SPEC_NAME']+'.ini.xml',xml_text]]
        f=open(xml_path+params['SPEC_NAME']+'.ini.xml','w')
        f.write(xml_text)
        
        input_files+=[stages] 
 
    return input_files




def make_tasks(L,T,nSources,session_uid,ensemble_path='./'):


    input_files=make_config_input_files(L,T,nSources,ensemble_path=ensemble_path)


    launch_source=['source ENV_FILE',
                   'export OMP_NUM_THREADS=1']
    gpu_prelaunch=["export QUDA_RESOURCE_PATH="+ensemble_path+'/quda_resource',
                   "[[ -d $QUDA_RESOURCE_PATH ]] || mkdir -p $QUDA_RESOURCE_PATH",
                   'export QUDA_ENABLE_DSLASH_POLICY="0,1,6,7"']  

    stage_resources= [{'cores_per_rank':1,'gpus_per_rank':0,'ranks':4},
                      {'cores_per_rank':1,'gpus_per_rank':1,'ranks':4},
                      {'cores_per_rank':1,'gpus_per_rank':0,'ranks':4}
                      ]
    stage_timeout  = [15,15,15]
    stage_env      = [launch_source,launch_source+gpu_prelaunch,launch_source]
    stage_prog     = ['CHROMA_CPU','CHROMA_GPU','CHROMA_CPU']
    stage_geom     = [' -geom 1 1 2 2',' -geom 1 1 2 2',' -geom 1 1 2 2'] 
    priorities = [1,0,2]

    tasks=[]
    for cfg in range(len(input_files)):
        for stg in range(len(input_files[cfg])):

            td = rp.TaskDescription()
            td.cores_per_rank   = stage_resources[stg]['cores_per_rank']
            td.ranks            = stage_resources[stg]['ranks']
            td.gpus_per_rank    = stage_resources[stg]['gpus_per_rank']
            td.timeout          = stage_timeout[stg]
            td.pre_launch       = stage_env[stg] +\
                                 ['export ini='+input_files[cfg][stg][0],
                                 'export out='+input_files[cfg][stg][0].replace('ini','out'),
                                 'export %(EXE)s=$%(EXE)s'%{'EXE':stage_prog[stg]}]
            td.name             = input_files[cfg][stg][0].split('/')[-1].split('.')[0]
            td.metadata         ={'time':15,
                                  'type':input_files[cfg][stg][0].split('/')[-1].split('_')[0],
                                  'next':None,
                                  'stage':stg,
                                  'priority':priorities[stg]
                                 }
            td.executable       = '$'+stage_prog[stg]+stage_geom[stg]+' -i $ini -o $out'
            td.stdout           = input_files[cfg][stg][0].replace('xml','stdout').replace('.ini.','.')
            td.stderr           = input_files[cfg][stg][0].replace('xml','stdout').replace('.ini.','.')

            tasks+=[td]

            if stg < len(input_files[cfg]) - 1:
                td.metadata['next']=input_files[cfg][stg+1][0].split('/')[-1].split('.')[0]


    return tasks,priorities


def make_ensemble_tasks(L, T, nSources, session_uid, ensemble_path):

    tasks,priorities=make_tasks(L,T,nSources,session_uid,ensemble_path)

    task_list,si={},{}
    task_names={}
    for iTask in tasks:
        uid_prefix  = iTask.metadata['type']+"_"+str(iTask.metadata['time'])
        if uid_prefix not in si:
            si[uid_prefix]=0
        iTask.uid = ru.generate_id(uid_prefix + f'.{si[uid_prefix]:06d}',ru.ID_CUSTOM, ns=session_uid)
        si[uid_prefix]+=1
        task_list[iTask.name]=iTask
        task_names[iTask.uid]=iTask

    for iTask in tasks:
        if iTask.metadata['next'] is not None:
            iTask.metadata['next_task']=task_list[iTask.metadata['next']]
        else:
            iTask.metadata['next_task']=None


    return task_names,priorities

def get_priority_tasks(next_td,alloc_init_time,PILOT_DESCRIPTION,tmgr):

    priority_tasks=[]
    
    task_list=list(next_td)

    new_list=[[] for k in next_td]

    if any(task_list):  
        #Check available wallclock time and resources            
        alloc_curr_time=datetime.now().strftime("%H:%M:%S")
        time_left=PILOT_DESCRIPTION['runtime']-(time_str_to_sec(alloc_curr_time)-time_str_to_sec(alloc_init_time))/60.

        acpus,agpus=check_resources(PILOT_DESCRIPTION['cores'],PILOT_DESCRIPTION['gpus'],tmgr)

        for p in range(len(task_list)):
            for task in task_list[p]:
                if time_left+2 > task.metadata['time']:
                    newTask=True

                task_cpus=task.ranks*task.cores_per_rank
                task_gpus=task.ranks*task.gpus_per_rank

                if acpus >= task_cpus and agpus >=task_gpus:
                    priority_tasks+=[task]
                    acpus=acpus-task_cpus
                    agpus=agpus-task_gpus
                    #need to remove from list
                else:
                    new_list[p]+=[rp.TaskDescription(task)]
  
    return priority_tasks,new_list
                                             


def launch_tasks(tmgr,tasks,PILOT_DESCRIPTION,priorities):

    tmgr.register_callback(task_state_cb) 
    print("Initial task list:\n")

    next_td=[[] for p in priorities]
    for iTask in tasks:
        if tasks[iTask].metadata['stage']==0:
            print(iTask)
            next_td[tasks[iTask].metadata['priority']]+=[tasks[iTask]]

    tasks_active = 0

    print('Start time: '+ datetime.now().strftime("%H:%M:%S"))
    alloc_init_time=datetime.now().strftime("%H:%M:%S")

    task_to_submit,next_td=get_priority_tasks(next_td,alloc_init_time,PILOT_DESCRIPTION,tmgr)

    sub_tasks=tmgr.submit_tasks(task_to_submit)

    for task in sub_tasks:
        print(f'task {task.uid} is submitted')
        tasks_active += 1

    while tasks_active:

        try:
            task_uid, task_state = tasks_finished_queue.get_nowait()
            tasks_active -= 1
            print(f'task: {task_uid} | state: {task_state}')
               
            #Add next stage task to the queue if the dependecy finished succesfully
            if tasks[task_uid].metadata['next_task'] is not None and task_state=='DONE':
                next_task=rp.TaskDescription(tasks[task_uid].metadata['next_task'])
                next_td[next_task.metadata['priority']]+=[next_task]

        except queue.Empty:
            if not any(next_td):
                continue

        task_to_submit,next_td=get_priority_tasks(next_td,alloc_init_time,PILOT_DESCRIPTION,tmgr)

        if len(task_to_submit) > 0:
            print('task_to_submit {}'.format(len(task_to_submit)))
            for k in task_to_submit:
                print(k['uid'])

        sub_tasks = tmgr.submit_tasks(task_to_submit)
        tasks_active+=len(sub_tasks)

    print(f'tasks_active: {tasks_active}')
