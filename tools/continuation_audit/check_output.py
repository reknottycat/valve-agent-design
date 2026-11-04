"""Complete native continuation window checker; no old diagnostic checker chain."""
import json,re,math,sys
from pathlib import Path
from window_contract import WindowContract
EPS=sys.float_info.epsilon
def values(tokens,n,nonnegative=False):
    x=list(map(float,tokens));assert len(x)==n and all(math.isfinite(v) for v in x)
    if nonnegative:assert all(v>=0 for v in x)
    return x

def check(path,ids,contract):
    if not isinstance(contract, WindowContract):raise TypeError("explicit validated WindowContract required")
    start=contract.start;first,last=contract.output_states;states=contract.observed_states
    if isinstance(ids,(str,Path)):ids=json.loads(Path(ids).read_text())
    assert ids==sorted(set(ids)) and len(ids)==38
    lines=Path(path).read_text().splitlines();begin={};end={};inc={};raw={};mom={};mr={};patch={};ports={};cont={};bins={};red={};div={};bcu={};bcp={};bcphi={}
    def add(o,k,v):assert k not in o;o[k]=v
    def sha(s):assert re.fullmatch('[0-9a-f]{64}',s);return s
    for line in lines:
        x=line.split()
        if not x:continue
        tag=x[0]
        if tag in ('CONT_BC_U','CONT_BC_P'):
            assert len(x)==11;hashes=[sha(v) for v in x[3:9]];delta=values([x[9]],1,True)[0];changed=int(x[10]);assert changed>=0 and ((changed==0)==(delta==0))
            target=bcu if tag=='CONT_BC_U' else bcp
            target.setdefault(int(x[1]),[]).append({'id':int(x[2]),'beforeValue_afterValue_beforeHidden_afterHidden_beforeFlags_afterFlags_hashes':hashes,'maxValueDelta':delta,'changed_faces':changed})
        elif tag=='CONT_BC_PHI':
            assert len(x)==8 and x[3]=='phi' and re.fullmatch('[1-9][0-9]*',x[4]) and x[4]==x[5];bcphi.setdefault(int(x[1]),[]).append({'id':int(x[2]),'phiName':x[3],'lookup_pointer':x[4],'running_phi_pointer':x[5],'patch_phi_hash':sha(x[6]),'maxFractionDefect':values([x[7]],1,True)[0]})
        elif tag=='CONT_STATE_BEGIN':
            assert len(x)==4;add(begin,int(x[1]),[sha(v) for v in x[2:]])
        elif tag=='CONT_STATE_END':
            assert len(x)==5 and x[4]=='UPDATED_RAW_AND_CONSERVATIVE_PHI_NO_SOLVE';add(end,int(x[1]),[sha(v) for v in x[2:4]])
        elif tag=='CONT_INCREMENT':
            assert len(x)==11 and x[2] in ('0','1');v=values(x[3:],8,True);add(inc,int(x[1]),{'valid':bool(int(x[2])),'currentU_RMS_m_s':v[0],'currentp_RMS_m2_s2':v[1],'deltaU_RMS_m_s':v[2],'deltap_RMS_m2_s2':v[3],'deltaU_max_m_s':v[4],'deltap_max_m2_s2':v[5],'deltaU_normalized':v[6],'deltap_normalized':v[7]})
        elif tag=='CONT_RAW_SOURCE':
            assert len(x)==8;add(raw,int(x[1]),[sha(v) for v in x[2:]])
        elif tag=='CONT_MOMENTUM':
            assert len(x)==10;v=values(x[2:8],6,True);cell=int(x[8]);vol=values(x[9:],1,True)[0];assert 0<=cell<759760 and vol>0;add(mom,int(x[1]),{'norms':v,'max_density_cell':cell,'max_density_cellV_m3':vol})
        elif tag=='CONT_MOM_SELECTED':
            m=re.fullmatch(r'CONT_MOM_SELECTED (\d+) (\d+) (\S+) \(([^)]*)\)',line);assert m
            s,i,v,r=m.groups();v=values([v],1,True)[0];assert v>0;mr.setdefault(int(s),[]).append({'id':int(i),'V_m3':v,'integrated_R_m4_s2':values(r.split(),3)})
        elif tag=='CONT_PATCH':
            assert len(x)==17;count=int(x[8]);v=values(x[9:14],5);counts=list(map(int,x[14:]));assert count>=0 and sum(counts)==count and min(counts)>=0 and v[0]>0 and v[3]>=0 and v[4]>=0
            patch.setdefault(int(x[1]),[]).append({'id':int(x[2]),'name':x[3],'mesh_type':x[4],'U_type':x[5],'p_type':x[6],'phi_type':x[7],'nfaces':count,'area_m2':v[0],'mean_pkin_m2_s2':v[1],'signedQ_m3_s':v[2],'incoming_m3_s':v[3],'outgoing_m3_s':v[4],'positive_negative_zero':counts})
        elif tag=='CONT_PORTS':
            assert len(x)==12 and x[11]=='static_area_mean_kinematic_inlet_reference' and x[9] in ('0','1');v=values(x[2:9],7);k=values([x[10]],1)[0];assert v[0]>0 and v[1]>0;add(ports,int(x[1]),{'Ain_m2':v[0],'Aout_m2':v[1],'Qin_m3_s':v[2],'Qout_m3_s':v[3],'pinMean_m2_s2':v[4],'poutMean_m2_s2':v[5],'DeltaPkin_m2_s2':v[6],'K_valid':bool(int(x[9])),'K':k if x[9]=='1' else None})
        elif tag=='CONT_CONTINUITY':
            assert len(x)==12;v=values(x[2:9],7);cell=int(x[9]);tail=values(x[10:],2);assert min(v[0],v[1],v[3],v[4])>=0 and v[5]>0 and 0<=cell<759760 and tail[0]>0;add(cont,int(x[1]),{'norms':v,'max_div_cell':cell,'max_div_cellV_m3':tail[0],'integratedMinusBoundary_m3_s':tail[1]})
        elif tag=='CONT_BIN':
            assert len(x)==6;count=int(x[3]);assert count>=0;v=values(x[4:],2,True);bins.setdefault(int(x[1]),[]).append({'bin':int(x[2]),'cells':count,'volume_m3':v[0],'abs_integrated_div_m3_s':v[1]})
        elif tag=='CONT_BIN_REDUCTION':
            assert len(x)==7 and int(x[2])==759760;v=values(x[3:],4);assert v[1]>0 and v[3]>0 and abs(v[0])<=v[1] and abs(v[2])<=v[3];add(red,int(x[1]),v)
        elif tag=='CONT_DIV_SELECTED':
            assert len(x)==6;v=values(x[3:],3);assert v[0]>0;div.setdefault(int(x[1]),[]).append({'id':int(x[2]),'V_m3':v[0],'div_s-1':v[1],'Vdiv_m3_s':v[2]})
    for o in (begin,end,inc,raw,mom,mr,patch,ports,cont,bins,red,div,bcu,bcp,bcphi):assert set(o)==set(states)
    assert begin==end,'observer changed original fields or nuEff'
    localmax={}
    for s in states:
        assert [r['id'] for r in mr[s]]==[r['id'] for r in div[s]]==ids
        assert [r['id'] for r in bcu[s]]==[r['id'] for r in bcp[s]]==list(range(132))
        need=[r['id'] for r in patch[s] if r['U_type']=='pressureInletOutletVelocity'];assert need and [r['id'] for r in bcphi[s]]==need
        for field,rows in [('U',bcu[s]),('p',bcp[s])]:
            for bc,identity in zip(rows,patch[s]):
                assert bc['changed_faces']<=identity['nfaces']
                if identity[field+'_type'] in (('fixedValue','noSlip') if field=='U' else ('fixedValue',)):
                    h=bc['beforeValue_afterValue_beforeHidden_afterHidden_beforeFlags_afterFlags_hashes'];assert h[0]==h[1] and h[2]==h[3] and bc['changed_faces']==0
        assert [r['id'] for r in patch[s]]==list(range(132)) and [r['bin'] for r in bins[s]]==list(range(9))
        assert sum(r['cells'] for r in bins[s])==759760
        assert inc[s]['valid']==(s!=start)
        if s==start:
            for k in ('deltaU_RMS_m_s','deltap_RMS_m2_s2','deltaU_max_m_s','deltap_max_m2_s2','deltaU_normalized','deltap_normalized'):assert inc[s][k]==0;inc[s][k]=None
        else:
            for out,num,den in [('deltaU_normalized','deltaU_RMS_m_s','currentU_RMS_m_s'),('deltap_normalized','deltap_RMS_m2_s2','currentp_RMS_m2_s2')]:
                target=inc[s][num]/max(inc[s][den],1e-12);assert abs(inc[s][out]-target)<=256*EPS*(abs(inc[s][out])+abs(target))+1e-30
        vs=0.;ab=0.
        for row in bins[s]:vs+=row['volume_m3'];ab+=row['abs_integrated_div_m3_s']
        n=cont[s]['norms'];g=8*759760*EPS;gamma=g/(1-g);vb=gamma*(abs(n[5])+abs(vs))+1e-30;bb=gamma*(abs(n[1])+abs(ab))+1e-30
        assert red[s]==[vs-n[5],vb,ab-n[1],bb] and abs(vs-n[5])<=vb and abs(ab-n[1])<=bb
        assert bins[s][0]['abs_integrated_div_m3_s']==0
        local=[]
        for r,v in zip(mr[s],div[s]):
            assert r['V_m3']==v['V_m3']
            r['density_R_m_s2']=[a/r['V_m3'] for a in r['integrated_R_m4_s2']]
            assert all(math.isfinite(z) for z in r['density_R_m_s2']);local.append(math.hypot(*r['density_R_m_s2']))
            product=v['V_m3']*v['div_s-1'];assert abs(v['Vdiv_m3_s']-product)<=256*EPS*(abs(v['Vdiv_m3_s'])+abs(product))+1e-30
        localmax[s]=max(local)
        pi=patch[s][78];po=patch[s][33];assert pi['name']=='inlet' and po['name']=='outlet' and patch[s][79]['name']=='wall_FDG_80'
        q=ports[s]
        assert [q['Ain_m2'],q['Aout_m2'],q['Qin_m3_s'],q['Qout_m3_s'],q['pinMean_m2_s2'],q['poutMean_m2_s2']]==[pi['area_m2'],po['area_m2'],pi['signedQ_m3_s'],po['signedQ_m3_s'],pi['mean_pkin_m2_s2'],po['mean_pkin_m2_s2']]
        assert q['DeltaPkin_m2_s2']==q['pinMean_m2_s2']-q['poutMean_m2_s2']
        assert q['K_valid']==(abs(q['Qin_m3_s'])>1e-12)
        if q['K_valid']:
            k=2*q['DeltaPkin_m2_s2']/(abs(q['Qin_m3_s'])/q['Ain_m2'])**2
            assert abs(q['K']-k)<=256*EPS*(abs(q['K'])+abs(k))+1e-30
        find=lambda p:next(i for i,l in enumerate(lines) if l.startswith(p))
        assert find('CONT_STATE_BEGIN '+str(s)+' ')<find('CONT_BC_U '+str(s)+' 0 ')<find('CONT_BC_P '+str(s)+' 131 ')<find('CONT_RAW_SOURCE '+str(s)+' ')<find('CONT_STATE_END '+str(s)+' ')
    # Verify actual native loop, strict linear and persistence lifecycle independently of IPC counters.
    native=check_native_stages(lines,contract)
    continuity={s:{f'L1_relative_imposed_Qin{start}':cont[s]['norms'][1]/max(abs(ports[start]['Qin_m3_s']),1e-12),'max_abs_div_s-1':cont[s]['norms'][4]} for s in contract.output_states}
    qrel=abs(ports[last]['Qout_m3_s']-ports[first]['Qout_m3_s'])/max(abs(ports[first]['Qout_m3_s']),1e-12)
    prel=abs(ports[last]['DeltaPkin_m2_s2']-ports[first]['DeltaPkin_m2_s2'])/max(abs(ports[first]['DeltaPkin_m2_s2']),1e-12)
    criteria={'updated_momentum_L2_final_below_restart':mom[last]['norms'][0]<mom[start]['norms'][0],'updated_momentum_volumeRMS_final_below_restart':mom[last]['norms'][1]<mom[start]['norms'][1],f'deltaU_step{last}_no_greater_than{first}':inc[last]['deltaU_RMS_m_s']<=inc[first]['deltaU_RMS_m_s'],f'deltap_step{last}_no_greater_than{first}':inc[last]['deltap_RMS_m2_s2']<=inc[first]['deltap_RMS_m2_s2'],'global_max_density_final_no_more_than1p10_restart':mom[last]['norms'][2]<=1.10*mom[start]['norms'][2],'fixed38_max_density_final_no_more_than1p10_restart':localmax[last]<=1.10*localmax[start],'local_continuity_each_endpoint':all(x[f'L1_relative_imposed_Qin{start}']<=1e-6 and x['max_abs_div_s-1']<=1e-6 for x in continuity.values()),f'Qout_step{first}to{last}_relative_change_le1pct':qrel<=.01,f'DeltaP_step{first}to{last}_relative_change_le1pct':prel<=.01}
    growth_warnings={}
    for current,previous in ((first,start),(last,first)):
        metrics={}
        for column,name in enumerate(('raw_L2','volumeRMS_density','global_max_density')):
            before=mom[previous]['norms'][column];after=mom[current]['norms'][column]
            metrics[name]={'previous':before,'current':after,'ratio':after/before if before>0 else None,'zero_previous':before==0,'warning_gt1p25':after>1.25*before}
        growth_warnings[current]={'previous_state':previous,'metrics':metrics,'any_warning':any(v['warning_gt1p25'] for v in metrics.values()),'effect':'record only; no early stop or execution qualification change'}
    return {'step_growth_warnings':growth_warnings,'qualified_execution':True,'status':f'COMPLETE_NATIVE_SIMPLE_CONTINUATION_{start}_{first}_{last}_RESEARCH_WINDOW_NOT_STEADY_CERTIFICATE','native_stages':native,'state_fields_nuEff_hashes':begin,'momentum_phase':'BC-consistent updated raw momentum, clone-native boundary evaluation before assembly','probe_BC_U':bcu,'probe_BC_p':bcp,'probe_actual_phi_lookup':bcphi,'updated_raw_RHS_probe_flags_hashes':raw,'increments':inc,'momentum':mom,'momentum_norm_columns':['vector_L2_m4_s2','volumeRMS_density_m_s2','max_density_m_s2','L1_x_m4_s2','L1_y_m4_s2','L1_z_m4_s2'],'momentum_selected38':mr,'patches':patch,'ports':ports,'continuity':cont,'continuity_norm_columns':['L2_integrated_m3_s','L1_integrated_m3_s','signedSum_m3_s','volumeRMS_div_s-1','max_abs_div_s-1','volume_m3','boundary_signedNet_m3_s'],'bins':bins,'bin_reduction':red,'div_selected38':div,'fixed38_max_density_m_s2':localmax,'continuity_research_metrics':continuity,f'Qout_relative_change{first}to{last}':qrel,f'DeltaP_relative_change{first}to{last}':prel,'research_criteria':criteria,'research_continuation_signal':all(criteria.values()),'research_threshold_basis':'self-built triage, not published engineering standard','imposed_Q_and_derived_K_independent_validation':False,'engineering_release':False,'real_seal_verified':False,'sustained_nonlinear_steady_convergence':False}

def check_native_stages(lines,contract):
    if not isinstance(contract, WindowContract):raise TypeError("explicit validated WindowContract required")
    start=contract.start;first,last=contract.output_states
    restart=[];loops={};steps={};us={};ps={};flux={};written={};solvelines=[]
    def add(o,k,v):assert k not in o;o[k]=v
    for line in lines:
        x=line.split()
        if not x:continue
        if 'Solving for ' in line:solvelines.append(line)
        if x[0]=='CONT_RESTART':
            assert len(x)==11 and x[1]==contract.time_name(start) and x[7:]==['Stokes','Newtonian','MRF0','options0'];idx=int(x[2]);v=values(x[3:7],4);assert v[0]==contract.delta_t and v[2]==int(v[2]);restart.append({'state':start,'index':idx,'deltaT':v[0],'cumulativeContErr':v[1],'pRefCell':int(v[2]),'pRefValue':v[3]})
        elif x[0]=='CONT_NATIVE_LOOP':
            assert len(x)==5 and x[2] in ('0','1');add(loops,int(x[1]),{'returned':bool(int(x[2])),'time':values([x[3]],1)[0],'index':int(x[4])})
        elif x[0]=='CONT_STEP_BEGIN':
            assert len(x)==6 and x[4]==x[5] and re.fullmatch('[0-9a-f]{64}',x[4]);add(steps,int(x[1]),{'state':int(x[2]),'index':int(x[3]),'prior_p_values_hash':x[4],'native_prevIter_hash':x[5]})
        elif x[0]=='CONT_U_LINEAR':
            m=re.fullmatch(r'CONT_U_LINEAR (\d+) \(([^)]*)\) \(([^)]*)\) \(([^)]*)\) ([01]) ([01])',line);assert m
            s,ini,fin,it,conv,sing=m.groups();ini=values(ini.split(),3,True);fin=values(fin.split(),3,True);it=list(map(int,it.split()));assert len(it)==3 and all(0<=v<=100 for v in it) and max(fin)<=1e-10 and sing=='0';add(us,int(s),{'initial':ini,'final':fin,'iterations':it,'aggregate_converged':bool(int(conv)),'singular':False,'aggregate_flag_known_vector_source_limitation':True})
        elif x[0]=='CONT_P_LINEAR':
            assert len(x)==9 and x[3] in ('0','1') and x[7:]==['1','0'];v=values(x[4:6],2,True);it=int(x[6]);assert v[1]<=1e-10 and 0<=it<=100;add(ps,(int(x[1]),int(x[2])),{'native_final':bool(int(x[3])),'initial':v[0],'final':v[1],'iterations':it,'converged':True,'singular':False})
        elif x[0]=='CONT_FINAL_PHI':
            assert len(x)==5 and x[2:4]==['2','1'] and x[4] in ('0','1');add(flux,int(x[1]),{'actual_corr':2,'oriented':True,'adjustClosed':bool(int(x[4]))})
        elif x[0]=='CONT_CHECKPOINT_WRITTEN':
            assert len(x)==5 and re.fullmatch('[0-9a-f]{64}',x[4]);add(written,int(x[1]),{'index':int(x[2]),'cumulativeContErr':values([x[3]],1)[0],'physical_hidden_state_hash':x[4]})
    assert len(restart)==1 and set(loops)=={1,2,3} and set(steps)=={1,2} and set(us)==set(flux)==set(written)==set(contract.output_states)
    assert set(ps)=={(s,c) for s in contract.output_states for c in (1,2)}
    assert restart[0]['index']==contract.restart_index and restart[0]['deltaT']==contract.delta_t and restart[0]['cumulativeContErr']==contract.cumulative_continuity,'native restart differs from explicit window contract'
    idx=restart[0]['index'];assert loops=={1:{'returned':True,'time':float(first),'index':contract.index_for(first)},2:{'returned':True,'time':float(last),'index':contract.index_for(last)},3:{'returned':False,'time':float(last),'index':contract.index_for(last)}}
    from collections import Counter
    names=[re.search(r'Solving for ([^,]+),',l).group(1) for l in solvelines]
    assert Counter(names)==Counter({'Ux':2,'Uy':2,'Uz':2,'p':4})
    find=lambda prefix:next(i for i,l in enumerate(lines) if l.startswith(prefix))
    ix=[find('CONT_RESTART '),find('CONT_STATE_END '+contract.time_name(start)+' ')]
    for n,s in enumerate(contract.output_states,1):
        assert steps[n]['state']==s and steps[n]['index']==written[s]['index']==idx+n
        assert ps[(s,1)]['native_final'] is False and ps[(s,2)]['native_final'] is True
        stateend=next(l.split() for l in lines if l.startswith('CONT_STATE_END '+str(s)+' '));assert stateend[2]==written[s]['physical_hidden_state_hash']
        ix.extend([find('CONT_NATIVE_LOOP '+str(n)+' '),find('CONT_STEP_BEGIN '+str(n)+' '),find('CONT_U_LINEAR '+str(s)+' '),find('CONT_P_LINEAR '+str(s)+' 1 '),find('CONT_P_LINEAR '+str(s)+' 2 '),find('CONT_FINAL_PHI '+str(s)+' '),find('CONT_STATE_BEGIN '+str(s)+' '),find('CONT_STATE_END '+str(s)+' '),find('CONT_CHECKPOINT_WRITTEN '+str(s)+' ')])
    terminal=f'SIMPLE_CONTINUATION_COMPLETE start{start} end{last} outerSteps2 momentumSolves2 pressureSolves4 conservativePhi1 nativeModelCorrect2 checkpointStates2'
    assert lines.count(terminal)==1;ix.extend([find('CONT_NATIVE_LOOP 3 '),lines.index(terminal)]);assert ix==sorted(set(ix))
    return {'restart':restart[0],'native_loops':loops,'steps':steps,'velocity_linear':us,'pressure_linear':{s:{c:ps[(s,c)] for c in (1,2)} for s in contract.output_states},'actual_final_phi':flux,'written_checkpoints':written,'native_solve_log_counts':dict(Counter(names))}

