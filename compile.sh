echo "compile.sh: Compile sol0.6.0/..."
cd sol0.6.0
echo """compiler:
   solc:
       version: 0.6.0""" > brownie-config.yaml
brownie compile
rm brownie-config.yaml
cd ..

echo ""

echo "compile.sh: Compile sol0.8.12/..."
cd sol080
echo """compiler:
   solc:
       version: 0.8.12""" > brownie-config.yaml
brownie compile
rm brownie-config.yaml
cd ..

echo ""

echo "compile.sh: Done"

