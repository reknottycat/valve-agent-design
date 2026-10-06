#!/usr/bin/env python3
"""Unit-pressure and kinematic studies; deliberately no pressure/material selection."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent


def calculate(parameters):
    p={k:v['value'] for k,v in parameters['values'].items()}
    bore_area=math.pi*p['bore']**2/4
    seat_area=math.pi*(p['seat_od']**2-p['bore']**2)/4
    stem_area=math.pi*p['stem_od']**2/4
    curtain=math.pi*p['bore']*p['disc_max_lift']
    # Only a geometric screw-study model: no claimed compliant thread profile or operating friction.
    d2=p['stem_od']-p['thread_lead']/2
    tan_lead=p['thread_lead']/(math.pi*d2)
    force_per_mpa=bore_area  # MPa is N/mm².
    torques=[]
    for mu in (.10,.15,.20):
        effective_mu=mu/math.cos(math.radians(15))
        torque_Nm=force_per_mpa*d2/2*(tan_lead+effective_mu)/(1-effective_mu*tan_lead)/1000
        torques.append({'assumed_thread_mu':mu,'thread_only_torque_Nm_per_MPa':torque_Nm,
                        'rim_force_N_per_MPa':torque_Nm/(p['handwheel_od']/2000)})
    return {'schema':'valve.c2-calculation/1.0','status':'NORMALIZED_STUDY_ONLY',
      'pressure_selected_MPa':None,'material_grade_selected':None,'allowable_stress_MPa':None,
      'engineering_compliance':'NOT_ASSESSED','manufacturing_authorized':False,
      'kinematics':{'screw_revolutions_for_reference_travel':p['stem_travel']/p['thread_lead'],
                    'assumed_disc_max_lift_mm':p['disc_max_lift'],'reference_stem_travel_mm':p['stem_travel'],'reference_bore_mm':p['bore'],
                    'bore_area_mm2':bore_area,'ideal_curtain_area_mm2':curtain,
                    'curtain_to_bore_area':curtain/bore_area,
                    'lift_for_equal_ideal_areas_mm':p['bore']/4,
                    'limitations':'Curtain area is a geometry screen; it does not predict resistance, cavitation or flow coefficient'},
      'normalized_static_relations':{'adverse_pressure_closing_force_N_per_MPa':force_per_mpa,
          'gross_stem_axial_stress_MPa_per_MPa':force_per_mpa/stem_area,
          'uniform_flat_seat_mean_contact_pressure_MPa_per_MPa':force_per_mpa/seat_area,
          'seat_annular_area_mm2':seat_area,
          'limitations':['Projected bore area used as a study effective pressure area, not verified force distribution',
             'No45degree tilt amplification or swing lever arm applies to this axial model',
             'Mean seat pressure is not a leak-tightness prediction',
             'Gross stem stress excludes thread roots, bending, buckling, torsion and fatigue']},
      'thread_study':{'pitch_diameter_assumed_mm':d2,'half_flank_angle_assumed_deg':15,
          'lead_angle_deg':math.degrees(math.atan(tan_lead)),'values':torques,
          'formula':'T=F*d2/2*(tan(lambda)+mu/cos(alpha))/(1-mu/cos(alpha)*tan(lambda))',
          'limitations':['Thread profile, actual friction, stem nut and drive efficiencies require verification',
             'Collar, packing, breakaway, seal preload and bearing torque are not included',
             'Not compared with45kgf auxiliary-wrench limit; that is a different application point']},
      'unassessed':['Pressure shell, bonnet joint and bolting strength','Material/service compatibility',
                    'Seal leakage','Shock/vibration/endurance','CFD performance','Manufacturability and casting quality']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=HERE/'calc_results.json');args=parser.parse_args()
    path=HERE.parent/'T11/parameters.json';r=calculate(json.loads(path.read_text()))
    r['parameters_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2))
    print(json.dumps(r,indent=2))


if __name__=='__main__':main()
