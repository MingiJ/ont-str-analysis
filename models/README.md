# Models

DeepRepeat requires the `trainedmod_32_0.2` model directory.

Download (from the DeepRepeat authors):
```bash
wget https://www.openbioinformatics.org/hx1/drmodel/trainedmod_32_0.2.tar.gz
mkdir -p models
cd models
 tar -xvf ../trainedmod_32_0.2.tar.gz
```

Then set:
```bash
export DEEPREPEAT_MODEL_DIR=$PWD/models/trainedmod_32_0.2
```
