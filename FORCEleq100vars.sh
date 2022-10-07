echo "[INFO] parsed/out clean up"
rm ./parsed/out/*.csv
rm ./parsed/out/*.log
rm ./parsed/out/*.orders
echo "-------------------------------------------"
./ddueruem.py evaluation/VELVET/VELVET.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/GPLtiny/GPLtiny.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/npc/npc.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/ChatClient/ChatClient.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/Car/Car.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/FeatureIDE/FeatureIDE.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/FameDB2/FameDB2.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/FameDB/FameDB.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/APL/APL.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/SafeBali/SafeBali.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/GPLsmall/GPLsmall.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/APL-Model/APL-Model.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/TightVNC/TightVNC.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/anyvend/anyvend.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/GPLmedium/GPLmedium.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/SortingLine/SortingLine.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/PPU/PPU.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/BerkeleyDB/BerkeleyDB.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
./ddueruem.py evaluation/axTLS/axTLS.xml --svo force n:$1 --bdd cudd lib_t:-1 dvo:$2 dump:True
sleep 1
echo "-------------------------------------------"
