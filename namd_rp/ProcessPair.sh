#!/bin/bash
#
# Enumerating by hand the lambda points and the associated weights 
#
lambdaPoint=("0.0254" "0.1292" "0.2971" "0.5000" "0.7029" "0.8708" "0.9746")
weights=("0.12948" "0.27971" "0.38183" "0.4180" "0.38183" "0.27971" "0.12948")
#
sum=0.0
scale=0.5
#
for i in "${!weights[@]}"
do
    #
    dir=G${lambdaPoint[i]}
    cd $dir
    egrep '^ENERGY:' pair.log  | awk '{printf("%d %f\n",$2,$7)}' | tail -n 100 > pair.dat 
    x=`awk '{n++;sum+=$2} END {print sum/n}' pair.dat`
    cd ..
    #
    w=${weights[i]}
    tmp=$(echo "$scale * $w * $x + $sum" | bc)
    sum=$tmp
    #
done 
#
simout=`printf "%.2f\n" $sum`
WignerCorrection=-12.02
echo "Simulation estimate of hydration free energy (kcal/mol):" $simout
correctedMu=` printf "%.2f\n" $(echo "$simout + $WignerCorrection" | bc)`
echo "Corrected estimate of hydration free energy (kcal/mol):" $correctedMu
Gerhard=-95.12
echo "Value reported by Hummer et al. 1996 (kcal/mol):" $Gerhard
